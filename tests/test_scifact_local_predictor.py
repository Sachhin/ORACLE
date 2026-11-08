import unittest

from scripts.predict_scifact_local import (
    parse_model_json, prompt_for_claim, validate_prediction,
)


class LocalSciFactPredictionTests(unittest.TestCase):
    def test_parses_fenced_json(self):
        self.assertEqual(
            parse_model_json('```json\n{"evidence": []}\n```'),
            {"evidence": []},
        )

    def test_parses_qwen_think_wrapper_and_leading_text(self):
        self.assertEqual(
            parse_model_json('<think>reasoning</think> Result: {"evidence": []}'),
            {"evidence": []},
        )

    def test_rejects_non_json_and_wrong_shape(self):
        with self.assertRaises(ValueError):
            parse_model_json("answer: support")
        with self.assertRaises(ValueError):
            parse_model_json('{"label":"SUPPORT"}')

    def test_rejects_unknown_document_and_invalid_sentence(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            validate_prediction({"evidence": [{
                "doc_id": "999", "label": "SUPPORT", "sentences": [0]
            }]}, {"1": 2})
        with self.assertRaisesRegex(ValueError, "sentence indices"):
            validate_prediction({"evidence": [{
                "doc_id": "1", "label": "SUPPORT", "sentences": [2]
            }]}, {"1": 2})

    def test_prompt_excludes_gold_labels_and_rationales(self):
        claim = {
            "id": 7, "claim": "A scientific claim.",
            "cited_doc_ids": [1],
            "evidence": {"1": [{"label": "SUPPORT", "sentences": [0]}]},
        }
        messages, allowed = prompt_for_claim(claim, {
            "1": {"doc_id": 1, "title": "Paper", "abstract": ["Evidence sentence."]}
        })
        import json
        user_payload = json.loads(messages[1]["content"])
        self.assertEqual(set(user_payload), {"claim_id", "claim", "candidate_abstracts"})
        self.assertNotIn("evidence", user_payload)
        self.assertNotIn("SUPPORT", messages[1]["content"])
        self.assertEqual(allowed, {"1": 1})

    def test_rejects_missing_cited_document_in_corpus(self):
        claim = {"id": 9, "claim": "Claim", "cited_doc_ids": [999]}
        with self.assertRaisesRegex(ValueError, "absent from corpus"):
            prompt_for_claim(claim, {})

    def test_rejects_duplicate_document_predictions(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_prediction({"evidence": [
                {"doc_id": "1", "label": "SUPPORT", "sentences": [0]},
                {"doc_id": "1", "label": "CONTRADICT", "sentences": [1]},
            ]}, {"1": 2})


if __name__ == "__main__":
    unittest.main()
