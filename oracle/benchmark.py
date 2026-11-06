"""Known-positive recovery benchmark for DESeq2 outputs.

This reports overlap with an externally curated positive set. Unmatched hits are
not labelled biological false positives: the reference set may be incomplete.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


def evaluate_known_positive_recovery(
    results: list[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    fdr_threshold: float = 0.05,
    absolute_log2fc_threshold: float = 0.0,
    results_sha256: str = "",
    manifest_sha256: str = "",
) -> dict[str, Any]:
    if not 0 < fdr_threshold < 1:
        raise ValueError("fdr_threshold must be strictly between 0 and 1")
    if absolute_log2fc_threshold < 0 or not math.isfinite(absolute_log2fc_threshold):
        raise ValueError("absolute_log2fc_threshold must be finite and non-negative")
    accession = str(manifest.get("dataset_accession", "")).strip().upper()
    reference = str(manifest.get("reference", "")).strip()
    positives = manifest.get("known_positive_features")
    if not accession:
        raise ValueError("Benchmark manifest requires dataset_accession")
    if not reference.startswith("https://"):
        raise ValueError("Benchmark manifest requires an HTTPS reference URL")
    if not isinstance(positives, list) or not positives:
        raise ValueError("Benchmark manifest requires a non-empty known_positive_features list")
    if any(not isinstance(item, str) or not item.strip() for item in positives):
        raise ValueError("Known-positive feature identifiers must be non-empty strings")
    truth = {item.strip() for item in positives}
    if len(truth) != len(positives):
        raise ValueError("Known-positive feature identifiers must be unique")

    seen: set[str] = set()
    significant: set[str] = set()
    for row in results:
        feature = str(row.get("feature", "")).strip()
        if not feature or feature in seen:
            raise ValueError("DE results must contain unique, non-empty feature identifiers")
        seen.add(feature)
        padj = row.get("p_value_adjusted_bh")
        lfc = row.get("log2_fold_change")
        try:
            padj_value = float(padj) if padj is not None else math.nan
            lfc_value = float(lfc) if lfc is not None else math.nan
        except (TypeError, ValueError):
            continue
        if (math.isfinite(padj_value) and math.isfinite(lfc_value)
                and 0 <= padj_value <= fdr_threshold
                and abs(lfc_value) >= absolute_log2fc_threshold):
            significant.add(feature)

    tested_truth = truth & seen
    recovered = significant & truth
    missed = tested_truth - significant
    untested = truth - seen
    unmatched_hits = significant - truth
    precision = len(recovered) / len(significant) if significant else None
    recall = len(recovered) / len(truth) if truth else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall > 0
        else None
    )
    return {
        "benchmark_type": "curated_known_positive_recovery",
        "dataset_accession": accession,
        "reference": reference,
        "contrast": manifest.get("contrast", {}),
        "truth_set_version": manifest.get("truth_set_version", "unspecified"),
        "truth_set_size": len(truth),
        "features_tested": len(seen),
        "significant_hits": sorted(significant),
        "recovered_known_positives": sorted(recovered),
        "missed_tested_known_positives": sorted(missed),
        "known_positives_not_tested": sorted(untested),
        "significant_hits_not_in_reference_set": sorted(unmatched_hits),
        "recovered_count": len(recovered),
        "missed_count": len(missed),
        "untested_truth_count": len(untested),
        "unmatched_hit_count": len(unmatched_hits),
        "known_positive_recall": recall,
        "curated_set_overlap_precision": precision,
        "f1_against_curated_set": f1,
        "thresholds": {
            "adjusted_p_value_max": fdr_threshold,
            "absolute_log2_fold_change_min": absolute_log2fc_threshold,
        },
        "provenance": {
            "results_sha256": results_sha256,
            "manifest_sha256": manifest_sha256,
        },
        "interpretation": (
            "This is a known-positive recovery/overlap benchmark, not a complete "
            "classification benchmark. Features absent from the curated reference "
            "are unmatched hits, not proven biological false positives. Recall uses "
            "the full curated positive set; positives absent from the tested matrix "
            "are reported separately. Results depend on identifier harmonization, "
            "the truth-set curation, contrast comparability, and threshold choices. "
            "This score does not establish causal discovery or independent replication."
        ),
    }


def run_benchmark(results_path: str | Path, manifest_path: str | Path,
                  fdr_threshold: float = 0.05,
                  absolute_log2fc_threshold: float = 0.0) -> dict[str, Any]:
    results_file = Path(results_path)
    manifest_file = Path(manifest_path)
    raw_results = results_file.read_bytes()
    raw_manifest = manifest_file.read_bytes()
    manifest = json.loads(raw_manifest.decode("utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Benchmark manifest must be a JSON object")
    payload = json.loads(raw_results.decode("utf-8")) if results_file.suffix.lower() == ".json" else None
    if payload is not None:
        results = payload.get("results") if isinstance(payload, dict) else payload
    else:
        import csv
        import io
        from .geo_analysis import GEOExpressionAnalyzer
        table = GEOExpressionAnalyzer._table_text(raw_results.decode("utf-8-sig"))
        first = table.splitlines()[0] if table.splitlines() else ""
        delimiter = "\t" if first.count("\t") >= first.count(",") else ","
        rows = list(csv.DictReader(io.StringIO(table), delimiter=delimiter))
        results = []
        for row in rows:
            results.append({
                "feature": row.get("feature", ""),
                "log2_fold_change": row.get("log2_fold_change", row.get("log2FoldChange")),
                "p_value_adjusted_bh": row.get("p_value_adjusted_bh", row.get("padj")),
            })
    if not isinstance(results, list):
        raise ValueError("Results file must contain a list of DE result rows")
    return evaluate_known_positive_recovery(
        results, manifest,
        fdr_threshold=fdr_threshold,
        absolute_log2fc_threshold=absolute_log2fc_threshold,
        results_sha256=hashlib.sha256(raw_results).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest).hexdigest(),
    )
