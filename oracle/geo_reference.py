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
    mechanism: str = "MCAR",
) -> dict:
    """Stress-test row-median reconstruction under MCAR, MAR, or MNAR masking.

    MCAR uses a constant cell-wise probability. MAR depends on sample position
    (an observed design covariate). MNAR preferentially masks low values in each
    feature row. These are synthetic sensitivity analyses, not estimates of a
    dataset's actual missingness mechanism.
    """
    import random
    mechanism = mechanism.upper()
    if mechanism not in {"MCAR", "MAR", "MNAR"}:
        raise ValueError("mechanism must be MCAR, MAR, or MNAR.")
    if not 0 < missing_fraction < 1 or replicates < 1 or max_cells < 1:
        raise ValueError("missing_fraction must be in (0,1), replicates/max_cells positive.")
    source = Path(matrix_path)
    features, samples, matrix, _ = _read_matrix(source, max_cells)
    if any(v is None for row in matrix for v in row):
        raise ValueError("Simulation requires a complete numeric matrix as its reference.")
    if len(samples) < 2:
        raise ValueError("At least two samples are required.")
    rng = random.Random(seed)
    errors, signed = [], []
    masked_total = 0
    for _ in range(replicates):
        for row in matrix:
            n = len(row)
            if mechanism == "MNAR":
                order = sorted(range(n), key=lambda j: row[j])
                rank = [0.0] * n
                for k, j in enumerate(order):
                    rank[j] = k / max(1, n - 1)
            keep = []
            for j, value in enumerate(row):
                if mechanism == "MCAR":
                    probability = missing_fraction
                elif mechanism == "MAR":
                    # Missingness depends on observed sample-position covariate.
                    covariate = j / max(1, n - 1)
                    probability = missing_fraction * (0.5 + covariate)
                else:
                    # Low-abundance measurements are preferentially missing.
                    probability = missing_fraction * (1.5 - rank[j])
                probability = min(0.95, max(0.01, probability))
                keep.append(rng.random() >= probability)
            if not any(keep):
                keep[rng.randrange(n)] = True
            observed = sorted(v for v, retained in zip(row, keep) if retained)
            mid = len(observed) // 2
            median = observed[mid] if len(observed) % 2 else (observed[mid-1] + observed[mid]) / 2
            for original, retained in zip(row, keep):
                if not retained:
                    error = median - original
                    errors.append(abs(error))
                    signed.append(error)
                    masked_total += 1
    return {
        "benchmark_type": f"row_median_imputation_{mechanism.lower()}_stress_test",
        "missingness_mechanism": mechanism,
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "features": len(features), "samples": len(samples),
        "missing_fraction_requested": missing_fraction,
        "observed_masked_fraction": masked_total / (len(features) * len(samples) * replicates),
        "replicates": replicates, "seed": seed,
        "masked_values": masked_total,
        "mae": sum(errors) / len(errors) if errors else None,
        "mean_signed_error": sum(signed) / len(signed) if signed else None,
        "limitations": "Synthetic masking sensitivity test only. MAR uses sample-column position as an observed covariate; MNAR preferentially masks low values. The requested fraction is a base probability, not an exact realized fraction. These simulations do not identify the real missingness mechanism, assess batch-specific effects, or establish downstream differential-expression bias. Compare multiple imputation methods and real labelled missingness patterns before choosing a policy.",
    }


