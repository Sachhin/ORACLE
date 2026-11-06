import json
import tempfile
import unittest
from pathlib import Path
from oracle.evidence_benchmark import evaluate_evidence_predictions, run_evidence_benchmark

class EvidenceBenchmarkTests(unittest.TestCase):
    def case(self, **overrides):
        row = {"case_id":"E1","gold_stance":"supports","predicted_stance":"supports",
               "reviewer_ids":["R1","R2"],"predicted_source_id":"S1",
               "allowed_source_ids":["S1","S2"],"predicted_quote":"supports the claim",
               "source_text":"This passage supports the claim in this context."}
        row.update(overrides)
        return row
    def test_reports_classification_and_provenance_metrics(self):
        rows = [self.case(), self.case(case_id="E2",gold_stance="refutes",
                 predicted_stance="contextual",predicted_source_id="BAD",
                 predicted_quote="invented")]
        report = evaluate_evidence_predictions(rows)
        self.assertEqual(report["case_count"], 2)
        self.assertEqual(report["accuracy"], .5)
        self.assertEqual(report["source_attribution_valid_rate"], .5)
        self.assertEqual(report["exact_quote_valid_rate"], .5)
    def test_requires_two_reviewers(self):
        with self.assertRaisesRegex(ValueError,"two distinct reviewers"):
            evaluate_evidence_predictions([self.case(reviewer_ids=["R1"])])
    def test_rejects_duplicate_reviewer_ids(self):
        with self.assertRaisesRegex(ValueError, "two distinct reviewers"):
            evaluate_evidence_predictions([self.case(reviewer_ids=["R1","R1"])])
    def test_requires_adjudication_for_three_or_more_reviewers(self):
        with self.assertRaisesRegex(ValueError,"adjudication_note"):
            evaluate_evidence_predictions([self.case(reviewer_ids=["R1","R2","R3"])])
    def test_reports_inter_reviewer_agreement_and_coverage(self):
        rows = [
            self.case(case_id="E1", reviewer_labels={"R1":"supports","R2":"supports"}),
            self.case(case_id="E2", reviewer_labels={"R1":"refutes","R2":"contextual"},
                      predicted_source_id=None, predicted_quote=None,
                      adjudication_note="Reviewers disagreed; adjudicated as refutes after source inspection.",
                      adjudicator_id="adjudicator-1"),
        ]
        report = evaluate_evidence_predictions(rows)
        self.assertEqual(report["reviewer_annotation_cases"], 4)
        self.assertEqual(report["reviewer_pair_agreement"]["R1__R2"]["paired_cases"], 2)
        self.assertAlmostEqual(report["reviewer_pair_agreement"]["R1__R2"]["observed_agreement"], .5)
        self.assertEqual(report["source_attribution_coverage"], .5)
        self.assertEqual(report["quote_coverage"], .5)
        self.assertIsNotNone(report["mean_pairwise_cohen_kappa"])
    def test_disagreement_requires_explicit_adjudication(self):
        row = self.case(reviewer_labels={"R1":"supports","R2":"refutes"})
        with self.assertRaisesRegex(ValueError, "adjudication_note and adjudicator_id"):
            evaluate_evidence_predictions([row])
        row["adjudication_note"] = "Original passage is contextual; claim scope is too broad."
        row["adjudicator_id"] = "senior-reviewer"
        report = evaluate_evidence_predictions([row])
        self.assertEqual(report["case_count"], 1)
    def test_reviewer_labels_must_cover_reviewers(self):
        row = self.case(reviewer_labels={"R1":"supports"})
        with self.assertRaisesRegex(ValueError, "every reviewer_id"):
            evaluate_evidence_predictions([row])
    def test_file_runner_hashes_benchmark(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"bench.json"
            path.write_text(json.dumps({"benchmark_id":"x","version":"1","cases":[self.case()]}))
            report=run_evidence_benchmark(path)
            self.assertEqual(len(report["benchmark_sha256"]),64)

if __name__ == "__main__":
    unittest.main()
