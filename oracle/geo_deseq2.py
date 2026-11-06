"""Optional DESeq2 adapter for explicitly designed raw-count GEO matrices.

Requires Rscript and the Bioconductor DESeq2 package at runtime. This module
never substitutes a t-test for count-aware RNA-seq inference.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Mapping

from .geo_analysis import GEOExpressionAnalyzer


_DESEQ2_SCRIPT = r'''
args <- commandArgs(trailingOnly=TRUE)
input_path <- args[[1]]
metadata_path <- args[[2]]
output_path <- args[[3]]
group_a <- args[[4]]
group_b <- args[[5]]
covariate_names <- if (length(args) >= 6 && nzchar(args[[6]])) strsplit(args[[6]], ",", fixed=TRUE)[[1]] else character(0)
suppressPackageStartupMessages({
  if (!requireNamespace("DESeq2", quietly=TRUE)) {
    stop("DESeq2 is not installed. Install it with BiocManager::install('DESeq2').")
  }
})
counts <- read.delim(input_path, row.names=1, check.names=FALSE)
metadata <- read.delim(metadata_path, row.names=1, check.names=FALSE)
if (!identical(colnames(counts), rownames(metadata))) stop("Sample order mismatch.")
metadata$group <- factor(metadata$group, levels=c(group_a, group_b))
if (any(is.na(metadata$group))) stop("Unexpected group label.")
for (name in covariate_names) {
  metadata[[name]] <- factor(metadata[[name]])
  if (any(is.na(metadata[[name]])) || nlevels(metadata[[name]]) < 2) {
    stop(paste("Invalid or constant covariate:", name))
  }
}
design_terms <- c(covariate_names, "group")
design_formula <- as.formula(paste("~", paste(design_terms, collapse=" + ")))
design_matrix <- model.matrix(design_formula, data=metadata)
if (qr(design_matrix)$rank < ncol(design_matrix)) {
  stop("Design matrix is rank deficient; group and covariates are confounded.")
}
dds <- DESeq2::DESeqDataSetFromMatrix(
  countData=as.matrix(counts), colData=metadata, design=design_formula
)
dds <- dds[rowSums(DESeq2::counts(dds)) > 0,]
if (nrow(dds) == 0) stop("No non-zero features remain.")
dds <- DESeq2::DESeq(dds, quiet=TRUE)
res <- DESeq2::results(dds, contrast=c("group", group_b, group_a), alpha=0.05)
out <- as.data.frame(res)
out$feature <- rownames(out)
out <- out[, c("feature", "baseMean", "log2FoldChange", "lfcSE", "stat", "pvalue", "padj")]
write.table(out, file=output_path, sep="\t", quote=FALSE, row.names=FALSE, na="NA")
cat(as.character(getRversion()), "\t", as.character(utils::packageVersion("DESeq2")), sep="")
'''


class DESeq2UnavailableError(RuntimeError):
    """Rscript or the DESeq2 Bioconductor package is unavailable."""


class GEOCountAnalyzer:
    """Run DESeq2 on integer raw counts with a fully explicit two-group design."""

    def analyze(
        self,
        path: str | Path,
        group_labels: Mapping[str, str],
        group_a: str,
        group_b: str,
        rscript: str = "Rscript",
        timeout_seconds: int = 900,
        min_replicates: int = 2,
        max_features: int = 100_000,
        max_cells: int = 5_000_000,
        covariates: Mapping[str, Mapping[str, str]] | None = None,
    ) -> dict:
        if not group_a or not group_b or group_a == group_b:
            raise ValueError("Two distinct non-empty contrast groups are required.")
        if min_replicates < 2:
            raise ValueError("At least two biological replicates per group are required.")
        if timeout_seconds < 1:
            raise ValueError("timeout_seconds must be positive.")
        executable = shutil.which(rscript)
        if executable is None:
            raise DESeq2UnavailableError(
                f"Cannot find {rscript!r}. Install R and make Rscript available on PATH."
            )

        matrix_path = Path(path)
        text = GEOExpressionAnalyzer()._read_text(matrix_path)
        table = GEOExpressionAnalyzer._table_text(text)
        first = table.splitlines()[0] if table.splitlines() else ""
        delimiter = "\t" if first.count("\t") >= first.count(",") else ","
        reader = csv.reader(io.StringIO(table), delimiter=delimiter)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("Expression matrix has no header.") from exc
        samples = [item.strip() for item in header[1:]]
        if not samples or any(not sample for sample in samples) or len(set(samples)) != len(samples):
            raise ValueError("Matrix must contain unique, non-empty sample column names.")
        if set(group_labels) != set(samples):
            missing = sorted(set(samples) - set(group_labels))
            extra = sorted(set(group_labels) - set(samples))
            raise ValueError(
                f"Group labels must cover matrix samples exactly; missing={missing}, extra={extra}."
            )
        unexpected = sorted(set(group_labels.values()) - {group_a, group_b})
        if unexpected:
            raise ValueError(f"Only the two requested groups may be present; found {unexpected}.")
        validated_covariates: dict[str, dict[str, str]] = {}
        for name, assignments in (covariates or {}).items():
            if (not isinstance(name, str) or not name
                    or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", name)
                    or name == "group" or name in {"sample", "feature"}):
                raise ValueError(f"Invalid or reserved covariate name: {name!r}.")
            if name in validated_covariates or not isinstance(assignments, Mapping):
                raise ValueError(f"Covariate {name!r} must map every sample to a category.")
            if set(assignments) != set(samples):
                raise ValueError(f"Covariate {name!r} must cover matrix samples exactly.")
            values = {}
            for sample in samples:
                value = assignments[sample]
                if not isinstance(value, str) or not value.strip() or len(value.strip()) > 100:
                    raise ValueError(f"Covariate {name!r} has an invalid value for {sample!r}.")
                values[sample] = value.strip()
            if len(set(values.values())) < 2:
                raise ValueError(f"Covariate {name!r} must contain at least two categories.")
            validated_covariates[name] = values

        left_samples = [sample for sample in samples if group_labels[sample] == group_a]
        right_samples = [sample for sample in samples if group_labels[sample] == group_b]
        if len(left_samples) < min_replicates or len(right_samples) < min_replicates:
            raise ValueError(
                f"Insufficient biological replicates: {group_a}={len(left_samples)}, "
                f"{group_b}={len(right_samples)}; need at least {min_replicates} each."
            )

        features: list[str] = []
        rows: list[list[int]] = []
        seen: set[str] = set()
        total_cells = 0
        for line_number, row in enumerate(reader, start=2):
            if not row or not any(cell.strip() for cell in row):
                continue
            if len(row) != len(samples) + 1:
                raise ValueError(f"Malformed matrix row {line_number}: expected {len(samples) + 1} columns.")
            feature = row[0].strip()
            if not feature:
                raise ValueError(f"Empty feature identifier on row {line_number}.")
            if feature in seen:
                raise ValueError(f"Duplicate feature identifier {feature!r}; rows must be unique.")
            seen.add(feature)
            values: list[int] = []
            for column, raw in enumerate(row[1:], start=1):
                value = GEOExpressionAnalyzer._number(raw)
                if value is None:
                    raise ValueError(
                        f"Missing/non-numeric count for feature {feature!r}, sample {samples[column - 1]!r}."
                    )
                if value < 0 or not math.isfinite(value) or not value.is_integer():
                    raise ValueError(
                        f"Raw counts must be finite, non-negative integers; invalid value {raw!r} "
                        f"for feature {feature!r}, sample {samples[column - 1]!r}."
                    )
                values.append(int(value))
            features.append(feature)
            rows.append(values)
            total_cells += len(values)
            if len(features) > max_features:
                raise ValueError(f"Matrix exceeds the {max_features}-feature DESeq2 limit.")
            if total_cells > max_cells:
                raise ValueError(f"Matrix exceeds the {max_cells}-cell DESeq2 limit.")
        if not rows:
            raise ValueError("Expression matrix contains no feature rows.")

        matrix_sha256 = hashlib.sha256(matrix_path.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(prefix="oracle-deseq2-") as workdir:
            root = Path(workdir)
            counts_path = root / "counts.tsv"
            metadata_path = root / "samples.tsv"
            script_path = root / "run_deseq2.R"
            output_path = root / "results.tsv"
            with counts_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
                writer.writerow(["feature", *samples])
                for feature, values in zip(features, rows):
                    writer.writerow([feature, *values])
            with metadata_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
                covariate_names = list(validated_covariates)
                writer.writerow(["sample", "group", *covariate_names])
                for sample in samples:
                    writer.writerow([
                        sample, group_labels[sample],
                        *(validated_covariates[name][sample] for name in covariate_names),
                    ])
            script_path.write_text(_DESEQ2_SCRIPT, encoding="utf-8")
            try:
                completed = subprocess.run(
                    [executable, "--vanilla", str(script_path), str(counts_path),
                     str(metadata_path), str(output_path), group_a, group_b,
                     ",".join(validated_covariates)],
                    capture_output=True, text=True, timeout=timeout_seconds, check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(f"DESeq2 analysis exceeded {timeout_seconds} seconds.") from exc
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout or "No R error details returned.").strip()
                if "DESeq2 is not installed" in detail:
                    raise DESeq2UnavailableError(
                        "R is available, but DESeq2 is missing. Install it with "
                        "BiocManager::install('DESeq2')."
                    )
                raise RuntimeError(f"DESeq2 failed (exit {completed.returncode}): {detail[-4000:]}")
            if not output_path.exists():
                raise RuntimeError("DESeq2 completed without producing its results file.")
            version_parts = (completed.stdout or "").strip().split("\t")
            if len(version_parts) != 2:
                raise RuntimeError("DESeq2 did not return verifiable R and package versions.")
            results: list[dict] = []
            with output_path.open("r", encoding="utf-8", newline="") as handle:
                for item in csv.DictReader(handle, delimiter="\t"):
                    def number(key: str) -> float | None:
                        raw = item.get(key, "")
                        if raw in {"", "NA", "NaN"}:
                            return None
                        value = float(raw)
                        return value if math.isfinite(value) else None
                    results.append({
                        "feature": item["feature"],
                        "base_mean": number("baseMean"),
                        "log2_fold_change": number("log2FoldChange"),
                        "lfc_se": number("lfcSE"),
                        "wald_statistic": number("stat"),
                        "p_value": number("pvalue"),
                        "p_value_adjusted_bh": number("padj"),
                    })
        results.sort(key=lambda item: (
            item["p_value_adjusted_bh"] is None,
            item["p_value_adjusted_bh"] if item["p_value_adjusted_bh"] is not None else 1.0,
            item["feature"],
        ))
        return {
            "method": "DESeq2 negative-binomial GLM; Wald test; independent filtering; Benjamini-Hochberg FDR",
            "contrast": {
                "group_a": group_a, "group_b": group_b,
                "direction": f"{group_b} vs {group_a}",
                "design_formula": "~ " + " + ".join([*validated_covariates, "group"]),
                "covariates": {name: sorted(set(values.values())) for name, values in validated_covariates.items()},
            },
            "normalization": "DESeq2 median-of-ratios size-factor normalization (DESeq2 default)",
            "sample_groups": {group_a: left_samples, group_b: right_samples},
            "sample_count": len(samples),
            "features_input": len(features),
            "features_returned": len(results),
            "features_with_adjusted_p_value": sum(item["p_value_adjusted_bh"] is not None for item in results),
            "matrix_sha256": matrix_sha256,
            "software": {"r": version_parts[0], "deseq2": version_parts[1]},
            "results": results,
            "limitations": (
                "Requires raw, unnormalized integer read counts and independent biological replicates. "
                "The design includes the explicitly supplied categorical covariates, if any; no covariates are inferred. "
                "No automatic sample exclusion or group inference is performed. Inspect library sizes, "
                "sample QC, study design, and DESeq2 diagnostics before biological interpretation. "
                "Adjusted p-values may be unavailable for filtered or all-zero features. "
                "Results are associations, not causal or independently validated discoveries."
            ),
        }
