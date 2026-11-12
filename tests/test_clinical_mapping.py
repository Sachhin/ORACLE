import csv
import hashlib
from pathlib import Path

from oracle.clinical_mapping import validate_mapping


def _write_mapping(path: Path, rows):
    fields = ["sample_id", "patient_id", "phenotype", "hand_status",
              "raw_acquisition_files", "source_reference", "source_manifest_sha256"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _valid_rows():
    rows = []
    sha = hashlib.sha256(b"submitter manifest").hexdigest()
    # 15 processed aliases, 13 distinct patients: two HIV patients have
    # an additional acquisition alias. Labels are test fixtures only.
    assignments = [
        ("HIV01", "HIV", "HAND"), ("HIV01", "HIV", "HAND"),
        ("HIV02", "HIV", "HAND"), ("HIV03", "HIV", "HAND"),
        ("HIV04", "HIV", "HAND"), ("HIV05", "HIV", "HAND"),
        ("HIV06", "HIV", "COGNITIVELY_NORMAL"),
        ("HIV07", "HIV", "COGNITIVELY_NORMAL"),
        ("HIV08", "HIV", "COGNITIVELY_NORMAL"),
        ("HERPES01", "HERPES", "NA"), ("HERPES02", "HERPES", "NA"),
        ("HERPES03", "HERPES", "NA"), ("HERPES04", "HERPES", "NA"),
        ("HERPES05", "HERPES", "NA"), ("HIV02", "HIV", "HAND"),
    ]
    for index, (patient, phenotype, hand) in enumerate(assignments, 1):
        rows.append({
            "sample_id": f"{index}_Slot1", "patient_id": patient,
            "phenotype": phenotype, "hand_status": hand,
            "raw_acquisition_files": f"raw/run_{index}.raw",
            "source_reference": "submitter-manifest-v1",
            "source_manifest_sha256": sha,
        })
    return rows


def test_complete_authenticated_crosswalk_passes_structure(tmp_path):
    path = tmp_path / "map.tsv"
    _write_mapping(path, _valid_rows())
    result = validate_mapping(path)
    assert result["status"] == "READY_FOR_CLINICAL_VALIDATION"
    assert result["sample_aliases_mapped"] == 15
    assert result["distinct_patients"] == 13


def test_missing_alias_is_blocked(tmp_path):
    path = tmp_path / "map.tsv"
    _write_mapping(path, _valid_rows()[:-1])
    result = validate_mapping(path)
    assert result["status"] == "BLOCKED"
    assert any("Missing sample aliases" in error for error in result["errors"])


def test_unverifiable_source_checksum_is_blocked(tmp_path):
    rows = _valid_rows()
    rows[0]["source_manifest_sha256"] = "not-a-checksum"
    path = tmp_path / "map.tsv"
    _write_mapping(path, rows)
    result = validate_mapping(path)
    assert result["status"] == "BLOCKED"
    assert any("source_manifest_sha256" in error for error in result["errors"])


def test_inconsistent_patient_phenotype_is_blocked(tmp_path):
    rows = _valid_rows()
    rows[0]["phenotype"] = "HERPES"
    path = tmp_path / "map.tsv"
    _write_mapping(path, rows)
    result = validate_mapping(path)
    assert result["status"] == "BLOCKED"
    assert any("conflicting phenotypes" in error for error in result["errors"])
