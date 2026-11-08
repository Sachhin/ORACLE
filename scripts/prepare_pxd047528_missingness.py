"""Prepare PEPerMINT's paired PXD047528 DDA/DIA tables for ORACLE.

This converter reproduces the published PEPerMINT peptide-level preparation:
group duplicate peptide sequences by summing available intensities, convert
zero-sum cells to missing, scale DIA's global mean to DDA's, and natural-log
transform both assays. It does not infer clinical labels.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Iterable

DEFAULT_SAMPLES = [f"{i}_Slot1" for i in range(1, 16)]
_MISSING = {"", "NA", "N/A", "NaN", "nan", "null", "NULL", "Filtered"}


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_peptide_table(path: str | Path, sample_ids: list[str]):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames or []
        if "Sequence" not in fields:
            raise ValueError(f"{path}: expected a Sequence column")
        missing_samples = sorted(set(sample_ids) - set(fields))
        if missing_samples:
            raise ValueError(f"{path}: missing expected sample columns: {missing_samples}")
        sums: dict[str, dict[str, float | None]] = {}
        source_rows = 0
        for line, row in enumerate(reader, start=2):
            source_rows += 1
            sequence = (row.get("Sequence") or "").strip()
            if not sequence:
                continue
            target = sums.setdefault(sequence, {sample: None for sample in sample_ids})
            for sample in sample_ids:
                raw = (row.get(sample) or "").strip()
                if raw in _MISSING:
                    continue
                try:
                    value = float(raw)
                except ValueError as exc:
                    raise ValueError(f"{path}:{line}: invalid abundance for {sample}: {raw!r}") from exc
                if not math.isfinite(value) or value < 0:
                    raise ValueError(f"{path}:{line}: abundance must be finite and non-negative")
                current = target[sample]
                target[sample] = value if current is None else current + value
    # PEPerMINT converts zero-sum abundance cells to NA after duplicate-sequence
    # aggregation. A zero is not treated as a measured zero in this pipeline.
    for row in sums.values():
        for sample, value in row.items():
            if value == 0:
                row[sample] = None
    if not sums:
        raise ValueError(f"{path}: no peptide sequences found")
    return sums, source_rows


def _mean_observed(matrix: dict[str, dict[str, float | None]]) -> float:
    values = [value for row in matrix.values() for value in row.values() if value is not None]
    if not values:
        raise ValueError("Cannot normalize an assay with no observed abundance values")
    return statistics.mean(values)


def _write_matrix(path: Path, sample_ids: list[str], matrix: dict[str, dict[str, float | None]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["Sequence", *sample_ids])
        for feature in sorted(matrix):
            writer.writerow([feature, *[
                "" if matrix[feature][sample] is None else format(matrix[feature][sample], ".12g")
                for sample in sample_ids
            ]])


def prepare_pxd047528(
    dda_path: str | Path,
    dia_path: str | Path,
    output_dir: str | Path,
    *,
    sample_ids: Iterable[str] = DEFAULT_SAMPLES,
) -> dict:
    samples = list(sample_ids)
    if len(samples) < 2 or len(set(samples)) != len(samples) or any(not x for x in samples):
        raise ValueError("At least two unique, non-empty sample IDs are required")
    dda, dda_source_rows = read_peptide_table(dda_path, samples)
    dia, dia_source_rows = read_peptide_table(dia_path, samples)
    dda_features, dia_features = set(dda), set(dia)
    shared = dda_features & dia_features
    # Match PEPerMINT's DDA preprocessing: peptides missing in every DDA sample
    # are removed before model input. Only common DDA/DIA peptide sequences can
    # contribute orthogonal truth.
    retained = sorted(feature for feature in shared
                     if any(dda[feature][sample] is not None for sample in samples))
    if not retained:
        raise ValueError("No shared peptides have at least one observed DDA value")

    scale_factor = _mean_observed(dda) / _mean_observed(dia)
    observed: dict[str, dict[str, float | None]] = {}
    orthogonal: dict[str, dict[str, float | None]] = {}
    imputed: dict[str, dict[str, float | None]] = {}
    for feature in retained:
        observed_row = {}
        dia_row = {}
        for sample in samples:
            d = dda[feature][sample]
            q = dia[feature][sample]
            observed_row[sample] = None if d is None else math.log(d)
            scaled_dia = None if q is None else q * scale_factor
            dia_row[sample] = None if scaled_dia is None else math.log(scaled_dia)
        observed[feature] = observed_row
        orthogonal[feature] = dia_row
        available = [value for value in observed_row.values() if value is not None]
        if not available:
            continue
        row_median = float(statistics.median(available))
        # Deterministic ORACLE baseline; a future candidate imputer can replace
        # this file while preserving all originally observed values.
        imputed[feature] = {
            sample: (observed_row[sample] if observed_row[sample] is not None else row_median)
            for sample in samples
        }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    observed_path = out / "observed_dda_log.tsv"
    orthogonal_path = out / "orthogonal_dia_log.tsv"
    imputed_path = out / "row_median_imputed_dda_log.tsv"
    labels_template = out / "sample_map_template.tsv"
    _write_matrix(observed_path, samples, observed)
    _write_matrix(orthogonal_path, samples, orthogonal)
    _write_matrix(imputed_path, samples, imputed)
    with labels_template.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow([
            "sample_id", "patient_id", "phenotype", "hand_status",
            "raw_acquisition_files", "source_reference", "source_manifest_sha256",
        ])
        for sample in samples:
            # Leave all clinical fields blank until the submitter-authenticated
            # run-to-patient manifest is obtained; never infer them from aliases.
            writer.writerow([sample, "", "", "", "", "", ""])

    missing_dda = sum(observed[f][s] is None for f in observed for s in samples)
    scored_missing = sum(observed[f][s] is None and orthogonal[f][s] is not None
                         for f in observed for s in samples)
    report = {
        "dataset": "PXD047528",
        "source": "PEPerMINT Example Data, Zenodo record 11216899, datasets/blood_hiv_dda_dia",
        "preparation_status": "MATRICES_PREPARED_CLINICAL_SAMPLE_MAPPING_REQUIRED",
        "sample_ids": samples,
        "sample_count": len(samples),
        "dda_source_rows": dda_source_rows,
        "dia_source_rows": dia_source_rows,
        "dda_unique_peptides": len(dda_features),
        "dia_unique_peptides": len(dia_features),
        "shared_peptides_with_at_least_one_dda_measurement": len(retained),
        "excluded_dda_only_peptides": len(dda_features - dia_features),
        "excluded_dia_only_peptides": len(dia_features - dda_features),
        "dia_to_dda_global_mean_scale_factor": scale_factor,
        "transformation": "natural logarithm after DIA global-mean scaling",
        "zero_policy": "sum duplicate Sequence rows with min_count=1; zero-sum cells become missing, matching PEPerMINT loader",
        "genuine_dda_missing_cells": missing_dda,
        "genuine_dda_missing_cells_with_dia_measurement": scored_missing,
        "orthogonal_coverage_of_dda_missing_cells": scored_missing / missing_dda if missing_dda else None,
        "baseline_imputer": "row median over observed DDA values; observed cells preserved",
        "files": {
            "observed_dda": {"path": observed_path.name, "sha256": sha256(observed_path)},
            "orthogonal_dia": {"path": orthogonal_path.name, "sha256": sha256(orthogonal_path)},
            "row_median_imputed": {"path": imputed_path.name, "sha256": sha256(imputed_path)},
            "sample_map_template": {"path": labels_template.name, "sha256": sha256(labels_template)},
        },
        "source_sha256": {"dda_peptides_tsv": sha256(dda_path), "dia_peptides_tsv": sha256(dia_path)},
        "clinical_mapping_warning": (
            "The PEPerMINT benchmark reports 15 samples, while Ahmed et al.'s original clinical paper "
            "reports 13 plasma patients (8 HIV and 5 herpes). The template intentionally contains no "
            "guessed labels. Resolve the 15-to-13 sample discrepancy and map sample IDs to patient IDs "
            "from source records before running biological outcome concordance."
        ),
        "limitations": (
            "This prepares published paired DDA/DIA peptide tables and a deterministic row-median baseline. "
            "It does not establish the clinical sample mapping, prove DIA is error-free, or claim an empirical "
            "benchmark score. Do not use filenames as phenotype labels."
        ),
    }
    manifest_path = out / "preparation_manifest.json"
    manifest_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return {**report, "manifest_path": str(manifest_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare paired PEPerMINT PXD047528 DDA/DIA tables for ORACLE")
    parser.add_argument("--dda-peptides", required=True, help="PEPerMINT datasets/blood_hiv_dda_dia/dda/peptides.tsv")
    parser.add_argument("--dia-peptides", required=True, help="PEPerMINT datasets/blood_hiv_dda_dia/dia/peptides.tsv")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--sample-id", action="append", default=[],
                        help="Sample column ID; repeat for a custom verified mapping. Default: 1_Slot1 through 15_Slot1.")
    args = parser.parse_args()
    result = prepare_pxd047528(args.dda_peptides, args.dia_peptides, args.output_dir,
                               sample_ids=args.sample_id or DEFAULT_SAMPLES)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
