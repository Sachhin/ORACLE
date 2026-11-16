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
            pxd_audit=paths["pxd"], longevity_audit=paths["lon"], expert_review=paths["expert"],
        )

    def test_release_gate_requires_every_external_and_engineering_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payloads = {
                "ci": {"required_checks": {"offline_tests": "success", "geo": "success", "riken2018": "success"}},
                "geo": {"status": "EXPLORATORY_ANALYSIS_COMPLETE",
                        "accessions_requested": ["GSE58137", "GSE65219"],
                        "successful_platforms": [{"age_max_years": 99, "invalid_age_samples": 0},
                                                 {"age_max_years": 98, "invalid_age_samples": 0}],
                        "failures": []},
                "cra": {"accession_provenance": {"unique_run_count": 171,
                                                  "unique_biosample_count": 171,
                                                  "unique_alias_count": 171},
                        "biosample_page_enrichment": {"samples_with_age": 171,
                                                      "samples_with_explicit_group": 171}},
                "pxd": {"status": "PROVENANCE_VALIDATED_READY_FOR_OUTCOME_ANALYSIS",
                        "alias_count": 15, "distinct_patient_count": 13, "errors": []},
                "lon": {"overall_assessment": "MIXED_EXPLORATORY_NO_VALIDATED_DISCOVERY",
                        "validated_new_mechanism_count": 0},
                "expert": {"reviewers": [
                    {"reviewer_id": "r1", "status": "completed", "frozen_score_file_sha256": "x"},
                    {"reviewer_id": "r2", "status": "completed", "frozen_score_file_sha256": "y"}],
                    "blinded": True, "paired_corpus_frozen": True, "adjudication_complete": True},
            }
            paths = self._write_payloads(root, payloads)
            report = verify(self._args(paths))
            self.assertEqual(report["status"], "READY_FOR_V1_TAG")
            self.assertEqual(report["passed_gate_count"], report["total_gate_count"])

    def test_real_current_blockers_keep_release_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payloads = {
                "ci": {"required_checks": {"offline_tests": "success", "geo": "success", "riken2018": "success"}},
                "geo": {"status": "EXPLORATORY_ANALYSIS_COMPLETE",
                        "accessions_requested": ["GSE58137", "GSE65219"],
                        "successful_platforms": [{"age_max_years": 99, "invalid_age_samples": 0},
                                                 {"age_max_years": 98, "invalid_age_samples": 0}],
                        "failures": []},
                "cra": {"accession_provenance": {"unique_run_count": 171,
                                                  "unique_biosample_count": 171,
                                                  "unique_alias_count": 171},
                        "biosample_page_enrichment": {"samples_with_age": 0,
                                                      "samples_with_explicit_group": 0}},
                "pxd": {"status": "BLOCKED_INVALID_OR_INCOMPLETE_CROSSWALK",
                        "alias_count": 15, "distinct_patient_count": 0, "errors": ["source manifest missing"]},
                "lon": {"overall_assessment": "MIXED_EXPLORATORY_NO_VALIDATED_DISCOVERY",
                        "validated_new_mechanism_count": 0},
                "expert": {"reviewers": [], "blinded": False, "paired_corpus_frozen": False,
                           "adjudication_complete": False},
            }
            paths = self._write_payloads(root, payloads)
            report = verify(self._args(paths))
            self.assertEqual(report["status"], "BLOCKED")
            gates = {item["gate"]: item["status"] for item in report["checks"]}
            self.assertEqual(gates["cra000515_accession_provenance"], "PASS")
            self.assertEqual(gates["cra000515_authenticated_age_and_cohort_labels"], "BLOCKED")
            self.assertEqual(gates["pxd047528_authenticated_clinical_crosswalk"], "BLOCKED")
            self.assertEqual(gates["independent_blinded_expert_review"], "BLOCKED")

    def test_missing_artifacts_keep_release_blocked(self):
        args = Namespace(ci_summary="", geo_report="", cra_audit="", pxd_audit="",
                         longevity_audit="", expert_review="")
        report = verify(args)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["passed_gate_count"], 0)
        self.assertTrue(all(item["status"] == "BLOCKED" for item in report["checks"]))


if __name__ == "__main__":
    unittest.main()
