"""Prepare a real DDA/DIA proteomics benchmark from PXD018408.

The published design has eight technical replicates per 1x and 2x mixture for
both DDA and DIA. DIA technical replicates are aggregated by the published
spike-in condition and used as an orthogonal group-level reference for each
DDA replicate in that condition. This is not falsely described as a
one-to-one run pairing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

DDA_1X = ["03", "11", "15", "19", "23", "31", "35", "39"]
DDA_2X = ["04", "08", "16", "20", "24", "28", "36", "40"]
DIA_1X = ["05", "09", "13", "21", "25", "29", "33", "41"]
DIA_2X = ["06", "10", "14", "18", "26", "30", "34", "38"]
DDA_SAMPLES = DDA_1X + DDA_2X


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_matrix(path: Path, frame) -> None:
    frame.index.name = "feature_id"
    frame.to_csv(path, sep="\t", na_rep="NA", float_format="%.10g")


def prepare_pxd018408(input_xlsx: str | Path, output_dir: str | Path) -> dict:
    try:
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError(
            "PXD018408 preparation requires the optional benchmark dependencies: "
            "pip install 'oracle-scientist[benchmark]'"
        ) from exc

    source = Path(input_xlsx)
    if not source.is_file():
        raise FileNotFoundError(source)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    dda = pd.read_excel(source, sheet_name="Table S3 MaxQuant Output")
    dia = pd.read_excel(source, sheet_name="Table S4 Spectronaut Output", na_values=["Filtered"])

    required_dda = {"Sequence", "Proteins"}
    if not required_dda.issubset(dda.columns):
        raise ValueError(f"DDA sheet must contain {sorted(required_dda)}")
    dda_columns = {sample: f"Intensity {sample}" for sample in DDA_SAMPLES}
    missing_dda = [column for column in dda_columns.values() if column not in dda.columns]
    if missing_dda:
        raise ValueError(f"DDA sheet is missing expected replicate columns: {missing_dda}")

    dda["sequence"] = dda["Sequence"].astype(str).str.strip()
    dda = dda[dda["sequence"].ne("") & dda["sequence"].ne("nan")].copy()
    proteins = dda["Proteins"].fillna("").astype(str)
    dda["is_human"] = proteins.str.contains("HUMAN", case=False, regex=False)
    dda["is_ecoli"] = proteins.str.contains("ECOLI", case=False, regex=False)
    species = dda.groupby("sequence")[["is_human", "is_ecoli"]].max()
    dda_values = dda.set_index("sequence")[[dda_columns[s] for s in DDA_SAMPLES]].apply(
        pd.to_numeric, errors="coerce"
    )
    dda_values.columns = DDA_SAMPLES
    dda_values = dda_values.groupby(level=0).sum(min_count=1)
    dda_values = dda_values.replace(0, np.nan)

    unique_human = species.index[species["is_human"] & ~species["is_ecoli"]]
    dda_reference_sums = dda_values.loc[dda_values.index.intersection(unique_human), DDA_SAMPLES].sum(axis=0)
    if "03" not in dda_reference_sums or not math.isfinite(float(dda_reference_sums["03"])) or dda_reference_sums["03"] <= 0:
        raise ValueError("Cannot normalize DDA: reference sample 03 has no unique-human peptide signal")
    if (dda_reference_sums <= 0).any():
        raise ValueError("Cannot normalize DDA: one or more replicates lack unique-human reference signal")
    dda_values = dda_values.mul(float(dda_reference_sums["03"]) / dda_reference_sums, axis=1)

    required_dia = {"EG.PrecursorId"}
    if not required_dia.issubset(dia.columns):
        raise ValueError(f"DIA sheet must contain {sorted(required_dia)}")
    dia_sample_columns = [column for column in dia.columns if ".raw" in str(column)]
    if not dia_sample_columns:
        raise ValueError("DIA sheet contains no .raw sample intensity columns")
    sample_map = {}
    for column in dia_sample_columns:
        match = re.search(r"EA100915_(\d{2})", str(column))
        if not match:
            raise ValueError(f"Cannot extract DIA sample ID from column {column!r}")
        sample_id = match.group(1)
        if sample_id in sample_map:
            raise ValueError(f"Duplicate DIA sample ID {sample_id}")
        sample_map[sample_id] = column
    expected_dia = set(DIA_1X + DIA_2X)
    if set(sample_map) != expected_dia:
        raise ValueError(
            "DIA sample IDs do not match the published design; "
            f"missing={sorted(expected_dia-set(sample_map))}, "
            f"unexpected={sorted(set(sample_map)-expected_dia)}"
        )

    precursor = dia["EG.PrecursorId"].fillna("").astype(str).str.replace(
        r"\[.*?\]", "", regex=True
    )
    dia["sequence"] = precursor.str.extract(r"_([A-Z]+)_", expand=False)
    dia = dia[dia["sequence"].notna() & dia["sequence"].isin(species.index)].copy()
    dia_values = dia.groupby("sequence")[[sample_map[s] for s in DIA_1X + DIA_2X]].sum(min_count=1)
    dia_values.columns = DIA_1X + DIA_2X
    dia_values = dia_values.apply(pd.to_numeric, errors="coerce").replace(0, np.nan)

    shared_human = species.index[species["is_human"] & ~species["is_ecoli"]].intersection(dia_values.index)
    dia_reference_sums = dia_values.loc[shared_human, DIA_1X + DIA_2X].sum(axis=0)
    if "05" not in dia_reference_sums or not math.isfinite(float(dia_reference_sums["05"])) or dia_reference_sums["05"] <= 0:
        raise ValueError("Cannot normalize DIA: reference sample 05 has no unique-human peptide signal")
    if (dia_reference_sums <= 0).any():
        raise ValueError("Cannot normalize DIA: one or more replicates lack unique-human reference signal")
    dia_values = dia_values.mul(float(dia_reference_sums["05"]) / dia_reference_sums, axis=1)

    # Match the PEPerMINT reference procedure: aggregate the eight DIA runs
    # within each known mixture ratio, then attach that group reference to each
    # DDA replicate from the same ratio. This is explicitly group-level, not
    # sample-paired ground truth.
    dia_1x = dia_values[DIA_1X].median(axis=1, skipna=True)
    dia_2x = dia_values[DIA_2X].median(axis=1, skipna=True)
    common = sorted(set(dda_values.index) & set(dia_values.index))
    observed = dda_values.loc[common, DDA_SAMPLES].copy()
    orthogonal = pd.DataFrame(index=common, columns=DDA_SAMPLES, dtype=float)
    for sample in DDA_1X:
        orthogonal[sample] = dia_1x.reindex(common)
    for sample in DDA_2X:
        orthogonal[sample] = dia_2x.reindex(common)

    observed = observed.replace([np.inf, -np.inf], np.nan)
    orthogonal = orthogonal.replace([np.inf, -np.inf], np.nan)
    observed_mean = float(observed.stack().mean())
    reference_mean = float(orthogonal.stack().mean())
    if not math.isfinite(observed_mean) or observed_mean <= 0 or not math.isfinite(reference_mean) or reference_mean <= 0:
        raise ValueError("DDA/DIA global intensity means must be finite and positive")
    orthogonal = orthogonal * (observed_mean / reference_mean)

    # The validation uses log2 values so the documented 2x E. coli spike-in
    # corresponds to an expected +1 log2 fold-change; human background is 0.
    observed = np.log2(observed.where(observed > 0))
    orthogonal = np.log2(orthogonal.where(orthogonal > 0))
    keep = observed.notna().any(axis=1) & orthogonal.notna().any(axis=1)
    observed = observed.loc[keep]
    orthogonal = orthogonal.loc[keep]

    imputed = observed.copy()
    for feature in imputed.index:
        row = imputed.loc[feature]
        if row.notna().any():
            imputed.loc[feature] = row.fillna(float(row.median()))

    labels = pd.DataFrame({
        "sample_id": DDA_SAMPLES,
        "ratio_group": ["1x"] * len(DDA_1X) + ["2x"] * len(DDA_2X),
    })
    feature_truth = species.reindex(observed.index).copy()
    feature_truth["organism"] = "ambiguous_or_unmapped"
    feature_truth.loc[feature_truth["is_ecoli"] & ~feature_truth["is_human"], "organism"] = "ecoli"
    feature_truth.loc[feature_truth["is_human"] & ~feature_truth["is_ecoli"], "organism"] = "human"
    feature_truth["expected_log2fc_2x_vs_1x"] = np.nan
    feature_truth.loc[feature_truth["organism"] == "ecoli", "expected_log2fc_2x_vs_1x"] = 1.0
    feature_truth.loc[feature_truth["organism"] == "human", "expected_log2fc_2x_vs_1x"] = 0.0
    feature_truth = feature_truth[feature_truth["organism"].isin(["ecoli", "human"])]

    observed_path = out / "pxd018408_dda_observed.tsv"
    orthogonal_path = out / "pxd018408_dia_group_reference.tsv"
    imputed_path = out / "pxd018408_row_median_baseline.tsv"
    labels_path = out / "pxd018408_sample_labels.tsv"
    truth_path = out / "pxd018408_expected_effects.tsv"
    _write_matrix(observed_path, observed)
    _write_matrix(orthogonal_path, orthogonal)
    _write_matrix(imputed_path, imputed)
    labels.to_csv(labels_path, sep="\t", index=False)
    feature_truth[["organism", "expected_log2fc_2x_vs_1x"]].to_csv(
        truth_path, sep="\t", index_label="feature_id", na_rep="NA"
    )

    missing_cells = int(observed.isna().sum().sum())
    total_cells = int(observed.shape[0] * observed.shape[1])
    report = {
        "dataset_accession": "PXD018408",
        "dataset_title": "Benchmarking and Best Practices for Quantitative Proteomics",
        "publication_doi": "10.1021/acsomega.0c04030",
        "benchmark_source": "PEPerMINT Example Data, Zenodo 10.5281/zenodo.11216899",
        "source_file_sha256": _sha256(source),
        "source_file": source.name,
        "feature_count": int(observed.shape[0]),
        "dda_sample_count": len(DDA_SAMPLES),
        "dia_technical_replicates": {"1x": len(DIA_1X), "2x": len(DIA_2X)},
        "dda_replicates": {"1x": DDA_1X, "2x": DDA_2X},
        "dia_replicates": {"1x": DIA_1X, "2x": DIA_2X},
        "real_dda_missing_cells": missing_cells,
        "real_dda_missing_fraction": missing_cells / total_cells if total_cells else 0.0,
        "reference_mode": "group_aggregated_by_spikein_ratio",
        "reference_method": "median of eight DIA technical replicates per ratio group; reused as group-level orthogonal reference for each DDA replicate in that group",
        "known_biological_truth": {
            "ecoli_unique_peptides": "expected log2FC +1 for 2x versus 1x",
            "human_unique_peptides": "expected log2FC 0 for 2x versus 1x",
            "ambiguous_or_shared_peptides": "excluded from feature-level known-effect scoring",
        },
        "outputs": {
            "observed": {"path": observed_path.name, "sha256": _sha256(observed_path)},
            "orthogonal": {"path": orthogonal_path.name, "sha256": _sha256(orthogonal_path)},
            "imputed_row_median_baseline": {"path": imputed_path.name, "sha256": _sha256(imputed_path)},
            "sample_labels": {"path": labels_path.name, "sha256": _sha256(labels_path)},
            "expected_effects": {"path": truth_path.name, "sha256": _sha256(truth_path)},
        },
        "limitations": (
            "DDA and DIA technical replicates are not one-to-one sample pairs. "
            "The DIA reference is aggregated by the independently known 1x/2x "
            "mixture condition, following the published PEPerMINT preprocessing "
            "procedure. This supports genuine-missing-cell reconstruction against "
            "an orthogonal condition-level reference, not per-run paired truth. "
            "The two-group outcome is a controlled mixture condition, not a patient "
            "clinical endpoint. DDA/DIA are not error-free absolute truth."
        ),
    }
    (out / "pxd018408-provenance.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare PXD018408 DDA/DIA genuine-missingness benchmark matrices")
    parser.add_argument("--input", required=True, help="PEPerMINT data.xlsx from Zenodo")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    print(json.dumps(prepare_pxd018408(args.input, args.output_dir), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
