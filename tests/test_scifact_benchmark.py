import json
import tempfile
import unittest
from pathlib import Path

from oracle.scifact_benchmark import evaluate_scifact


class SciFactBenchmarkTests(unittest.TestCase):
    def test_scores_stance_and_rationale_retrieval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            claims = root / "claims_dev.jsonl"
            corpus = root / "corpus.jsonl"
            predictions = root / "predictions.jsonl"
            claims.write_text("\n".join([
                json.dumps({"id": 1, "claim": "Claim A", "cited_doc_ids": [10, 11],
                            "evidence": {"10": [{"label": "SUPPORT", "sentences": [0, 1]}]}}),
                json.dumps({"id": 2, "claim": "Claim B", "cited_doc_ids": [11],
                            "evidence": {}}),
                json.dumps({"id": 3, "claim": "Claim C", "cited_doc_ids": [12],
                            "evidence": {"12": [{"label": "CONTRADICT", "sentences": [2]}]}}),
            ]), encoding="utf-8")
            corpus.write_text("\n".join([
                json.dumps({"doc_id": 10, "title": "A", "abstract": ["s0", "s1"]}),
                json.dumps({"doc_id": 11, "title": "B", "abstract": ["s0"]}),
                json.dumps({"doc_id": 12, "title": "C", "abstract": ["s0", "s1", "s2"]}),
            ]), encoding="utf-8")
            predictions.write_text("\n".join([
                json.dumps({"id": 1, "evidence": {"10": {"label": "SUPPORT", "sentences": [0, 1]}}}),
                json.dumps({"id": 2, "evidence": {}}),
                json.dumps({"id": 3, "evidence": {"12": {"label": "CONTRADICT", "sentences": [2]}}}),
            ]), encoding="utf-8")
            report = evaluate_scifact(claims, corpus, predictions)
            self.assertEqual(report["claim_count"], 3)
            self.assertEqual(report["stance_accuracy"], 1.0)
            self.assertEqual(report["abstract_level_evidence"]["f1"], 1.0)
            self.assertEqual(report["sentence_level_evidence"]["f1"], 1.0)
            self.assertEqual(report["prediction_coverage"], 1.0)

    def test_incomplete_rationale_is_not_correct_abstract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            claims, corpus, predictions = [root / n for n in ("claims.jsonl", "corpus.jsonl", "pred.jsonl")]
            claims.write_text(json.dumps({"id": 1, "claim": "A", "evidence": {
                "10": [{"label": "SUPPORT", "sentences": [0, 1]}]}}) + "\n")
            corpus.write_text(json.dumps({"doc_id": 10, "abstract": ["a", "b"]}) + "\n")
            predictions.write_text(json.dumps({"id": 1, "evidence": {
                "10": {"label": "SUPPORT", "sentences": [0]}}}) + "\n")
            report = evaluate_scifact(claims, corpus, predictions)
            self.assertEqual(report["abstract_level_evidence"]["correct"], 0)
            self.assertEqual(report["sentence_level_evidence"]["correct"], 0)


    def test_rejects_prediction_sentence_outside_abstract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            claims, corpus, predictions = [root / n for n in ("claims.jsonl", "corpus.jsonl", "pred.jsonl")]
            claims.write_text(json.dumps({"id": 1, "claim": "A", "evidence": {}}) + "\\n")
            corpus.write_text(json.dumps({"doc_id": 10, "abstract": ["only sentence"]}) + "\\n")
            predictions.write_text(json.dumps({"id": 1, "evidence": {
                "10": {"label": "SUPPORT", "sentences": [1]}}}) + "\\n")
            with self.assertRaisesRegex(ValueError, "in-range abstract indices"):
                evaluate_scifact(claims, corpus, predictions)

    def test_rejects_gold_sentence_outside_abstract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            claims, corpus, predictions = [root / n for n in ("claims.jsonl", "corpus.jsonl", "pred.jsonl")]
            claims.write_text(json.dumps({"id": 1, "claim": "A", "evidence": {
                "10": [{"label": "SUPPORT", "sentences": [2]}]}}) + "\\n")
            corpus.write_text(json.dumps({"doc_id": 10, "abstract": ["only sentence"]}) + "\\n")
            predictions.write_text(json.dumps({"id": 1, "evidence": {}}) + "\\n")
            with self.assertRaisesRegex(ValueError, "gold sentence index is outside"):
                evaluate_scifact(claims, corpus, predictions)

    def test_rejects_unlabelled_test_split(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            claims, corpus, predictions = [root / n for n in ("claims.jsonl", "corpus.jsonl", "pred.jsonl")]
            claims.write_text(json.dumps({"id": 1, "claim": "A"}) + "\n")
            corpus.write_text(json.dumps({"doc_id": 10, "abstract": ["a"]}) + "\n")
            predictions.write_text(json.dumps({"id": 1, "evidence": {}}) + "\n")
            with self.assertRaisesRegex(ValueError, "test gold labels are withheld"):
                evaluate_scifact(claims, corpus, predictions, split="test")

    def test_rejects_prediction_document_outside_corpus(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            claims, corpus, predictions = [root / n for n in ("claims.jsonl", "corpus.jsonl", "pred.jsonl")]
            claims.write_text(json.dumps({"id": 1, "claim": "A", "evidence": {}}) + "\n")
            corpus.write_text(json.dumps({"doc_id": 10, "abstract": ["a"]}) + "\n")
            predictions.write_text(json.dumps({"id": 1, "evidence": {
                "99": {"label": "SUPPORT", "sentences": [0]}}}) + "\n")
            with self.assertRaisesRegex(ValueError, "absent from the supplied corpus"):
                evaluate_scifact(claims, corpus, predictions)


if __name__ == "__main__":
    unittest.main()
