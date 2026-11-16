import unittest

from scripts.predict_scifact_open_corpus import BM25Index, build_prompt, retrieval_diagnostics, select_model_context


class OpenCorpusSciFactTests(unittest.TestCase):
    def setUp(self):
        self.corpus = [
            {"doc_id": 1, "title": "Telomere biology", "abstract": ["Telomere shortening is associated with cellular aging."]},
            {"doc_id": 2, "title": "Ocean chemistry", "abstract": ["Salinity affects marine carbonate chemistry."]},
            {"doc_id": 3, "title": "DNA repair", "abstract": ["DNA repair pathways protect cells from genomic damage."]},
        ]

    def test_bm25_retrieves_relevant_document_and_is_deterministic(self):
        index = BM25Index(self.corpus)
        first = index.search("telomere shortening cellular aging", top_k=2)
        second = index.search("telomere shortening cellular aging", top_k=2)
        self.assertEqual(first, second)
        self.assertEqual(first[0][0], "1")
        self.assertLessEqual(len(first), 2)

    def test_rejects_invalid_top_k(self):
        with self.assertRaisesRegex(ValueError, "at least 1"):
            BM25Index(self.corpus).search("DNA repair", top_k=0)

    def test_model_prompt_contains_candidates_but_not_gold_labels(self):
        claim = {
            "id": 7,
            "claim": "Telomere shortening is associated with aging.",
            "evidence": {"1": [{"label": "SUPPORT", "sentences": [0]}]},
        }
        messages, allowed = build_prompt(claim, [self.corpus[0]])
        self.assertEqual(allowed, {"1": 1})
        self.assertNotIn("evidence", messages[1]["content"])
        self.assertNotIn("SUPPORT", messages[1]["content"])
        self.assertIn("candidate_abstracts", messages[1]["content"])

    def test_retrieval_candidates_are_separate_from_model_context(self):
        retrieved = ["d1", "d2", "d3", "d4", "d5", "d6"]
        context = select_model_context(retrieved, 4)
        self.assertEqual(context, ["d1", "d2", "d3", "d4"])
        self.assertEqual(len(retrieved), 6)

    def test_model_context_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "at least 1"):
            select_model_context(["d1"], 0)

    def test_retrieval_and_model_context_recall_are_reported_separately(self):
        claims = [{"id": 1, "evidence": {"d5": [{"label": "SUPPORT", "sentences": [0]}]}}]
        top20 = {"1": ["d1", "d2", "d3", "d4", "d5"]}
        context4 = {"1": ["d1", "d2", "d3", "d4"]}
        self.assertEqual(retrieval_diagnostics(claims, top20)["document_recall"], 1.0)
        self.assertEqual(retrieval_diagnostics(claims, context4)["document_recall"], 0.0)

    def test_retrieval_diagnostics_are_post_inference_gold_only(self):
        claims = [
            {"id": 1, "evidence": {"10": [{"label": "SUPPORT", "sentences": [0]}]}},
            {"id": 2, "evidence": {}},
        ]
        report = retrieval_diagnostics(claims, {"1": ["10"], "2": []})
        self.assertEqual(report["claim_hit_rate"], 1.0)
        self.assertEqual(report["document_recall"], 1.0)
        self.assertEqual(report["gold_evidence_claims"], 1)


if __name__ == "__main__":
    unittest.main()
