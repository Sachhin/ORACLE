"""Explicit, reproducible GEO matrix normalization helpers.

Quantile normalization is intended for continuous microarray-like matrices.
CPM/log2-CPM is a library-size transform for raw integer counts and is not
an inferential RNA-seq model; use DESeq2 for count-aware differential testing.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import math
import platform
import tempfile
from pathlib import Path


def _table_text(text: str) -> str:
    lines = text.splitlines()
    begin = next((i for i, line in enumerate(lines)
                  if line.strip().lower() == "!series_matrix_table_begin"), None)
    if begin is not None:
        end = next((i for i in range(begin + 1, len(lines))
                    if lines[i].strip().lower() == "!series_matrix_table_end"), len(lines))
        return "\n".join(lines[begin + 1:end])
    return "\n".join(line for line in lines if line.strip()
                       and not line.lstrip().startswith(("!", "#")))


def _read_matrix(path: Path, max_cells: int, allow_missing: bool = False) -> tuple[list[str], list[str], list[list[float | None]], str]:
    opener = gzip.open if path.name.lower().endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8-sig", errors="strict", newline="") as handle:
        text = handle.read(100_000_001)
    if len(text.encode("utf-8")) > 100_000_000:
        raise ValueError("Input matrix exceeds 100 MB uncompressed limit.")
    table = _table_text(text)
    if not table.strip():
        raise ValueError("No tabular expression matrix was found.")
    first = table.splitlines()[0]
    delimiter = "\t" if first.count("\t") >= first.count(",") else ","
    reader = csv.reader(table.splitlines(), delimiter=delimiter)
    header = next(reader, [])
    samples = [value.strip() for value in header[1:]]
    if not samples or any(not value for value in samples) or len(set(samples)) != len(samples):
        raise ValueError("Matrix must have unique non-empty sample columns.")
    features, matrix, seen = [], [], set()
    for line_number, row in enumerate(reader, start=2):
        if not row or not any(value.strip() for value in row):
            continue
        if row[0].strip().lower() in {"id_ref", "feature_id", "gene_id"}:
            continue
        if len(row) != len(samples) + 1:
            raise ValueError(f"Malformed matrix row {line_number}: expected {len(samples)+1} columns.")
        feature = row[0].strip()
        if not feature or feature in seen:
            raise ValueError(f"Empty or duplicate feature identifier on row {line_number}.")
        seen.add(feature)
        values = []
        for sample, raw in zip(samples, row[1:]):
            if allow_missing and raw.strip().lower() in {"", "na", "nan", "null", "n/a", "."}:
                values.append(None)
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Missing/non-numeric value for {feature}/{sample}.") from exc
            if not math.isfinite(value):
                raise ValueError(f"Non-finite value for {feature}/{sample}.")
            values.append(value)
        features.append(feature)
        matrix.append(values)
        if len(features) * len(samples) > max_cells:
            raise ValueError(f"Matrix exceeds the {max_cells}-cell normalization limit.")
    if not matrix:
        raise ValueError("Matrix contains no feature rows.")
    return features, samples, matrix, delimiter


def _quantile_normalize(matrix: list[list[float]]) -> list[list[float]]:
    sample_count = len(matrix[0])
    feature_count = len(matrix)
    sorted_columns = []
    for column in range(sample_count):
        sorted_columns.append(sorted(matrix[row][column] for row in range(feature_count)))
    target = [
        sum(sorted_columns[column][rank] for column in range(sample_count)) / sample_count
        for rank in range(feature_count)
    ]
    normalized = [[0.0] * sample_count for _ in range(feature_count)]
    for column in range(sample_count):
        ordered = sorted((matrix[row][column], row) for row in range(feature_count))
        index = 0
        while index < feature_count:
            end = index + 1
            while end < feature_count and ordered[end][0] == ordered[index][0]:
                end += 1
            tied_value = sum(target[index:end]) / (end - index)
            for _, row_index in ordered[index:end]:
                normalized[row_index][column] = tied_value
            index = end
    return normalized



def _tmm_factors(matrix, totals):
    def q(values, p):
        v = sorted(values); x = (len(v)-1)*p; lo=int(math.floor(x)); hi=int(math.ceil(x))
        return v[lo] + (v[hi]-v[lo])*(x-lo)
    upper=[q([r[j]/totals[j]*1e6 for r in matrix], .75) for j in range(len(totals))]
    ref=min(range(len(totals)), key=lambda j: abs(upper[j]-sum(upper)/len(upper)))
    factors=[1.0]*len(totals)
    for j in range(len(totals)):
        if j==ref: continue
        vals=[]
        for r in matrix:
            a,b=r[ref],r[j]
            if a<=0 or b<=0: continue
            m=math.log2((b/totals[j])/(a/totals[ref]))
            v=(totals[j]-b)/(totals[j]*b)+(totals[ref]-a)/(totals[ref]*a)
            if v>0 and math.isfinite(m): vals.append((m,1.0/v))
        if len(vals)<3: raise ValueError('TMM requires three shared positive-count features.')
        vals.sort(key=lambda x:x[0]); lo=int(len(vals)*.30); hi=int(math.ceil(len(vals)*.70))
        kept=vals[lo:hi]
        if not kept: raise ValueError('TMM trimming removed all features; matrix too small.')
        factors[j]=2**(sum(m*w for m,w in kept)/sum(w for _,w in kept))
    gm=math.exp(sum(math.log(x) for x in factors)/len(factors))
    return [x/gm for x in factors]

def normalize_geo_matrix(
    input_path: str | Path,
    output_path: str | Path,
    method: str,
    prior_count: float = 0.5,
    max_cells: int = 2_000_000,
) -> dict:
    """Normalize a rectangular GEO matrix and write a new TSV plus provenance report."""
    if method not in {"quantile", "quantile-row-median", "cpm", "log2-cpm", "tmm-cpm", "tmm-log2-cpm"}:
        raise ValueError("method must be quantile, cpm, or log2-cpm.")
    if not math.isfinite(prior_count) or prior_count <= 0:
        raise ValueError("prior_count must be a finite positive number.")
    if max_cells < 1:
        raise ValueError("max_cells must be positive.")
    source = Path(input_path)
    destination = Path(output_path)
    if source.resolve() == destination.resolve():
        raise ValueError("Output path must differ from input; the raw matrix is preserved.")
    features, samples, matrix, _ = _read_matrix(source, max_cells, allow_missing=(method == "quantile-row-median"))
    missing_mask = [[value is None for value in row] for row in matrix]
    missing_count = sum(sum(row) for row in missing_mask)
    imputation_values = {}
    if method == "quantile-row-median":
        for index, row in enumerate(matrix):
            observed = sorted(value for value in row if value is not None)
            if not observed:
                raise ValueError(f"Feature {features[index]} has no observed values; cannot median-impute.")
            middle = len(observed) // 2
            median = observed[middle] if len(observed) % 2 else (observed[middle-1] + observed[middle]) / 2
            imputation_values[features[index]] = median
            matrix[index] = [median if value is None else value for value in row]
    totals = [sum(row[column] for row in matrix) for column in range(len(samples))]
    effective_totals = list(totals)
    tmm_factors = [1.0] * len(samples)
    if method in {"cpm", "log2-cpm", "tmm-cpm", "tmm-log2-cpm"}:
        for row_index, row in enumerate(matrix):
            for column, value in enumerate(row):
                if value < 0 or not value.is_integer():
                    raise ValueError(
                        f"{method} requires non-negative integer raw counts; invalid "
                        f"value for {features[row_index]}/{samples[column]}."
                    )
        if any(total <= 0 for total in totals):
            raise ValueError("Every sample must have a positive library size.")
        normalized = []
        effective_totals = list(totals)
        tmm_factors = [1.0] * len(samples)
        if method in {"tmm-cpm", "tmm-log2-cpm"}:
            tmm_factors = _tmm_factors(matrix, totals)
            effective_totals = [n * f for n, f in zip(totals, tmm_factors)]
        for row in matrix:
            values = []
            for column, value in enumerate(row):
                cpm = value / effective_totals[column] * 1_000_000.0
                use_log = method in {"log2-cpm", "tmm-log2-cpm"}
                values.append(math.log2(cpm + prior_count) if use_log else cpm)
            normalized.append(values)
    else:
        normalized = _quantile_normalize(matrix)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["feature", *samples])
        for feature, row in zip(features, normalized):
            writer.writerow([feature, *(format(value, ".12g") for value in row)])
    input_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    missing_mask_path = None
    missing_mask_hash = None
    if method == "quantile-row-median":
        mask_destination = Path(str(destination) + ".missing-mask.tsv")
        with mask_destination.open("w", encoding="utf-8", newline="") as mask_handle:
            mask_writer = csv.writer(mask_handle, delimiter="\\t", lineterminator="\\n")
            mask_writer.writerow(["feature", *samples])
            for feature, row in zip(features, missing_mask):
                mask_writer.writerow([feature, *[int(value) for value in row]])
        missing_mask_path = str(mask_destination)
        missing_mask_hash = hashlib.sha256(mask_destination.read_bytes()).hexdigest()
    output_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
    return {
        "method": method,
        "input_path": str(source),
        "output_path": str(destination),
        "input_sha256": input_hash,
        "output_sha256": output_hash,
        "features": len(features),
        "missing_cells": missing_count,
        "missing_mask_path": missing_mask_path,
        "missing_mask_sha256": missing_mask_hash,
        "row_median_imputation_values": imputation_values if method == "quantile-row-median" else None,
        "samples": len(samples),
        "sample_library_sizes": dict(zip(samples, totals)),
        "tmm_normalization_factors": dict(zip(samples, tmm_factors)) if method.startswith("tmm-") else None,
        "effective_library_sizes": dict(zip(samples, effective_totals)),
        "prior_count": prior_count if method in {"log2-cpm", "tmm-log2-cpm"} else None,
        "limitations": (
            "Row-median imputation is explicit and emits a hashed missingness mask; it can bias distributions and is not a substitute for a missing-data model. Quantile normalization assumes comparable sample distributions and is intended for "
            "continuous microarray-like measurements; do not apply it blindly to raw RNA-seq counts. "
            "CPM/log2-CPM is a library-size transform only, not TMM, variance-stabilizing "
            "transformation, DESeq2, or a differential-expression test. Confirm platform, assay, "
            "background correction, probe annotation, and study design before interpretation. "
            "Input data are never overwritten."
        ),
    }



def verify_geo_normalization_rerun(
    input_path: str | Path,
    output_path: str | Path,
    method: str,
    prior_count: float = 0.5,
    max_cells: int = 2_000_000,
) -> dict:
    """Run the same deterministic transform twice and compare byte-level outputs.

    This verifies same-runtime repeatability only; it is not an independent
    implementation, cross-platform reproducibility study, or scientific validation.
    """
    destination = Path(output_path)
    first = normalize_geo_matrix(
        input_path, destination, method, prior_count=prior_count, max_cells=max_cells,
    )
    with tempfile.TemporaryDirectory(prefix="oracle-geo-rerun-") as temporary:
        second_path = Path(temporary) / "repeat.tsv"
        second = normalize_geo_matrix(
            input_path, second_path, method, prior_count=prior_count, max_cells=max_cells,
        )
    identical = first["output_sha256"] == second["output_sha256"]
    return {
        "method": method,
        "input_sha256": first["input_sha256"],
        "first_output_sha256": first["output_sha256"],
        "repeat_output_sha256": second["output_sha256"],
        "byte_identical": identical,
        "python_version": platform.python_version(),
        "verification_scope": (
            "Same-runtime deterministic rerun only. This does not establish independent "
            "implementation agreement, cross-platform reproducibility, or biological validity."
        ),
        "output_path": str(destination),
    }