def evaluate_imputation_downstream_bias(
    matrix_path: str | Path, group_labels: dict[str, str], *,
    group_a: str, group_b: str, mechanism: str = "MCAR",
    missing_fraction: float = 0.1, replicates: int = 20,
    seed: int = 1729, fdr_threshold: float = 0.05,
    max_cells: int = 500_000,
) -> dict:
    """Compare complete-matrix DE statistics with row-median-imputed masked copies.

    The complete matrix is the synthetic reference, not biological ground truth.
    Values must be continuous measurements suitable for the Welch adapter.
    """
    import random
    from .geo_statistics import _welch_test, _benjamini_hochberg
    mechanism = mechanism.upper()
    if mechanism not in {"MCAR", "MAR", "MNAR"}:
        raise ValueError("mechanism must be MCAR, MAR, or MNAR.")
    if not 0 < missing_fraction < 1 or replicates < 1:
        raise ValueError("missing_fraction must be in (0,1) and replicates positive.")
    if not 0 < fdr_threshold < 1:
        raise ValueError("fdr_threshold must be between 0 and 1.")
    source = Path(matrix_path)
    features, samples, matrix, _ = _read_matrix(source, max_cells)
    if any(value is None for row in matrix for value in row):
        raise ValueError("Downstream bias simulation requires a complete reference matrix.")
    if set(group_labels) != set(samples):
        raise ValueError("group_labels must cover every matrix sample exactly.")
    if not group_a or not group_b or group_a == group_b:
        raise ValueError("Two distinct groups are required.")
    if set(group_labels.values()) != {group_a, group_b}:
        raise ValueError("Exactly the two requested groups must be present.")
    left = [i for i, sample in enumerate(samples) if group_labels[sample] == group_a]
    right = [i for i, sample in enumerate(samples) if group_labels[sample] == group_b]
    if min(len(left), len(right)) < 2:
        raise ValueError("At least two biological replicates per group are required.")
    def analyze(values):
        rows = []
        for feature, row in zip(features, values):
            a, b = [row[i] for i in left], [row[i] for i in right]
            t_stat, df, p_value = _welch_test(a, b)
            rows.append({"feature": feature, "log2fc": math.fsum(b)/len(b)-math.fsum(a)/len(a),
                         "p": p_value})
        order = sorted(range(len(rows)), key=lambda i: rows[i]["p"])
        adjusted = _benjamini_hochberg([rows[i]["p"] for i in order])
        for rank, index in enumerate(order):
            rows[index]["padj"] = adjusted[rank]
        return rows
    reference = analyze(matrix)
    rng = random.Random(seed)
    summaries = []
    for rep in range(replicates):
        masked_matrix = []
        masked_count = 0
        for row in matrix:
            if mechanism == "MNAR":
                order = sorted(range(len(row)), key=lambda j: row[j])
                rank = [0.0] * len(row)
                for k, j in enumerate(order):
                    rank[j] = k / max(1, len(row)-1)
            keep = []
            for j, value in enumerate(row):
                if mechanism == "MCAR":
                    probability = missing_fraction
                elif mechanism == "MAR":
                    probability = missing_fraction * (0.5 + j/max(1, len(row)-1))
                else:
                    probability = missing_fraction * (1.5-rank[j])
                keep.append(rng.random() >= min(.95, max(.01, probability)))
            if not any(keep):
                keep[rng.randrange(len(row))] = True
            observed = sorted(value for value, retained in zip(row, keep) if retained)
            middle = len(observed)//2
            median = observed[middle] if len(observed)%2 else (observed[middle-1]+observed[middle])/2
            masked_count += sum(not retained for retained in keep)
            masked_matrix.append([value if retained else median
                                  for value, retained in zip(row, keep)])
        candidate = analyze(masked_matrix)
        abs_lfc = [abs(x["log2fc"]-y["log2fc"]) for x,y in zip(reference,candidate)]
        abs_p = [abs(x["p"]-y["p"]) for x,y in zip(reference,candidate)]
        ref_hits = {x["feature"] for x in reference if x["padj"] <= fdr_threshold}
        cand_hits = {x["feature"] for x in candidate if x["padj"] <= fdr_threshold}
        summaries.append({
            "replicate": rep+1, "masked_cells": masked_count,
            "mean_absolute_log2fc_change": math.fsum(abs_lfc)/len(abs_lfc),
            "median_absolute_log2fc_change": sorted(abs_lfc)[len(abs_lfc)//2],
            "mean_absolute_raw_p_value_change": math.fsum(abs_p)/len(abs_p),
            "reference_significant_features": len(ref_hits),
            "imputed_significant_features": len(cand_hits),
            "significance_status_flips": len(ref_hits.symmetric_difference(cand_hits)),
            "new_imputed_significant_features": sorted(cand_hits-ref_hits),
            "lost_reference_significant_features": sorted(ref_hits-cand_hits),
        })
    return {
        "benchmark_type": f"synthetic_downstream_de_bias_{mechanism.lower()}",
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "features": len(features), "samples": len(samples),
        "contrast": {"group_a": group_a, "group_b": group_b},
        "missingness_mechanism": mechanism, "missing_fraction_base_probability": missing_fraction,
        "replicates": replicates, "seed": seed, "fdr_threshold": fdr_threshold,
        "reference_significant_features": sorted(
            row["feature"] for row in reference if row["padj"] <= fdr_threshold),
        "replicate_results": summaries,
        "mean_significance_status_flips": math.fsum(x["significance_status_flips"] for x in summaries)/replicates,
        "mean_absolute_log2fc_change": math.fsum(x["mean_absolute_log2fc_change"] for x in summaries)/replicates,
        "limitations": "This is a synthetic sensitivity experiment: the complete input matrix is treated as a reference, not as biological ground truth. It measures row-median imputation effects on a user-defined Welch/BH contrast only. It does not validate the measurement scale, model real missingness, account for batch/covariates, or establish DESeq2/limma behavior. Run on suitable continuous log2 data with a predeclared design; real labelled datasets and alternative imputation methods are still required.",
    }
