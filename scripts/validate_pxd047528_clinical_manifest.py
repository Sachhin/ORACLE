#!/usr/bin/env python3
"""Validate a source-authenticated PXD047528 15-alias to 13-patient manifest.

This validator never guesses patient identities or clinical labels. It accepts
only a manifest that carries explicit provenance for every row.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

EXPECTED_SAMPLES = {f"{i}_Slot1" for i in range(1, 16)}
EXPECTED_PATIENT_COUNTS = {"HIV": 8, "HERPES": 5}
EXPECTED_HAND_COUNTS = {"MND": 3, "HAD": 2, "COGNITIVELY_NORMAL": 3}
VALID_RELATIONSHIPS = {"PRIMARY", "TECHNICAL_REPLICATE", "REPEAT_ACQUISITION", "OTHER_DOCUMENTED", "EXCLUDED"}
VALID_PROVENANCE = {"SUBMITTER_CONFIRMED", "REPOSITORY_DEPOSITED"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_manifest(path: str | Path) -> dict:
    source = Path(path)
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {
            "sample_id", "patient_id", "phenotype", "hand_status",
            "raw_dda_files", "raw_dia_files", "relationship_to_patient",
            "mapping_rationale", "source_url", "source_document_sha256",
            "provenance_status",
        }
        missing_columns = sorted(required - set(reader.fieldnames or []))
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        rows = list(reader)

    errors: list[str] = []
    if len(rows) != 15:
        errors.append(f"Expected exactly 15 processed aliases, found {len(rows)}")
    sample_ids = [str(row.get("sample_id", "")).strip() for row in rows]
    if len(sample_ids) != len(set(sample_ids)):
        errors.append("Duplicate sample_id rows found")
    if set(sample_ids) != EXPECTED_SAMPLES:
        errors.append(
            "sample_id set must be exactly 1_Slot1 through 15_Slot1; "
            f"missing={sorted(EXPECTED_SAMPLES-set(sample_ids))}, "
            f"unexpected={sorted(set(sample_ids)-EXPECTED_SAMPLES)}"
        )

    patients: dict[str, dict[str, str]] = {}
    patient_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for index, row in enumerate(rows, start=2):
        patient = str(row.get("patient_id", "")).strip()
        phenotype = str(row.get("phenotype", "")).strip().upper()
        hand = str(row.get("hand_status", "")).strip().upper()
        relationship = str(row.get("relationship_to_patient", "")).strip().upper()
        rationale = str(row.get("mapping_rationale", "")).strip()
        source_url = str(row.get("source_url", "")).strip()
        source_hash = str(row.get("source_document_sha256", "")).strip().lower()
        provenance = str(row.get("provenance_status", "")).strip().upper()

        if not patient:
            errors.append(f"Row {index}: patient_id is blank")
            continue
        if phenotype not in EXPECTED_PATIENT_COUNTS:
            errors.append(f"Row {index}: phenotype must be HIV or HERPES")
        if relationship not in VALID_RELATIONSHIPS:
            errors.append(f"Row {index}: invalid relationship_to_patient {relationship!r}")
        if not rationale:
            errors.append(f"Row {index}: mapping_rationale is required")
        if not row.get("raw_dda_files", "").strip() or not row.get("raw_dia_files", "").strip():
            errors.append(f"Row {index}: both raw DDA and DIA file identifiers are required")
        if not source_url.startswith(("https://", "http://")):
            errors.append(f"Row {index}: source_url must be an http(s) provenance URL")
        if not SHA256_RE.fullmatch(source_hash):
            errors.append(f"Row {index}: source_document_sha256 must be a 64-character SHA-256")
        if provenance not in VALID_PROVENANCE:
            errors.append(f"Row {index}: provenance_status must be SUBMITTER_CONFIRMED or REPOSITORY_DEPOSITED")

        if phenotype == "HIV" and hand not in EXPECTED_HAND_COUNTS:
            errors.append(f"Row {index}: HIV patient requires MND, HAD, or COGNITIVELY_NORMAL HAND status")
        if phenotype == "HERPES" and hand not in {"", "NA", "NOT_APPLICABLE"}:
            errors.append(f"Row {index}: HAND status must be not applicable for HERPES patients")

        current = {"phenotype": phenotype, "hand_status": hand}
        if patient in patients and patients[patient] != current:
            errors.append(f"Patient {patient}: inconsistent phenotype or HAND status across aliases")
        patients[patient] = current
        patient_rows[patient].append(row)

    if len(patients) != 13:
        errors.append(f"Expected exactly 13 distinct clinical patients, found {len(patients)}")

    phenotype_counts = Counter(value["phenotype"] for value in patients.values())
    if dict(phenotype_counts) != EXPECTED_PATIENT_COUNTS:
        errors.append(f"Expected patient phenotype counts {EXPECTED_PATIENT_COUNTS}, found {dict(phenotype_counts)}")

    hand_counts = Counter(
        value["hand_status"] for value in patients.values() if value["phenotype"] == "HIV"
    )
    if dict(hand_counts) != EXPECTED_HAND_COUNTS:
        errors.append(f"Expected HIV HAND subgroup counts {EXPECTED_HAND_COUNTS}, found {dict(hand_counts)}")

    for patient, group in patient_rows.items():
        if len(group) > 1:
            relationships = [str(row.get("relationship_to_patient", "")).strip().upper() for row in group]
            if relationships.count("PRIMARY") != 1:
                errors.append(f"Patient {patient}: repeated aliases require exactly one PRIMARY row")
            if not any(item in {"TECHNICAL_REPLICATE", "REPEAT_ACQUISITION", "OTHER_DOCUMENTED", "EXCLUDED"} for item in relationships if item != "PRIMARY"):
                errors.append(f"Patient {patient}: repeated aliases need an explicitly documented relationship")

    report = {
        "dataset": "PXD047528",
        "status": "PROVENANCE_VALIDATED_READY_FOR_OUTCOME_ANALYSIS" if not errors else "BLOCKED_INVALID_OR_INCOMPLETE_CROSSWALK",
        "manifest_path": str(source),
        "manifest_sha256": sha256(source),
        "alias_count": len(sample_ids),
        "distinct_patient_count": len(patients),
        "phenotype_patient_counts": dict(phenotype_counts),
        "hiv_hand_patient_counts": dict(hand_counts),
        "errors": errors,
        "interpretation": "This checks the submitted mapping and its declared provenance fields. It does not independently authenticate a submitter's identity or prove clinical correctness; reviewers must inspect the cited source document.",
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Source-authenticated TSV crosswalk")
    parser.add_argument("--report", default="", help="JSON report path (default: MANIFEST.audit.json)")
    args = parser.parse_args()
    try:
        report = validate_manifest(args.manifest)
    except Exception as exc:
        report = {"dataset": "PXD047528", "status": "BLOCKED_INVALID_OR_INCOMPLETE_CROSSWALK", "error": str(exc)}
    target = Path(args.report or (args.manifest + ".audit.json"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("status") == "PROVENANCE_VALIDATED_READY_FOR_OUTCOME_ANALYSIS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
