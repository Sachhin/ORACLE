import json
import tempfile
import unittest
from pathlib import Path
from argparse import Namespace

from scripts.verify_v1_release import verify


class ReleaseGateTests(unittest.TestCase):
    def test_release_gate_requires_every_external_and_engineering_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payloads = {
                "ci": {"required_checks": {"offline_tests": "success", "geo": "success", "qwen3": "success"}},
                "qwen": {"scored_claim_count": 300, "prediction_coverage": 1.0,
                         "prediction_run": {"requested_claims": 300, "gold_evidence_exposed_to_model": False,
                                            "predictions_sha256": "a", "corpus_sha256": "b", "claims_sha256": "c",
                                            "invalid_model_response_count": 0, "model": "Qwen3-1.7B"}},
                "provenance": {"model_sha256": "a", "verified_model_sha256": "a", "download_sha256_verified": True},
                "geo": {"status": "EXPLORATORY_ANALYSIS_COMPLETE", "accessions_requested": ["GSE58137", "GSE65219"],
                        "successful_platforms": [{"age_max_years": 99, "invalid_age_samples": 0},
                                                 {"age_max_years": 98, "invalid_age_samples": 0}], "failures": []},
                "cra": {"status": "metadata_acquired_and_cohort_validated",
                        "cohort_design_check": {"all_expected_group_labels_explicitly_present": True},
                        "biosample_join": {"unmatched_runs": 0},
                        "biosample_page_enrichment": {"samples_with_age": 171}},
                "pxd": {"status": "PROVENANCE_VALIDATED_READY_FOR_OUTCOME_ANALYSIS", "alias_count": 15,
                        "distinct_patient_count": 13, "errors": []},
                "longevity": {"overall_assessment": "screening_only_no_validated_discovery",
                              "hypothesis_reviews": [], "gates": {}},
                "expert": {"reviewers": [
                    {"reviewer_id": "r1", "status": "completed", "frozen_score_file_sha256": "x"},
                    {"reviewer_id": "r2", "status": "completed", "frozen_score_file_sha256": "y"}],
                    "blinded": True, "paired_corpus_frozen": True, "adjudication_complete": True},
            }
            paths = {}
            for name, payload in payloads.items():
                path = root / f"{name}.json"
                path.write_text(json.dumps(payload))
                paths[name] = str(path)
            args = Namespace(
                ci_summary=paths["ci"], qwen_report=paths["qwen"], qwen_provenance=paths["provenance"],
                geo_report=paths["geo"], cra_audit=paths["cra"], pxd_audit=paths["pxd"],
                longevity_audit=paths["longevity"], expert_review=paths["expert"],
            )
            report = verify(args)
            self.assertEqual(report["status"], "READY_FOR_V1_TAG")
            self.assertEqual(report["passed_gate_count"], report["total_gate_count"])

    def test_missing_artifacts_keep_release_blocked(self):
        args = Namespace(ci_summary="", qwen_report="", qwen_provenance="", geo_report="",
                         cra_audit="", pxd_audit="", longevity_audit="", expert_review="")
        report = verify(args)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["passed_gate_count"], 0)


if __name__ == "__main__":
    unittest.main()
