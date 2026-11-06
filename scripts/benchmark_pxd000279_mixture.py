"""Benchmark missing-value handling against known HeLa/E. coli mixture ratios.

Input: MaxQuant proteinGroups.txt from PXD000279/proteomebenchmark.zip.
The two mixtures contain the same HeLa amount and a three-fold E. coli
increase. This evaluates downstream ratio recovery under the dataset's
observed missingness; it does not claim cell-level missing values have
known exact abundances.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from pathlib import Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _truth_species(headers: str) -> str | None:
    human = "OS=Homo sapiens" in headers
    ecoli = "OS=Escherichia coli" in headers
    if human == ecoli:
        return None
    return "human" if human else "ecoli"


def _is_yes(value: str | None) -> bool:
    return (value or "").strip() in {"+", "1", "true", "TRUE", "yes", "YES"}


def _metrics(values: list[float], expected: float) -> dict:
    if not values:
        return {"n": 0, "median_log2_fold_change": None, "mae": None,
                "rmse": None, "within_0_5_log2": None}
    errors = [v - expected for v in values]
    return {
        "n": len(values),
        "median_log2_fold_change": statistics.median(values),
        "mae": statistics.mean(abs(e) for e in errors),
        "rmse": math.sqrt(statistics.mean(e * e for e in errors)),
        "within_0_5_log2": sum(abs(e) <= 0.5 for e in errors) / len(errors),
    }


def _group_effect(row: dict[str, float | None], group10: list[str],
                  group30: list[str]) -> float:
    a = statistics.mean(float(row[s]) for s in group10)
    b = statistics.mean(float(row[s]) for s in group30)
    return b - a


def benchmark_pxd000279(input_path: str | Path, *, seed: int = 1729) -> dict:
    path = Path(input_path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames or []
        if not fields:
            raise ValueError("proteinGroups input has no header")
        fasta_col = next((c for c in ("Fasta headers", "Fasta.headers") if c in fields), None)
        if fasta_col is None:
            raise ValueError("Expected MaxQuant 'Fasta headers' column for species assignment")
        intensity_cols = [c for c in fields if c.startswith("LFQ intensity ")]
        if len(intensity_cols) != 6:
            raise ValueError(f"Expected exactly six LFQ intensity columns; found {len(intensity_cols)}")
        group10 = [c for c in intensity_cols if "Ecoli10" in c or "E. coli 10" in c]
        group30 = [c for c in intensity_cols if "Ecoli30" in c or "E. coli 30" in c]
        if len(group10) != 3 or len(group30) != 3:
            raise ValueError("Could not identify three Ecoli10 and three Ecoli30 LFQ replicate columns from headers")
        required_flags = [c for c in ("Reverse", "Potential contaminant", "Only identified by site") if c in fields]
        rows = []
        skipped = {"decoy_or_contaminant_or_site_only": 0, "ambiguous_species": 0,
                   "insufficient_replicates": 0}
        for line, raw in enumerate(reader, start=2):
            if any(_is_yes(raw.get(c)) for c in required_flags):
                skipped["decoy_or_contaminant_or_site_only"] += 1
                continue
            species = _truth_species(raw.get(fasta_col) or "")
            if species is None:
                skipped["ambiguous_species"] += 1
                continue
            values = {}
            for col in intensity_cols:
                token = (raw.get(col) or "").strip()
                if token in {"", "0", "NA", "NaN", "nan"}:
                    values[col] = None
                    continue
                try:
                    intensity = float(token)
                except ValueError as exc:
                    raise ValueError(f"Line {line}: invalid LFQ intensity in {col}: {token!r}") from exc
                if not math.isfinite(intensity) or intensity < 0:
                    raise ValueError(f"Line {line}: LFQ intensities must be finite and non-negative")
                values[col] = math.log2(intensity) if intensity > 0 else None
            if sum(values[c] is not None for c in group10) < 2 or sum(values[c] is not None for c in group30) < 2:
                skipped["insufficient_replicates"] += 1
                continue
            rows.append({"species": species, "values": values})

    if not rows:
        raise ValueError("No unambiguous species-assigned proteins met the >=2/3 replicate rule in both groups")

    # All methods are evaluated on the same protein universe. The primary
    # observed-only analysis uses measured values; the two imputation baselines
    # fill missing log2 intensities but never overwrite observed values.
    rng = random.Random(seed)
    by_species = {"human": [], "ecoli": []}
    missing_total = observed_total = 0
    for item in rows:
        original = item["values"]
        missing_total += sum(original[c] is None for c in intensity_cols)
        observed_total += len(intensity_cols) - sum(original[c] is None for c in intensity_cols)
        observed_only = {
            c: float(original[c]) for c in intensity_cols if original[c] is not None
        }
        complete_effect = _group_effect(observed_only, 
            [c for c in group10 if c in observed_only],
            [c for c in group30 if c in observed_only])
        row_values = [float(v) for v in original.values() if v is not None]
        row_median = float(statistics.median(row_values))
        row_median_filled = {c: (float(original[c]) if original[c] is not None else row_median)
                             for c in intensity_cols}
        minprob_filled = {c: (float(original[c]) if original[c] is not None else None)
                          for c in intensity_cols}
        for col in intensity_cols:
            if minprob_filled[col] is not None:
                continue
            observed_col = [float(r["values"][col]) for r in rows if r["values"][col] is not None]
            if len(observed_col) < 2:
                raise ValueError(f"Cannot estimate left-censored distribution for {col}")
            sd = statistics.stdev(observed_col)
            if sd <= 0:
                sd = 0.1
            mu = min(observed_col) - 1.8 * sd
            minprob_filled[col] = rng.gauss(mu, 0.3 * sd)
        by_species[item["species"]].append({
            "observed_only": complete_effect,
            "row_median": _group_effect(row_median_filled, group10, group30),
            "minprob": _group_effect(minprob_filled, group10, group30),
        })

    expected = {"human": 0.0, "ecoli": math.log2(3.0)}
    results = {}
    for species, records in by_species.items():
        results[species] = {
            method: _metrics([r[method] for r in records], expected[species])
            for method in ("observed_only", "row_median", "minprob")
        }
    return {
        "dataset_accession": "PXD000279",
        "dataset_title": "MaxLFQ HeLa/E. coli controlled-mixture proteome benchmark",
        "source_url": "https://ftp.ebi.ac.uk/pride-archive/2014/09/PXD000279/proteomebenchmark.zip",
        "publication_doi": "10.1074/mcp.M113.031591",
        "status": "SCORED_KNOWN_MIXTURE_RATIO",
        "input_sha256": _sha256(path),
        "sample_columns": {"Ecoli10": group10, "Ecoli30": group30},
        "replicates_per_group": 3,
        "protein_universe": len(rows),
        "missing_lfq_cells": missing_total,
        "total_lfq_cells": observed_total + missing_total,
        "missing_fraction": missing_total / (observed_total + missing_total),
        "expected_log2_fold_change_Ecoli30_vs_Ecoli10": expected,
        "species_results": results,
        "skipped_rows": skipped,
        "imputation_methods": {
            "observed_only": "No imputation; observed LFQ values only, >=2 of 3 replicates per group",
            "row_median": "Per-protein median of observed log2 LFQ values, used to fill missing cells",
            "minprob": "Per-sample left-censored Gaussian baseline: min observed log2 LFQ - 1.8 SD, spread 0.3 SD; seed fixed",
        },
        "interpretation": (
            "This is a known-mixture downstream-effect benchmark under real deposited missingness. "
            "Expected human log2 fold change is 0 because HeLa input is constant; expected E. coli "
            "log2 fold change is log2(3) because E. coli input triples. Metrics compare per-protein "
            "group effects with those known species-level mixture ratios. They do not reveal exact "
            "cell-level missing abundances, prove an imputer's superiority in other studies, or "
            "establish biological clinical validity."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate PXD000279 known-mixture ratios under real LFQ missingness")
    parser.add_argument("--input", required=True, help="MaxQuant proteinGroups.txt from proteomebenchmark.zip")
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=1729)
    args = parser.parse_args()
    report = benchmark_pxd000279(args.input, seed=args.seed)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
