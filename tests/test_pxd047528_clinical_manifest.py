import csv
import tempfile
import unittest
from pathlib import Path

from scripts.validate_pxd047528_clinical_manifest import validate_manifest, EXPECTED_SAMPLES


HEADERS = [
    "sample_id", "patient_id", "phenotype", "hand_status", "raw_dda_files",
    "raw_dia_files", "relationship_to_patient", "mapping_rationale",
    "source_url", "source_document_sha256", "provenance_status",
]


def valid_rows():
    rows = []
    patients = []
    for i in range(1, 9):
        hand = "MND" if i <= 3 else "HAD" if i <= 5 else "COGNITIVELY_NORMAL"
        patients.append((f"HIV{i}", "HIV", hand))
    for i in range(1, 6):
        patients.append((f"HERPES{i}", "HERPES", "NOT_APPLICABLE"))
    sample_no = 1
    for patient, phenotype, hand in patients:
        rows.append({
            "sample_id": f"{sample_no}_Slot1", "patient_id": patient,
            "phenotype": phenotype, "hand_status": hand,
            "raw_dda_files": f"{patient}_DDA.raw", "raw_dia_files": f"{patient}_DIA.raw",
            "relationship_to_patient": "PRIMARY", "mapping_rationale": "Explicit in submitter manifest",
            "source_url": "https://example.org/source-manifest.tsv",
            "source_document_sha256": "a" * 64, "provenance_status": "SUBMITTER_CONFIRMED",
        })
        sample_no += 1
    for patient in ("HIV1", "HIV2"):
        phenotype = "HIV"
        hand = "MND" if patient == "HIV1" else "MND"
        rows.append({
            "sample_id": f"{sample_no}_Slot1", "patient_id": patient,
            "phenotype": phenotype, "hand_status": hand,
            "raw_dda_files": f"{patient}_repeat_DDA.raw", "raw_dia_files": f"{patient}_repeat_DIA.raw",
            "relationship_to_patient": "TECHNICAL_REPLICATE", "mapping_rationale": "Submitter identifies repeated acquisition",
            "source_url": "https://example.org/source-manifest.tsv",
            "source_document_sha256": "a" * 64, "provenance_status": "SUBMITTER_CONFIRMED",
        })
        sample_no += 1
    return rows


class PXD047528ManifestTests(unittest.TestCase):
    def write_manifest(self, rows):
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name) / "crosswalk.tsv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=HEADERS, delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
        return tmp, path

    def test_accepts_source_provenance_complete_15_to_13_mapping(self):
        tmp, path = self.write_manifest(valid_rows())
        try:
            report = validate_manifest(path)
            self.assertEqual(report["status"], "PROVENANCE_VALIDATED_READY_FOR_OUTCOME_ANALYSIS")
            self.assertEqual(report["alias_count"], 15)
            self.assertEqual(report["distinct_patient_count"], 13)
            self.assertEqual(report["phenotype_patient_counts"], {"HIV": 8, "HERPES": 5})
            self.assertEqual(report["hiv_hand_patient_counts"], {"MND": 3, "HAD": 2, "COGNITIVELY_NORMAL": 3})
        finally:
            tmp.cleanup()

    def test_rejects_wrong_patient_count_and_missing_provenance(self):
        rows = valid_rows()
        rows[0]["patient_id"] = "HIV2"
        rows[13]["patient_id"] = "HIV2"
        rows[0]["source_document_sha256"] = ""
        tmp, path = self.write_manifest(rows)
        try:
            report = validate_manifest(path)
            self.assertEqual(report["status"], "BLOCKED_INVALID_OR_INCOMPLETE_CROSSWALK")
            self.assertTrue(any("13 distinct clinical patients" in item for item in report["errors"]))
            self.assertTrue(any("SHA-256" in item for item in report["errors"]))
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
