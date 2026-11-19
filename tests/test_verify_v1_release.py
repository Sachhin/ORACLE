import json
import tempfile
import unittest
from pathlib import Path
from argparse import Namespace

from scripts.verify_v1_release import verify


class ReleaseGateTests(unittest.TestCase):
    def _write_payloads(self, root, payloads):
        paths = {}
        for name, payload in payloads.items():
            path = root / f"{name}.json"
            path.write_text(json.dumps(payload))
            paths[name] = str(path)
        return paths

    def _args(self, paths):
        return Namespace(
            ci_summary=paths["ci"], geo_report=paths["geo"], cra_audit=paths["cra"],
            pxd_audit=paths.get("pxd", ""), longevity_audit=paths["lon"], expert_review=paths["expert"],
        )

    def _base_payloads(self):
        return {
            "ci": {"required_checks": {"offline_tests": "success", "geo": "success", "riken2018": "success"}},
            "geo": {"status": "EXPLORATORY_ANALYSIS_COMPLETE",
                    "accessions_requested": ["GSE58137", "GSE65219"],
                    "successful_platforms": [{"age_max_years": 99, "invalid_age_samples": 0},
                                             {"age_max_years": 98, "invalid_age_samples": 0}],
                    "failures": []},
            "cra": {"unique_run_count": 171, "unique_biosample_count": 171,
                    "biosample_page_enrichment": {"requested_unique_biosamples": 171,
                                                  "retrieved_unique_biosamples": 171,
                                                  "samples_with_age": 171},
                    "cohort_design_check": {"all_expected_group_labels_explicitly_present": True}},
            "pxd": {"status": "PROVENANCE_VALIDATED_READY_FOR_OUTCOME_ANALYSIS",
                    "alias_count": 15, "distinct_patient_count": 13, "errors": []},
            "lon": {"overall_assessment": "MIXED_EXPLORATORY_NO_VALIDATED_DISCOVERY",
                    "validated_new_mechanism_count": 0},
            "expert": {"reviewers": [
                {"reviewer_id": "r1", "status": "completed", "frozen_score_file_sha256": "x"},
                {"reviewer_id": "r2", "status": "completed", "frozen_score_file_sha256": "y"}],
                "blinded": True, "paired_corpus_frozen": True, "adjudication_complete": True},
        }

    def test_release_gate_passes_core_requirements_and_reports_optional_pxd(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_payloads(root, self._base_payloads())
            report = verify(self._args(paths))
            self.assertEqual(report["status"], "READY_FOR_V1_TAG")
            self.assertEqual(report["passed_gate_count"], report["total_gate_count"])
            optional = {item["gate"]: item["status"] for item in report["optional_checks"]}
            self.assertEqual(optional["pxd047528_clinical_outcome_crosswalk"], "PASS")

    def test_unrelated_pxd_clinical_mapping_does_not_block_longevity_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payloads = self._base_payloads()
            payloads["pxd"] = {
                "status": "BLOCKED_INVALID_OR_INCOMPLETE_CROSSWALK",
                "alias_count": 15, "distinct_patient_count": 0,
                "errors": ["source manifest missing"],
            }
            paths = self._write_payloads(root, payloads)
            report = verify(self._args(paths))
            self.assertEqual(report["status"], "READY_FOR_V1_TAG")
            optional = {item["gate"]: item["status"] for item in report["optional_checks"]}
            self.assertEqual(optional["pxd047528_clinical_outcome_crosswalk"], "NOT_REQUIRED_FOR_LONGEVITY_RELEASE")

    def test_real_longevity_and_expert_blockers_keep_release_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payloads = self._base_payloads()
            payloads["cra"] = {
                "unique_run_count": 171, "unique_biosample_count": 171,
                "biosample_page_enrichment": {"requested_unique_biosamples": 171,
                                              "retrieved_unique_biosamples": 171,
                                              "samples_with_age": 0},
                "cohort_design_check": {"all_expected_group_labels_explicitly_present": False},
            }
            payloads["expert"] = {
                "reviewers": [], "blinded": False, "paired_corpus_frozen": False,
                "adjudication_complete": False,
            }
            payloads["pxd"] = {
                "status": "BLOCKED_INVALID_OR_INCOMPLETE_CROSSWALK",
                "alias_count": 15, "distinct_patient_count": 0,
                "errors": ["source manifest missing"],
            }
            paths = self._write_payloads(root, payloads)
            report = verify(self._args(paths))
            self.assertEqual(report["status"], "BLOCKED")
            gates = {item["gate"]: item["status"] for item in report["checks"]}
            self.assertEqual(gates["cra000515_accession_provenance"], "PASS")
            self.assertEqual(gates["cra000515_authenticated_age_and_cohort_labels"], "BLOCKED")
            self.assertEqual(gates["independent_blinded_expert_review"], "BLOCKED")
            optional = {item["gate"]: item["status"] for item in report["optional_checks"]}
            self.assertEqual(optional["pxd047528_clinical_outcome_crosswalk"], "NOT_REQUIRED_FOR_LONGEVITY_RELEASE")

    def test_missing_required_artifacts_keep_release_blocked(self):
        args = Namespace(ci_summary="", geo_report="", cra_audit="", pxd_audit="",
                         longevity_audit="", expert_review="")
        report = verify(args)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["passed_gate_count"], 0)
        self.assertTrue(all(item["status"] == "BLOCKED" for item in report["checks"]))
        self.assertEqual(report["optional_checks"][0]["status"], "NOT_REQUIRED_FOR_LONGEVITY_RELEASE")


if __name__ == "__main__":
    unittest.main()
