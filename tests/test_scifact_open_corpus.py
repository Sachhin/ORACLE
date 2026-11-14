import unittest

from scripts.predict_scifact_open_corpus import (
    BM25Index, build_prompt, generate_validated_prediction, retrieval_diagnostics,
)


class FakeModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate(self, messages, temperature=0.0):
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


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
        self.assertTrue(messages[1]["content"].startswith("/no_think"))
        self.assertNotIn("evidence", messages[1]["content"])
        self.assertNotIn("SUPPORT", messages[1]["content"])
        self.assertIn("candidate_abstracts", messages[1]["content"])

    def test_retries_malformed_json_and_accepts_only_validated_response(self):
        model = FakeModel([
            "not json",
            '{"evidence":[{"doc_id":"1","label":"SUPPORT","sentences":[0]}]}',
        ])
        evidence, retries, raw = generate_validated_prediction(
            model, [{"role": "user", "content": "claim"}], {"1": 1}, max_attempts=3
        )
        self.assertEqual(model.calls, 2)
        self.assertEqual(retries, 1)
        self.assertEqual(evidence["1"]["label"], "SUPPORT")
        self.assertIn('"evidence"', raw)

    def test_rejects_invalid_document_even_after_all_retries(self):
        model = FakeModel([
            '{"evidence":[{"doc_id":"999","label":"SUPPORT","sentences":[0]}]}',
            '{"evidence":[{"doc_id":"999","label":"SUPPORT","sentences":[0]}]}',
        ])
        with self.assertRaisesRegex(ValueError, "after 2 attempts"):
            generate_validated_prediction(
                model, [{"role": "user", "content": "claim"}], {"1": 1}, max_attempts=2
            )
        self.assertEqual(model.calls, 2)

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
