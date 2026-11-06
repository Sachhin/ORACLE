import json
import tempfile
import unittest
from pathlib import Path

from oracle.blinded_review import build_blinded_packets, unblind_paired_reviews
from oracle.model_comparison import evaluate_paired_answers


class BlindedReviewTests(unittest.TestCase):
    def fixture(self, root):
        source_packet = {"paper": [{"source_id": "S1", "text": "frozen abstract"}]}
        payload = {"benchmark_id": "test", "cases": [{
            "case_id": "C1", "question": "Question?", "source_packet": source_packet,
            "baseline_answer": "Baseline answer", "candidate_answer": "Candidate answer",
            "prompt_version": "prompt-v1", "model_version": "baseline-v1|candidate-v1",
        }]}
        path = root / "input.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path, payload

    def test_builds_blinded_packets_and_unblinds_paired_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path, payload = self.fixture(root)
            built = build_blinded_packets(input_path, root / "out", ["reviewer-1", "reviewer-2"], seed=17)
            self.assertEqual(built["reviewer_count"], 2)
            score_paths, key_paths = [], []
            for item in built["created"]:
                packet = json.loads(Path(item["packet"]).read_text())
                self.assertNotIn("baseline", json.dumps(packet).lower())
                self.assertNotIn("candidate", json.dumps(packet).lower())
                scores = json.loads(Path(item["scores_template"]).read_text())
                scores["cases"][0]["scores_A"] = {
                    "factual_accuracy": 4, "evidence_traceability": 4,
                    "uncertainty_calibration": 4, "reasoning_quality": 4, "completeness": 4}
                scores["cases"][0]["scores_B"] = {
                    "factual_accuracy": 5, "evidence_traceability": 5,
                    "uncertainty_calibration": 5, "reasoning_quality": 5, "completeness": 5}
                score_path = root / (scores["reviewer_id"] + ".scores.json")
                score_path.write_text(json.dumps(scores), encoding="utf-8")
                score_paths.append(score_path)
                key_paths.append(Path(item["private_key"]))
            output = root / "unblinded.json"
            result = unblind_paired_reviews(input_path, score_paths, key_paths, output)
            self.assertEqual(result["reviewer_count"], 2)
            final = json.loads(output.read_text())
            report = evaluate_paired_answers(final["cases"], bootstrap_samples=100)
            self.assertEqual(report["reviewer_count"], 2)
            self.assertEqual(report["case_count"], 1)

    def test_rejects_source_packet_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, payload = self.fixture(root)
            payload["cases"][0]["source_packet_sha256"] = "0" * 64
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match"):
                build_blinded_packets(path, root / "out", ["r1", "r2"])

    def test_requires_two_reviewers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, _ = self.fixture(root)
            with self.assertRaisesRegex(ValueError, "At least two"):
                build_blinded_packets(path, root / "out", ["r1"])

    def test_rejects_missing_scores_during_unblinding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, _ = self.fixture(root)
            built = build_blinded_packets(path, root / "out", ["r1", "r2"])
            scores = []
            keys = []
            for item in built["created"]:
                score = json.loads(Path(item["scores_template"]).read_text())
                score_path = root / (score["reviewer_id"] + ".json")
                score_path.write_text(json.dumps(score), encoding="utf-8")
                scores.append(score_path)
                keys.append(Path(item["private_key"]))
            with self.assertRaisesRegex(ValueError, "integer from 1 to 5"):
                unblind_paired_reviews(path, scores, keys, root / "out.json")


if __name__ == "__main__":
    unittest.main()
