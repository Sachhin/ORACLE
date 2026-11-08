import json
import tempfile
import unittest
from pathlib import Path

from scripts.evaluate_scifact_sentence_retrieval import (
    evaluate_sentence_retrieval,
    flatten_sentences,
)


class SciFactSentenceRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.claims = self.root / "claims.jsonl"
        self.corpus = self.root / "corpus.jsonl"
        claim_rows = [{
            "id": 1,
            "claim": "Telomere shortening causes cellular aging",
            "evidence": {
                "10": [{"label": "SUPPORT", "sentences": [0]}]
            },
        }]
        corpus_rows = [
            {"doc_id": 10, "title": "Telomeres", "abstract": [
                "Telomere shortening causes cellular aging.",
                "Marine salinity changes ocean chemistry.",
            ]},
            {"doc_id": 20, "title": "Unrelated", "abstract": [
                "DNA repair protects the genome from damage."
            ]},
        ]
        self.claims.write_text("".join(json.dumps(row) + "\n" for row in claim_rows))
        self.corpus.write_text("".join(json.dumps(row) + "\n" for row in corpus_rows))

    def tearDown(self):
        self.tmp.cleanup()

    def test_sentence_index_preserves_document_and_sentence_ids(self):
        rows, locations = flatten_sentences([
            {"doc_id": 7, "abstract": ["first", "second"]}
        ])
        self.assertEqual(len(rows), 2)
        self.assertEqual(locations["7::1"], ("7", 1))

    def test_sentence_retrieval_scores_gold_rationale_without_model(self):
        report = evaluate_sentence_retrieval(
            str(self.claims), str(self.corpus), top_k=1
        )
        self.assertEqual(report["scored_claim_count"], 1)
        self.assertEqual(report["sentence_metrics"]["matched_gold_sentences"], 1)
        self.assertEqual(report["sentence_metrics"]["recall"], 1.0)
        self.assertEqual(report["fully_retrieved_rationale_group_rate"], 1.0)
        self.assertIn("does not classify SUPPORT", report["limitations"])

    def test_rejects_invalid_top_k(self):
        with self.assertRaisesRegex(ValueError, "at least 1"):
            evaluate_sentence_retrieval(str(self.claims), str(self.corpus), top_k=0)

    def test_rejects_duplicate_corpus_ids(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            flatten_sentences([
                {"doc_id": 1, "abstract": ["a"]},
                {"doc_id": 1, "abstract": ["b"]},
            ])


if __name__ == "__main__":
    unittest.main()
