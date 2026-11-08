"""Validate a source-authenticated PXD047528 run-to-clinical-patient crosswalk.

The 15 processed aliases must not be assigned by filename order or inferred
from abundance patterns. A source manifest and acquisition provenance are
required for every row.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

EXPECTED_SAMPLES = {f"{i}_Slot1" for i in range(1, 16)}
REQUIRED_COLUMNS = {
    "sample_id", "patient_id", "phenotype", "hand_status",
    "raw_acquisition_files", "source_reference", "source_manifest_sha256",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def validate_mapping(path: str | Path) -> dict:
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        columns = set(reader.fieldnames or [])
        missing_columns = sorted(REQUIRED_COLUMNS - columns)
        rows = list(reader)
    errors: list[str] = []
    warnings: list[str] = []
    if missing_columns:
        errors.append("Missing required columns: " + ", ".join(missing_columns))
    if missing_columns:
        return {"status": "BLOCKED", "errors": errors, "warnings": warnings,
                "mapping_file_sha256": digest, "row_count": len(rows)}

    by_sample: dict[str, dict[str, str]] = {}
    for line, row in enumerate(rows, 2):
        sample = (row.get("sample_id") or "").strip()
        if sample not in EXPECTED_SAMPLES:
            errors.append(f"Line {line}: unexpected sample_id {sample!r}")
            continue
        if sample in by_sample:
            errors.append(f"Line {line}: duplicate sample_id {sample}")
            continue
        normalized = {key: (row.get(key) or "").strip() for key in REQUIRED_COLUMNS}
        by_sample[sample] = normalized
        for field in ("patient_id", "raw_acquisition_files", "source_reference"):
            if not normalized[field]:
                errors.append(f"Line {line}: {field} is required")
        if not _SHA256.fullmatch(normalized["source_manifest_sha256"]):
            errors.append(f"Line {line}: source_manifest_sha256 must be 64 lowercase hex characters")
        phenotype = normalized["phenotype"].upper()
        hand = normalized["hand_status"].upper()
        if phenotype not in {"HIV", "HERPES"}:
            errors.append(f"Line {line}: phenotype must be HIV or HERPES")
        elif phenotype == "HIV" and hand not in {"HAND", "COGNITIVELY_NORMAL"}:
            errors.append(f"Line {line}: HIV samples require HAND or COGNITIVELY_NORMAL classification")
        elif phenotype == "HERPES" and hand not in {"NA", "NOT_APPLICABLE"}:
            errors.append(f"Line {line}: HERPES samples must use NA hand_status")

    missing_samples = sorted(EXPECTED_SAMPLES - set(by_sample))
    if missing_samples:
        errors.append("Missing sample aliases: " + ", ".join(missing_samples))

    patients = {r["patient_id"] for r in by_sample.values() if r["patient_id"]}
    phenotype_by_patient: dict[str, set[str]] = {}
    for r in by_sample.values():
        if r["patient_id"]:
            phenotype_by_patient.setdefault(r["patient_id"], set()).add(r["phenotype"].upper())
    for patient, labels in phenotype_by_patient.items():
        if len(labels) > 1:
            errors.append(f"Patient {patient} is assigned conflicting phenotypes")

    phenotype_counts = {}
    for r in by_sample.values():
        label = r["phenotype"].upper()
        phenotype_counts[label] = phenotype_counts.get(label, 0) + 1
    patient_counts = {}
    for r in by_sample.values():
        key = (r["patient_id"], r["phenotype"].upper())
        patient_counts[key] = 1
    unique_patient_phenotypes = {}
    for patient, labels in phenotype_by_patient.items():
        if len(labels) == 1:
            label = next(iter(labels))
            unique_patient_phenotypes[label] = unique_patient_phenotypes.get(label, 0) + 1

    hand_counts = {}
    for r in by_sample.values():
        if r["phenotype"].upper() == "HIV":
            key = r["hand_status"].upper()
            hand_counts[key] = hand_counts.get(key, 0) + 1

    if len(by_sample) == 15 and not missing_samples:
        if len(patients) != 13:
            errors.append(f"Expected 13 distinct clinical patients for the 15 aliases; found {len(patients)}")
        if unique_patient_phenotypes != {"HIV": 8, "HERPES": 5}:
            errors.append("Expected 8 distinct HIV and 5 distinct HERPES patients; "
                          f"found {unique_patient_phenotypes}")
        hiv_patients = {
            r["patient_id"]: r["hand_status"].upper()
            for r in by_sample.values() if r["phenotype"].upper() == "HIV"
        }
        if len(hiv_patients) != 8 or set(hiv_patients.values()) != {"HAND", "COGNITIVELY_NORMAL"}:
            errors.append("All 8 HIV patients require source-backed HAND/COGNITIVELY_NORMAL labels")
        else:
            patient_hand = {}
            for r in by_sample.values():
                if r["phenotype"].upper() == "HIV":
                    previous = patient_hand.setdefault(r["patient_id"], r["hand_status"].upper())
                    if previous != r["hand_status"].upper():
                        errors.append(f"Patient {r['patient_id']} has conflicting HAND labels")
            counts = {label: list(patient_hand.values()).count(label) for label in set(patient_hand.values())}
            if counts != {"HAND": 5, "COGNITIVELY_NORMAL": 3}:
                errors.append("Expected 5 HAND and 3 cognitively-normal HIV patients; "
                              f"found {counts}")

    if len(by_sample) == 15 and len(patients) == 13:
        warnings.append("15 run aliases map to 13 patients; retain explicit technical/replicate provenance.")

    return {
        "status": "READY_FOR_CLINICAL_VALIDATION" if not errors else "BLOCKED",
        "sample_aliases_mapped": len(by_sample),
        "distinct_patients": len(patients),
        "sample_phenotype_counts": phenotype_counts,
        "patient_phenotype_counts": unique_patient_phenotypes,
        "hiv_hand_sample_counts": hand_counts,
        "mapping_file_sha256": digest,
        "errors": errors,
        "warnings": warnings,
        "provenance_rule": "Every alias must cite the source manifest and raw acquisition file(s); inferred labels are prohibited.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", required=True, help="Submitter-authenticated tab-separated crosswalk")
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
