import json
import tempfile
import unittest
from pathlib import Path

from oracle.scifact_predict import BM25Index, predict_scifact


class StubProvider:
    def __init__(self, response):
        self.response = response
        self.prompts = []

    def generate_json(self, prompt):
        self.prompts.append(prompt)
        return self.response


class SciFactPredictionTests(unittest.TestCase):
    def write_jsonl(self, path, rows):
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def test_bm25_retrieval_is_relevant_and_deterministic(self):
        corpus = [
            {"doc_id": "2", "title": "Alpha", "abstract": ["Beta pathway is activated."]},
            {"doc_id": "1", "title": "Alpha", "abstract": ["Beta pathway is activated."]},
            {"doc_id": "3", "title": "Other", "abstract": ["Unrelated words only."]},
        ]
        index = BM25Index(corpus)
        first = [x["doc_id"] for x in index.retrieve("beta pathway", top_k=2)]
        second = [x["doc_id"] for x in index.retrieve("beta pathway", top_k=2)]
        self.assertEqual(first, ["1", "2"])
        self.assertEqual(first, second)

    def test_prediction_rejects_hallucinated_quotes_and_unknown_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            claims = root / "claims.jsonl"
            corpus = root / "corpus.jsonl"
            predictions = root / "predictions.jsonl"
            report = root / "report.json"
            self.write_jsonl(claims, [{"id": 1, "claim": "Beta pathway is activated.", "evidence": {}}])
            self.write_jsonl(corpus, [
                {"doc_id": 10, "title": "Beta", "abstract": ["Beta pathway is activated in cells."]}
            ])
            provider = StubProvider({"evidence": [
                {"doc_id": "10", "label": "SUPPORT", "sentences": [0],
                 "quote": "Invented evidence sentence."},
                {"doc_id": "999", "label": "SUPPORT", "sentences": [0],
                 "quote": "Beta pathway is activated in cells."},
            ]})
            result = predict_scifact(claims, corpus, predictions, report,
                provider=provider, model="test-model", max_claims=1, top_k=1)
            rows = [json.loads(x) for x in predictions.read_text().splitlines()]
            self.assertEqual(rows, [{"id": "1", "evidence": {}}])
            self.assertEqual(result["invalid_model_evidence_items_rejected"], 2)
            self.assertFalse(result["gold_labels_used_for_prediction"])

    def test_accepts_only_exact_quote_from_retrieved_sentence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            claims, corpus = root / "claims.jsonl", root / "corpus.jsonl"
            predictions, report = root / "pred.jsonl", root / "report.json"
            self.write_jsonl(claims, [{"id": "C1", "claim": "Beta pathway is activated.", "evidence": {}}])
            self.write_jsonl(corpus, [{"doc_id": "D1", "title": "Beta", "abstract": [
                "Beta pathway is activated in cells.", "No adverse effect was observed."
            ]}])
            provider = StubProvider({"evidence": [{
                "doc_id": "D1", "label": "SUPPORT", "sentences": [0],
                "quote": "Beta pathway is activated in cells."
            }]})
            predict_scifact(claims, corpus, predictions, report, provider=provider,
                            model="test-model", max_claims=1, top_k=1)
            row = json.loads(predictions.read_text())
            self.assertEqual(row["evidence"]["D1"]["sentences"], [0])
            self.assertEqual(row["evidence"]["D1"]["label"], "SUPPORT")

    def test_invalid_retrieval_configuration_fails(self):
        with self.assertRaises(ValueError):
            BM25Index([{"doc_id": "D", "title": "", "abstract": ["text"]}]).retrieve("text", top_k=0)


if __name__ == "__main__":
    unittest.main()
