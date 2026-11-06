"""Independent reference checks and simulation diagnostics for GEO preprocessing.

These tools produce validation reports, not proof that a dataset or design is
biologically appropriate. The edgeR comparator requires a real R installation.
"""
from __future__ import annotations
import csv, hashlib, json, math, shutil, subprocess, tempfile
from pathlib import Path
from typing import Sequence
from .geo_normalization import _read_matrix, _tmm_factors

_EDGE_R = r'''
suppressPackageStartupMessages(library(edgeR))
args <- commandArgs(trailingOnly=TRUE)
x <- read.delim(args[1], row.names=1, check.names=FALSE)
y <- DGEList(counts=as.matrix(x))
y <- calcNormFactors(y, method="TMM")
cat(as.character(packageVersion("edgeR")), "\n", sep="")
write.table(data.frame(sample=colnames(y), factor=y$samples$norm.factors),
 file=args[2], sep="\t", quote=FALSE, row.names=FALSE)
'''

def compare_tmm_to_edger(matrix_path: str | Path, *, rscript: str = "Rscript",
                         timeout_seconds: int = 300, tolerance: float = 1e-6) -> dict:
    """Compare ORACLE TMM factors to edgeR calcNormFactors on identical raw counts."""
    if timeout_seconds < 1 or not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Timeout must be positive and tolerance finite/non-negative.")
    source = Path(matrix_path)
    features, samples, matrix, _ = _read_matrix(source, 5_000_000)
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            if value < 0 or not value.is_integer():
                raise ValueError(f"edgeR comparison requires integer counts ({features[i]}/{samples[j]}).")
    totals = [sum(row[j] for row in matrix) for j in range(len(samples))]
    if any(x <= 0 for x in totals):
        raise ValueError("Every sample must have positive library size.")
    oracle = _tmm_factors(matrix, totals)
    exe = shutil.which(rscript)
    if not exe:
        raise RuntimeError(f"Cannot find {rscript!r}; edgeR reference comparison was not run.")
    with tempfile.TemporaryDirectory(prefix="oracle-edger-check-") as tmp:
        root = Path(tmp); counts = root / "counts.tsv"; script = root / "check.R"; out = root / "factors.tsv"
        with counts.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(["feature", *samples])
            for feature, row in zip(features, matrix):
                writer.writerow([feature, *[int(v) for v in row]])
        script.write_text(_EDGE_R, encoding="utf-8")
        try:
            run = subprocess.run([exe, "--vanilla", str(script), str(counts), str(out)],
                                 capture_output=True, text=True, timeout=timeout_seconds, check=False)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("edgeR reference comparison timed out.") from exc
        if run.returncode:
            raise RuntimeError("edgeR reference comparison failed: " + (run.stderr or run.stdout)[-3000:])
        if not out.is_file():
            raise RuntimeError("edgeR did not write normalization factors.")
        with out.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        ref = {r["sample"]: float(r["factor"]) for r in rows}
        if set(ref) != set(samples) or any(not math.isfinite(v) or v <= 0 for v in ref.values()):
            raise RuntimeError("edgeR returned invalid or incomplete factors.")
        edge = [ref[s] for s in samples]
        if abs(math.prod(edge) - 1.0) > 1e-5:
            raise RuntimeError("edgeR factors are not geometric-mean normalized.")
    diffs = {s: abs(a-b) for s, a, b in zip(samples, oracle, edge)}
    return {
        "comparison": "ORACLE TMM vs edgeR::calcNormFactors(method='TMM')",
        "edgeR_version": (run.stdout or "").strip(),
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "samples": samples,
        "oracle_factors": dict(zip(samples, oracle)),
        "edgeR_factors": ref,
        "absolute_factor_differences": diffs,
        "max_absolute_difference": max(diffs.values()),
        "tolerance": tolerance,
        "within_tolerance": max(diffs.values()) <= tolerance,
        "limitations": "Same matrix and default TMM method are compared. Differences can reflect implementation details, filtering/zero handling, or reference selection. Passing is not a biological validation or substitute for inspecting edgeR settings.",
    }

def evaluate_row_median_imputation(
    matrix_path: str | Path, *, missing_fraction: float = 0.1,
    replicates: int = 20, seed: int = 1729, max_cells: int = 500_000,
) -> dict:
    """Mask observed values reproducibly and measure row-median reconstruction error.

    This is a within-matrix stress test under MCAR masking only. It cannot
    establish performance under MAR/MNAR or recover the unknown true values
    in naturally missing cells.
    """
    import random
    if not 0 < missing_fraction < 1 or replicates < 1 or max_cells < 1:
        raise ValueError("missing_fraction must be in (0,1), replicates/max_cells positive.")
    source = Path(matrix_path)
    features, samples, matrix, _ = _read_matrix(source, max_cells)
    if any(v is None for row in matrix for v in row):
        raise ValueError("Simulation requires a complete numeric matrix as its reference.")
    if len(samples) < 2:
        raise ValueError("At least two samples are required.")
    rng = random.Random(seed)
    errors, biases, per_feature = [], [], []
    for _ in range(replicates):
        masked = []
        for row in matrix:
            keep = [rng.random() >= missing_fraction for _ in row]
            if not any(keep):
                keep[rng.randrange(len(row))] = True
            observed_sorted = sorted(v for v, retained in zip(row, keep) if retained)
            mid = len(observed_sorted)//2
            median = (observed_sorted[mid] if len(observed_sorted)%2
                      else (observed_sorted[mid-1]+observed_sorted[mid])/2)
            masked.extend((median-v) for v, retained in zip(row, keep) if not retained)
        if masked:
            errors.extend(abs(v) for v in masked)
            biases.extend(masked)
    mae = sum(errors)/len(errors) if errors else None
    bias = sum(biases)/len(biases) if biases else None
    return {
        "benchmark_type": "row_median_imputation_mcar_stress_test",
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "features": len(features), "samples": len(samples),
        "missing_fraction_requested": missing_fraction,
        "replicates": replicates, "seed": seed,
        "masked_values": len(errors), "mae": mae, "mean_signed_error": bias,
        "limitations": "Synthetic MCAR masking of observed entries only. Does not assess MAR/MNAR, batch-dependent missingness, downstream differential-expression bias, or suitability of median imputation. Compare alternative methods and real missingness mechanisms before selecting an imputation policy.",
    }
