"""Auditable comparison against externally supplied scientific reference outputs.

These routines never fetch or invent reference labels. They require frozen,
provenance-described reference files supplied by a researcher and report
feature/sample overlap, numeric agreement, and thresholded call concordance.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_tsv(path: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"{source} has no TSV header.")
        rows = list(reader)
    return list(reader.fieldnames), rows


def _provenance(value: dict[str, Any] | None) -> dict[str, Any]:
    required = {"dataset_accession", "reference_method", "software", "source_url"}
    if not isinstance(value, dict) or any(not str(value.get(k, "")).strip() for k in required):
        raise ValueError("reference_provenance must include dataset_accession, reference_method, software, and source_url.")
    return value


def _finite(value: str, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Non-numeric value for {label}: {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"Non-finite value for {label}.")
    return result


def _rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[order[k]] = rank
        i = j
    return ranks


def _pearson(a: list[float], b: list[float]) -> float | None:
    if len(a) < 2:
        return None
    ma, mb = math.fsum(a) / len(a), math.fsum(b) / len(b)
    da, db = [x - ma for x in a], [x - mb for x in b]
    va, vb = math.fsum(x*x for x in da), math.fsum(x*x for x in db)
    if va <= 0 or vb <= 0:
        return None
    return math.fsum(x*y for x, y in zip(da, db)) / math.sqrt(va*vb)


def _numeric_metrics(actual: list[float], reference: list[float]) -> dict[str, float | None]:
    if not actual or len(actual) != len(reference):
        raise ValueError("Numeric metric vectors must be non-empty and equal length.")
    errors = [a-r for a, r in zip(actual, reference)]
    return {
        "n": len(errors),
        "mae": math.fsum(abs(x) for x in errors) / len(errors),
        "rmse": math.sqrt(math.fsum(x*x for x in errors) / len(errors)),
        "mean_signed_error": math.fsum(errors) / len(errors),
        "pearson_r": _pearson(actual, reference),
        "spearman_r": _pearson(_rank(actual), _rank(reference)),
    }


def compare_expression_matrices(
    oracle_path: str | Path, reference_path: str | Path, *,
    provenance: dict[str, Any], minimum_feature_overlap: float = 0.8,
) -> dict[str, Any]:
    """Compare matched features/samples in two expression matrices (feature x sample TSV)."""
    provenance = _provenance(provenance)
    if not 0 < minimum_feature_overlap <= 1:
        raise ValueError("minimum_feature_overlap must be in (0, 1].")
    oracle_file, reference_file = Path(oracle_path), Path(reference_path)
    oh, orows = _read_tsv(oracle_file)
    rh, rrows = _read_tsv(reference_file)
    if len(oh) < 3 or len(rh) < 3:
        raise ValueError("Expression matrices need a feature column and at least two sample columns.")
    if oh[0] != rh[0]:
        raise ValueError("Feature identifier column names must match.")
    osamples, rsamples = oh[1:], rh[1:]
    if set(osamples) != set(rsamples) or len(osamples) != len(rsamples):
        raise ValueError("Oracle and reference sample identifiers must match exactly.")
    def index(rows, columns, label):
        result = {}
        for row in rows:
            feature = row.get(columns[0], "").strip()
            if not feature or feature in result:
                raise ValueError(f"{label} contains an empty or duplicate feature identifier: {feature!r}")
            result[feature] = row
        return result
    oi, ri = index(orows, oh, "Oracle matrix"), index(rrows, rh, "Reference matrix")
    common = sorted(set(oi) & set(ri))
    overlap = len(common) / max(1, min(len(oi), len(ri)))
    if overlap < minimum_feature_overlap:
        raise ValueError(f"Feature overlap {overlap:.3f} is below required {minimum_feature_overlap:.3f}.")
    per_sample = {}
    all_o, all_r = [], []
    for sample in osamples:
        a = [_finite(oi[f][sample], f"{f}/{sample}") for f in common]
        b = [_finite(ri[f][sample], f"{f}/{sample}") for f in common]
        per_sample[sample] = _numeric_metrics(a, b)
        all_o.extend(a); all_r.extend(b)
    return {
        "benchmark_type": "external_expression_matrix_reference_comparison",
        "oracle_sha256": _sha(oracle_file), "reference_sha256": _sha(reference_file),
        "reference_provenance": provenance,
        "oracle_features": len(oi), "reference_features": len(ri),
        "matched_features": len(common), "feature_overlap_fraction": overlap,
        "samples": osamples, "per_sample": per_sample,
        "pooled_numeric_metrics": _numeric_metrics(all_o, all_r),
        "limitations": "Agreement is conditional on the supplied reference, platform, probe mapping, preprocessing, and sample identity. High correlation does not establish biological correctness. Inspect systematic offsets, feature mapping, normalization, and reference provenance; do not compare different platforms as if they were interchangeable.",
    }


def compare_de_tables(
    oracle_path: str | Path, reference_path: str | Path, *,
    provenance: dict[str, Any], feature_column: str = "feature",
    oracle_logfc_column: str = "log2fc", reference_logfc_column: str = "logFC",
    oracle_fdr_column: str = "padj", reference_fdr_column: str = "adj.P.Val",
    fdr_threshold: float = 0.05, minimum_feature_overlap: float = 0.8,
) -> dict[str, Any]:
    """Compare ORACLE and trusted external DE result tables on shared feature IDs."""
    provenance = _provenance(provenance)
    if not 0 < fdr_threshold < 1 or not 0 < minimum_feature_overlap <= 1:
        raise ValueError("FDR threshold and overlap must be within (0,1).")
    op, rp = Path(oracle_path), Path(reference_path)
    oh, orows = _read_tsv(op); rh, rrows = _read_tsv(rp)
    for header, required, label in (
        (oh, {feature_column, oracle_logfc_column, oracle_fdr_column}, "Oracle"),
        (rh, {feature_column, reference_logfc_column, reference_fdr_column}, "Reference"),
    ):
        if not required.issubset(header):
            raise ValueError(f"{label} table missing columns: {sorted(required-set(header))}")
    def index(rows, fc_col, fdr_col, label):
        result = {}
        for row in rows:
            feature = row[feature_column].strip()
            if not feature or feature in result:
                raise ValueError(f"{label} has empty or duplicate feature IDs: {feature!r}")
            fc, fdr = _finite(row[fc_col], f"{feature}/{fc_col}"), _finite(row[fdr_col], f"{feature}/{fdr_col}")
            if not 0 <= fdr <= 1:
                raise ValueError(f"{label} adjusted p-values must be in [0,1].")
            result[feature] = (fc, fdr)
        return result
    oi = index(orows, oracle_logfc_column, oracle_fdr_column, "Oracle")
    ri = index(rrows, reference_logfc_column, reference_fdr_column, "Reference")
    common = sorted(set(oi) & set(ri))
    overlap = len(common) / max(1, min(len(oi), len(ri)))
    if overlap < minimum_feature_overlap:
        raise ValueError(f"Feature overlap {overlap:.3f} is below required {minimum_feature_overlap:.3f}.")
    ofc, rfc = [oi[x][0] for x in common], [ri[x][0] for x in common]
    osig = {x for x in common if oi[x][1] <= fdr_threshold}
    rsig = {x for x in common if ri[x][1] <= fdr_threshold}
    tp, fp, fn, tn = len(osig & rsig), len(osig-rsig), len(rsig-osig), len(set(common)-(osig|rsig))
    precision = tp/(tp+fp) if tp+fp else None
    recall = tp/(tp+fn) if tp+fn else None
    return {
        "benchmark_type": "external_differential_expression_reference_comparison",
        "oracle_sha256": _sha(op), "reference_sha256": _sha(rp),
        "reference_provenance": provenance,
        "oracle_features": len(oi), "reference_features": len(ri),
        "matched_features": len(common), "feature_overlap_fraction": overlap,
        "fdr_threshold": fdr_threshold,
        "log2fc_metrics": _numeric_metrics(ofc, rfc),
        "significance_concordance": {
            "true_positive": tp, "false_positive": fp, "false_negative": fn, "true_negative": tn,
            "precision": precision, "recall": recall,
            "f1": (2*precision*recall/(precision+recall) if precision is not None and recall is not None and precision+recall else None),
            "jaccard": tp/(tp+fp+fn) if tp+fp+fn else None,
            "oracle_significant": len(osig), "reference_significant": len(rsig),
        },
        "limitations": "DE agreement depends on identical samples, contrast direction, design/covariates, feature universe, filtering, and reference implementation. P-value agreement is not expected across different statistical models. This is external concordance, not proof that either analysis is biologically correct.",
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compare ORACLE outputs with a frozen external reference.")
    parser.add_argument("mode", choices=("expression", "de"))
    parser.add_argument("--oracle", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--provenance-json", required=True, help="JSON object documenting the trusted reference.")
    parser.add_argument("--output", help="Write report JSON here; otherwise print it.")
    parser.add_argument("--minimum-overlap", type=float, default=0.8)
    parser.add_argument("--fdr", type=float, default=0.05)
    args = parser.parse_args(argv)
    provenance = json.loads(Path(args.provenance_json).read_text(encoding="utf-8"))
    if args.mode == "expression":
        report = compare_expression_matrices(args.oracle, args.reference, provenance=provenance,
                                             minimum_feature_overlap=args.minimum_overlap)
    else:
        report = compare_de_tables(args.oracle, args.reference, provenance=provenance,
                                   minimum_feature_overlap=args.minimum_overlap, fdr_threshold=args.fdr)
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
