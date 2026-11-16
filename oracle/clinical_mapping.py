#!/usr/bin/env python3
"""Validate a submitter-authenticated PXD047528 sample-to-clinical crosswalk.

This validator never assigns patient labels. It only checks a completed,
source-backed TSV against the published 13-participant clinical cohort and
the 15 processed aliases used by PEPerMINT.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

EXPECTED_SAMPLES = {f"{i}_Slot1" for i in range(1, 16)}
REQUIRED_COLUMNS = {
    "sample_id", "patient_id", "phenotype", "hand_status",
    "raw_dda_files", "raw_dia_files", "relationship_to_patient",
    "mapping_rationale", "source_url", "source_document_sha256",
    "provenance_status", "include_in_hiv_vs_herpes",
    "include_in_hand_vs_cognitively_normal",
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _truth(value: str) -> bool | None:
    value = (value or "").strip().lower()
    if value in {"true", "1", "yes", "y"}:
        return True
    if value in {"false", "0", "no", "n"}:
        return False
    return None


def validate_mapping(path: str | Path) -> dict:
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        columns = set(reader.fieldnames or [])
        rows = list(reader)

    errors: list[str] = []
    warnings: list[str] = []
    missing_columns = sorted(REQUIRED_COLUMNS - columns)
    if missing_columns:
        errors.append("Missing required columns: " + ", ".join(missing_columns))
        return {
            "status": "BLOCKED", "mapping_file_sha256": digest,
            "row_count": len(rows), "errors": errors, "warnings": warnings,
        }

    by_sample: dict[str, dict[str, str]] = {}
    included_hiv_herpes: list[dict[str, str]] = []
    included_hand: list[dict[str, str]] = []
    patient_labels: dict[str, set[tuple[str, str]]] = defaultdict(set)

    for line, raw in enumerate(rows, 2):
        row = {key: (raw.get(key) or "").strip() for key in REQUIRED_COLUMNS}
        sample = row["sample_id"]
        if sample not in EXPECTED_SAMPLES:
            errors.append(f"Line {line}: unexpected sample alias {sample!r}")
            continue
        if sample in by_sample:
            errors.append(f"Line {line}: duplicate sample alias {sample}")
            continue
        by_sample[sample] = row

        if not row["raw_dda_files"] or not row["raw_dia_files"]:
            errors.append(f"Line {line}: both raw_dda_files and raw_dia_files are required")
        if not row["mapping_rationale"] or not row["source_url"]:
            errors.append(f"Line {line}: mapping_rationale and source_url are required")
        if not SHA256.fullmatch(row["source_document_sha256"]):
            errors.append(f"Line {line}: source_document_sha256 must be 64 lowercase hex characters")

        relationship = row["relationship_to_patient"].upper()
        provenance = row["provenance_status"].upper()
        phenotype = row["phenotype"].upper()
        hand = row["hand_status"].upper()
        use_hiv_herpes = _truth(row["include_in_hiv_vs_herpes"])
        use_hand = _truth(row["include_in_hand_vs_cognitively_normal"])

        if relationship not in {"PRIMARY", "TECHNICAL_REPLICATE", "QC", "EXCLUDED", "UNRESOLVED"}:
            errors.append(f"Line {line}: invalid relationship_to_patient {relationship!r}")
        if use_hiv_herpes is None or use_hand is None:
            errors.append(f"Line {line}: inclusion fields must be explicit TRUE/FALSE")

        if provenance != "SOURCE_AUTHENTICATED":
            if use_hiv_herpes or use_hand:
                errors.append(f"Line {line}: unverified provenance cannot be included in clinical analysis")
            if phenotype not in {"", "UNKNOWN", "NA", "NOT_APPLICABLE"} or hand not in {"", "UNKNOWN", "NA", "NOT_APPLICABLE"}:
                errors.append(f"Line {line}: unverified rows must not carry clinical phenotype/HAND labels")
            if relationship == "UNRESOLVED" and (use_hiv_herpes or use_hand):
                errors.append(f"Line {line}: unresolved row cannot be included")
            continue

        if relationship in {"QC", "EXCLUDED", "UNRESOLVED"}:
            if use_hiv_herpes or use_hand:
                errors.append(f"Line {line}: {relationship} rows cannot be included in clinical comparisons")
            continue

        if not row["patient_id"]:
            errors.append(f"Line {line}: authenticated clinical row requires patient_id")
        if phenotype not in {"HIV", "HERPES"}:
            errors.append(f"Line {line}: authenticated clinical phenotype must be HIV or HERPES")
            continue
        if phenotype == "HIV" and hand not in {"HAND", "COGNITIVELY_NORMAL"}:
            errors.append(f"Line {line}: HIV row requires HAND or COGNITIVELY_NORMAL")
        if phenotype == "HERPES" and hand not in {"NA", "NOT_APPLICABLE"}:
            errors.append(f"Line {line}: HERPES row must use NA hand_status")
        if relationship == "TECHNICAL_REPLICATE" and (use_hiv_herpes or use_hand):
            errors.append(f"Line {line}: technical replicate must not be counted as an independent participant")

        if row["patient_id"]:
            patient_labels[row["patient_id"]].add((phenotype, hand))
        if use_hiv_herpes:
            included_hiv_herpes.append(row)
        if use_hand:
            included_hand.append(row)

    missing_samples = sorted(EXPECTED_SAMPLES - set(by_sample))
    if missing_samples:
        errors.append("Missing sample aliases: " + ", ".join(missing_samples))

    for patient, labels in patient_labels.items():
        if len(labels) > 1:
            errors.append(f"Patient {patient} has conflicting phenotype/HAND labels")

    primary_patients = {r["patient_id"] for r in included_hiv_herpes if r["patient_id"]}
    phenotype_by_patient: dict[str, set[str]] = defaultdict(set)
    hand_by_patient: dict[str, set[str]] = defaultdict(set)
    for row in included_hiv_herpes:
        phenotype_by_patient[row["patient_id"]].add(row["phenotype"].upper())
        if row["phenotype"].upper() == "HIV":
            hand_by_patient[row["patient_id"]].add(row["hand_status"].upper())

    patient_phenotypes = {
        patient: next(iter(labels)) for patient, labels in phenotype_by_patient.items() if len(labels) == 1
    }
    phenotype_counts = defaultdict(int)
    for label in patient_phenotypes.values():
        phenotype_counts[label] += 1

    hand_patient_counts = defaultdict(int)
    for patient, labels in hand_by_patient.items():
        if len(labels) == 1:
            hand_patient_counts[next(iter(labels))] += 1
        elif len(labels) > 1:
            errors.append(f"Patient {patient} has conflicting HAND labels in included rows")

    if len(primary_patients) != 13:
        errors.append(f"Expected 13 distinct clinical patients in HIV/herpes comparison; found {len(primary_patients)}")
    if dict(phenotype_counts) != {"HIV": 8, "HERPES": 5}:
        errors.append(f"Expected 8 HIV and 5 HERPES patients; found {dict(phenotype_counts)}")
    if dict(hand_patient_counts) != {"HAND": 5, "COGNITIVELY_NORMAL": 3}:
        errors.append(f"Expected 5 HAND and 3 cognitively-normal HIV patients; found {dict(hand_patient_counts)}")
    if len(included_hand) != 8:
        errors.append(f"Expected 8 unique HIV patients in HAND comparison; found {len(included_hand)}")

    if len(by_sample) == 15 and len(primary_patients) == 13:
        warnings.append("15 processed aliases resolve to 13 clinical patients; non-primary aliases require explicit technical/QC/exclusion provenance.")

    return {
        "status": "READY_FOR_CLINICAL_VALIDATION" if not errors else "BLOCKED",
        "mapping_file_sha256": digest,
        "processed_aliases_mapped": len(by_sample),
        "distinct_included_clinical_patients": len(primary_patients),
        "patient_phenotype_counts": dict(phenotype_counts),
        "patient_hand_counts": dict(hand_patient_counts),
        "included_sample_aliases_hiv_herpes": len(included_hiv_herpes),
        "included_sample_aliases_hand_comparison": len(included_hand),
        "errors": errors,
        "warnings": warnings,
        "provenance_rule": "Every clinical inclusion must have SOURCE_AUTHENTICATED provenance, raw DDA/DIA filenames, rationale, source URL and source document SHA-256. No alias-order inference is allowed.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", required=True, help="Submitter-authenticated TSV crosswalk")
    parser.add_argument("--output", required=True, help="JSON validation report")
    args = parser.parse_args()
    report = validate_mapping(args.mapping)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "READY_FOR_CLINICAL_VALIDATION":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
