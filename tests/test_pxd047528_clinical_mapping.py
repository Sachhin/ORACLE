import csv
import hashlib
from pathlib import Path

from oracle.clinical_mapping import validate_mapping


FIELDS = [
    "sample_id", "patient_id", "phenotype", "hand_status",
    "raw_dda_files", "raw_dia_files", "relationship_to_patient",
    "mapping_rationale", "source_url", "source_document_sha256",
    "provenance_status", "include_in_hiv_vs_herpes",
    "include_in_hand_vs_cognitively_normal",
]


def make_rows():
    rows = []
    sha = hashlib.sha256(b"synthetic source document").hexdigest()
    assignments = []
    for i in range(1, 9):
        assignments.append((f"HIV{i:02d}", "HIV", "HAND" if i <= 5 else "COGNITIVELY_NORMAL"))
    for i in range(1, 6):
        assignments.append((f"HERPES{i:02d}", "HERPES", "NA"))
    for index, (patient, phenotype, hand) in enumerate(assignments, 1):
        rows.append({
            "sample_id": f"{index}_Slot1",
            "patient_id": patient,
            "phenotype": phenotype,
            "hand_status": hand,
            "raw_dda_files": f"dda_{index}.raw",
            "raw_dia_files": f"dia_{index}.raw",
            "relationship_to_patient": "PRIMARY",
            "mapping_rationale": "Synthetic fixture only; not a real clinical mapping",
            "source_url": "https://example.org/synthetic-manifest.tsv",
            "source_document_sha256": sha,
            "provenance_status": "SOURCE_AUTHENTICATED",
            "include_in_hiv_vs_herpes": "true",
            "include_in_hand_vs_cognitively_normal": "true" if phenotype == "HIV" else "false",
        })
    for alias, patient, phenotype, hand in [
        ("14_Slot1", "HIV01", "HIV", "HAND"),
        ("15_Slot1", "HIV02", "HIV", "HAND"),
    ]:
        rows.append({
            "sample_id": alias,
            "patient_id": patient,
            "phenotype": phenotype,
            "hand_status": hand,
            "raw_dda_files": f"dda_{alias}.raw",
            "raw_dia_files": f"dia_{alias}.raw",
            "relationship_to_patient": "TECHNICAL_REPLICATE",
            "mapping_rationale": "Synthetic fixture only; not a real clinical mapping",
            "source_url": "https://example.org/synthetic-manifest.tsv",
            "source_document_sha256": sha,
            "provenance_status": "SOURCE_AUTHENTICATED",
            "include_in_hiv_vs_herpes": "false",
            "include_in_hand_vs_cognitively_normal": "false",
        })
    return rows


def write_rows(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def test_valid_synthetic_crosswalk_is_ready(tmp_path):
    path = tmp_path / "mapping.tsv"
    write_rows(path, make_rows())
    report = validate_mapping(path)
    assert report["status"] == "READY_FOR_CLINICAL_VALIDATION"
    assert report["processed_aliases_mapped"] == 15
    assert report["distinct_included_clinical_patients"] == 13
    assert report["patient_phenotype_counts"] == {"HIV": 8, "HERPES": 5}
    assert report["patient_hand_counts"] == {"HAND": 5, "COGNITIVELY_NORMAL": 3}


def test_missing_alias_blocks_mapping(tmp_path):
    path = tmp_path / "mapping.tsv"
    write_rows(path, make_rows()[:-1])
    report = validate_mapping(path)
    assert report["status"] == "BLOCKED"
    assert any("Missing sample aliases" in error for error in report["errors"])


def test_technical_replicate_cannot_be_counted_twice(tmp_path):
    path = tmp_path / "mapping.tsv"
    rows = make_rows()
    rows[-1]["include_in_hiv_vs_herpes"] = "true"
    write_rows(path, rows)
    report = validate_mapping(path)
    assert report["status"] == "BLOCKED"
    assert any("technical replicate" in error for error in report["errors"])


def test_conflicting_patient_phenotype_blocks_mapping(tmp_path):
    path = tmp_path / "mapping.tsv"
    rows = make_rows()
    rows[-1]["phenotype"] = "HERPES"
    rows[-1]["hand_status"] = "NA"
    write_rows(path, rows)
    report = validate_mapping(path)
    assert report["status"] == "BLOCKED"
    assert any("conflicting phenotype/HAND" in error for error in report["errors"])


def test_unverified_row_cannot_carry_clinical_labels(tmp_path):
    path = tmp_path / "mapping.tsv"
    rows = make_rows()
    rows[-1]["provenance_status"] = "UNRESOLVED"
    rows[-1]["phenotype"] = "HIV"
    write_rows(path, rows)
    report = validate_mapping(path)
    assert report["status"] == "BLOCKED"
    assert any("unverified rows must not carry" in error for error in report["errors"])
