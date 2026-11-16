#!/usr/bin/env python3
"""Reproduce the published 8-mRPG/7-cRPG signature in Leiden GSE16717.

Uses only public processed GEO expression data and GPL2895 annotations. The
analysis is exploratory and reports group differences without claiming causal
or independent-from-the-2026-paper validation.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import ttest_ind

GSE_URL = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE16nnn/GSE16717/matrix/GSE16717_series_matrix.txt.gz"
GPL_URL = "https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL2nnn/GPL2895/annot/GPL2895.annot.gz"
M_RPG = ["MRPL3", "MRPL32", "MRPL42", "MRPL45", "MRPL50", "MRPS10", "MRPS33", "MRPS35"]
C_RPG = ["RPL10A", "RPL22", "RPL4", "RPL5", "RPS13", "RPS23", "RPS6"]
TARGETS = set(M_RPG + C_RPG)


def download(url: str, target: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "ORACLE-GSE16717-signature-audit/1.0"})
    with urllib.request.urlopen(req, timeout=900) as response, target.open("wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_platform(path: Path) -> dict[str, list[str]]:
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
        lines = handle.readlines()
    header_index = None
    header = None
    for i, line in enumerate(lines):
        row = next(csv.reader([line], delimiter="\t", quotechar='"'))
        lowered = [x.strip().lower() for x in row]
        if any(x in {"gene symbol", "gene_symbol"} for x in lowered) and lowered[0] in {"id", "id_ref"}:
            header_index, header = i, row
            break
    if header_index is None or header is None:
        raise RuntimeError("Could not locate GPL2895 annotation header with ID and Gene Symbol")
    symbol_idx = next(i for i, x in enumerate(header) if x.strip().lower() in {"gene symbol", "gene_symbol"})
    probe_idx = 0
    mapping: dict[str, list[str]] = {}
    for line in lines[header_index + 1:]:
        if not line.strip() or line.startswith("#") or line.startswith("["):
            continue
        row = next(csv.reader([line], delimiter="\t", quotechar='"'))
        if len(row) <= max(symbol_idx, probe_idx):
            continue
        probe = row[probe_idx].strip()
        symbols = re.split(r"\s*(?:///|//|;|\|)\s*", row[symbol_idx].strip())
        for symbol in symbols:
            symbol = symbol.strip().upper()
            if symbol in TARGETS:
                mapping.setdefault(probe, []).append(symbol)
    return mapping


def parse_series_matrix(path: Path):
    sample_ids = []
    titles = []
    characteristics: dict[str, list[str]] = {}
    matrix_start = None
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
        for line in handle:
            if line.startswith("!Sample_geo_accession"):
                sample_ids = next(csv.reader([line], delimiter="\t", quotechar='"'))[1:]
            elif line.startswith("!Sample_title"):
                titles = next(csv.reader([line], delimiter="\t", quotechar='"'))[1:]
            elif line.startswith("!Sample_characteristics_ch1"):
                row = next(csv.reader([line], delimiter="\t", quotechar='"'))[1:]
                characteristics.setdefault("characteristics", []).append(row)
            elif line.startswith("!series_matrix_table_begin"):
                matrix_start = handle.tell()
                break
        if not sample_ids:
            raise RuntimeError("GSE16717 series matrix contains no !Sample_geo_accession row")
        if len(titles) != len(sample_ids):
            titles = [""] * len(sample_ids)
        if matrix_start is None:
            raise RuntimeError("GSE16717 series matrix table start not found")

        expression_by_gene: dict[str, list[list[float]]] = {g: [] for g in TARGETS}
        for row in csv.reader(handle, delimiter="\t", quotechar='"'):
            if not row or row[0].startswith("!series_matrix_table_end"):
                break
            if row[0] == "ID_REF" or len(row) < len(sample_ids) + 1:
                continue
            values = []
            for item in row[1:len(sample_ids) + 1]:
                try:
                    values.append(float(item))
                except ValueError:
                    values.append(float("nan"))
            # Probe-to-gene mapping is applied after reading rows by caller.
            yield_row = (row[0].strip(), values)
            yield yield_row, sample_ids, titles, characteristics


def build_complete_panel_scores(z_values: dict[str, np.ndarray]):
    """Only calculate a composite score when every pre-specified gene is present."""
    scores = {}
    status = {}
    for panel_name, genes in (("mRPG_8", M_RPG), ("cRPG_7", C_RPG)):
        missing = [gene for gene in genes if gene not in z_values]
        status[panel_name] = {
            "expected_genes": len(genes),
            "present_genes": len(genes) - len(missing),
            "missing_genes": missing,
            "status": "COMPLETE" if not missing else "INCOMPLETE_NO_COMPOSITE_SCORE",
        }
        if not missing:
            scores[panel_name] = np.nanmean(np.vstack([z_values[g] for g in genes]), axis=0)
    return scores, status


def bh_adjust(pvalues: list[float]) -> list[float]:
    if not pvalues:
        return []
    arr = np.asarray(pvalues, dtype=float)
    order = np.argsort(arr)
    ranked = arr[order]
    n = len(arr)
    adjusted = np.minimum.accumulate((ranked * n / np.arange(1, n + 1))[::-1])[::-1]
    out = np.empty(n, dtype=float)
    out[order] = np.clip(adjusted, 0, 1)
    return out.tolist()


def parse_sample_group(title: str, chars: list[str]) -> tuple[str, float | None, str]:
    text = " ".join([title] + chars).lower()
    if "long-lived sib" in text or "long lived sib" in text:
        group = "long_lived_sibling"
    elif "offspring" in text:
        group = "offspring"
    elif "control" in text or "partner" in text or "spouse" in text:
        group = "control"
    else:
        group = "unknown"
    age = None
    sex = ""
    for item in chars:
        match = re.search(r"age\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)", item, flags=re.I)
        if match:
            age = float(match.group(1))
        match = re.search(r"(?:sex|gender)\s*[:=]\s*([A-Za-z]+)", item, flags=re.I)
        if match:
            sex = match.group(1).lower()
    return group, age, sex


def main() -> None:
    out = Path("artifacts/gse16717-mrpg-validation")
    raw = out / "raw"
    out.mkdir(parents=True, exist_ok=True)
    raw.mkdir(exist_ok=True)
    matrix_path = raw / "GSE16717-GPL2895_series_matrix.txt.gz"
    platform_path = raw / "GPL2895.annot.gz"
    download(GSE_URL, matrix_path)
    download(GPL_URL, platform_path)

    probe_to_genes = parse_platform(platform_path)
    sample_ids = []
    titles = []
    chars: dict[str, list[list[str]]] = {}
    per_gene_probe_values: dict[str, list[list[float]]] = {g: [] for g in TARGETS}
    matrix_started = False
    with gzip.open(matrix_path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
        for line in handle:
            if line.startswith("!Sample_geo_accession"):
                sample_ids = next(csv.reader([line], delimiter="\t", quotechar='"'))[1:]
            elif line.startswith("!Sample_title"):
                titles = next(csv.reader([line], delimiter="\t", quotechar='"'))[1:]
            elif line.startswith("!Sample_characteristics_ch1"):
                row = next(csv.reader([line], delimiter="\t", quotechar='"'))[1:]
                chars.setdefault("rows", []).append(row)
            elif line.startswith("!series_matrix_table_begin"):
                matrix_started = True
                break
        if not matrix_started or not sample_ids:
            raise RuntimeError("GSE16717 series matrix metadata/table not found")
        if len(titles) != len(sample_ids):
            titles = [""] * len(sample_ids)
        for row in csv.reader(handle, delimiter="\t", quotechar='"'):
            if not row or row[0].startswith("!series_matrix_table_end"):
                break
            probe = row[0].strip()
            genes = probe_to_genes.get(probe, [])
            if not genes:
                continue
            values = []
            for item in row[1:len(sample_ids) + 1]:
                try:
                    values.append(float(item))
                except ValueError:
                    values.append(float("nan"))
            for gene in set(genes):
                per_gene_probe_values[gene].append(values)

    sample_chars = [[] for _ in sample_ids]
    for row in chars.get("rows", []):
        for i, value in enumerate(row[:len(sample_ids)]):
            sample_chars[i].append(value)
    sample_meta = []
    for i, gsm in enumerate(sample_ids):
        group, age, sex = parse_sample_group(titles[i], sample_chars[i])
        sample_meta.append({"gsm": gsm, "title": titles[i], "group": group, "age": age, "sex": sex})

    gene_values = {}
    missing_genes = []
    for gene in M_RPG + C_RPG:
        probe_rows = per_gene_probe_values.get(gene, [])
        if not probe_rows:
            missing_genes.append(gene)
            continue
        arr = np.asarray(probe_rows, dtype=float)
        gene_values[gene] = np.nanmedian(arr, axis=0)

    if len(sample_ids) != 150:
        raise RuntimeError(f"Expected 150 GEO samples, observed {len(sample_ids)}")
    group_counts = {}
    for item in sample_meta:
        group_counts[item["group"]] = group_counts.get(item["group"], 0) + 1
    if group_counts.get("long_lived_sibling") != 50 or group_counts.get("offspring") != 50 or group_counts.get("control") != 50:
        raise RuntimeError(f"Unexpected group counts in GSE16717: {group_counts}")

    # Per-gene z-scores are computed across all 150 samples; composite scores are
    # the unweighted mean of the pre-specified published gene panels.
    z_values = {}
    for gene, values in gene_values.items():
        mean = float(np.nanmean(values))
        sd = float(np.nanstd(values, ddof=1))
        z_values[gene] = (values - mean) / sd if sd > 0 else np.full(len(sample_ids), np.nan)

    scores, panel_status = build_complete_panel_scores(z_values)

    comparisons = []
    for group_a, group_b in (("long_lived_sibling", "control"), ("offspring", "control")):
        ia = np.array([i for i, x in enumerate(sample_meta) if x["group"] == group_a])
        ib = np.array([i for i, x in enumerate(sample_meta) if x["group"] == group_b])
        for gene in M_RPG + C_RPG:
            if gene not in gene_values:
                continue
            va, vb = gene_values[gene][ia], gene_values[gene][ib]
            stat = ttest_ind(va, vb, equal_var=False, nan_policy="omit")
            comparisons.append({
                "comparison": f"{group_a}_vs_{group_b}",
                "panel": "mRPG_8" if gene in M_RPG else "cRPG_7",
                "gene": gene,
                "mean_group_a": float(np.nanmean(va)),
                "mean_group_b": float(np.nanmean(vb)),
                "difference_a_minus_b": float(np.nanmean(va) - np.nanmean(vb)),
                "welch_t": float(stat.statistic),
                "p_value": float(stat.pvalue),
            })
        for panel_name, panel_genes in (("mRPG_8", M_RPG), ("cRPG_7", C_RPG)):
            if panel_name not in scores:
                continue
            va, vb = scores[panel_name][ia], scores[panel_name][ib]
            stat = ttest_ind(va, vb, equal_var=False, nan_policy="omit")
            comparisons.append({
                "comparison": f"{group_a}_vs_{group_b}",
                "panel": panel_name,
                "gene": "COMPOSITE_SCORE",
                "mean_group_a": float(np.nanmean(va)),
                "mean_group_b": float(np.nanmean(vb)),
                "difference_a_minus_b": float(np.nanmean(va) - np.nanmean(vb)),
                "welch_t": float(stat.statistic),
                "p_value": float(stat.pvalue),
            })

    # Apply BH separately to each comparison/panel family, including the
    # composite score, and preserve all raw p-values.
    for comp in sorted({x["comparison"] for x in comparisons}):
        for panel in ("mRPG_8", "cRPG_7"):
            idx = [i for i, x in enumerate(comparisons) if x["comparison"] == comp and x["panel"] == panel]
            qvals = bh_adjust([comparisons[i]["p_value"] for i in idx])
            for i, q in zip(idx, qvals):
                comparisons[i]["fdr_bh"] = q

    with (out / "sample_metadata.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(sample_meta[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(sample_meta)
    with (out / "gene_expression.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["gene", "panel"] + sample_ids)
        for gene in M_RPG + C_RPG:
            if gene in gene_values:
                writer.writerow([gene, "mRPG_8" if gene in M_RPG else "cRPG_7"] + [f"{x:.8g}" for x in gene_values[gene]])
    with (out / "group_comparisons.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparisons[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(comparisons)

    summary = {
        "accession": "GSE16717",
        "platform": "GPL2895",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "sample_count": len(sample_ids),
        "group_counts": group_counts,
        "group_age_sex_summary": {
            group: {
                "n": sum(x["group"] == group for x in sample_meta),
                "mean_age_years": float(np.mean([x["age"] for x in sample_meta if x["group"] == group and x["age"] is not None])),
                "sd_age_years": float(np.std([x["age"] for x in sample_meta if x["group"] == group and x["age"] is not None], ddof=1)),
                "female_n": sum(x["group"] == group and x["sex"] == "female" for x in sample_meta),
                "male_n": sum(x["group"] == group and x["sex"] == "male" for x in sample_meta),
            }
            for group in sorted(group_counts)
        },
        "panel_status": panel_status,
        "sample_age_metadata_count": sum(x["age"] is not None for x in sample_meta),
        "sample_sex_metadata_count": sum(bool(x["sex"]) for x in sample_meta),
        "probe_count_for_target_genes": {g: len(per_gene_probe_values.get(g, [])) for g in M_RPG + C_RPG},
        "missing_signature_genes": missing_genes,
        "mRPG_8": M_RPG,
        "cRPG_7": C_RPG,
        "matrix_sha256": sha256(matrix_path),
        "platform_annotation_sha256": sha256(platform_path),
        "analysis_method": "median across probes per gene; gene-wise z-score across all 150 samples; unweighted panel mean; Welch t-tests; BH FDR separately within each panel and group comparison",
        "limitations": [
            "This is a reanalysis of the same Leiden GSE16717 cohort already cited as validation in the 2026 paper, not a new independent cohort.",
            "GEO sample metadata include individual age and sex for all 150 samples; reported age/sex summaries are descriptive.",
            "The analysis uses normalized microarray probe values and median probe aggregation; it is not a direct RNA-seq count replication.",
            "Unadjusted Welch tests do not control family structure or covariates; they are descriptive and exploratory. Long-lived siblings are substantially older than controls, so a simple group mean difference is not age-adjusted replication of the published age-trajectory method.",
            "The cRPG-7 composite score is withheld if any published gene is missing from GPL2895; gene-level results for available genes remain descriptive.",
            "The analysis does not establish causality or a novel mechanism."
        ],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
