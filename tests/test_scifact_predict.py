import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oracle.model_agents import GeminiAgentError, ProviderRouter
from oracle.scifact_predict import BM25Retriever, _default_provider, generate_predictions


class FakeProvider:
    model = "fake-gemini"

    def __init__(self, result):
        self.result = result
        self.prompts = []

    def generate_json(self, prompt):
        self.prompts.append(prompt)
        return self.result


class SciFactPredictionTests(unittest.TestCase):
    def test_default_provider_configures_stable_gemini_fallbacks(self):
        created = []

        class StubGemini:
            def __init__(self, model):
                self.model = model
                created.append(model)

        with patch.dict("os.environ", {"ORACLE_GEMINI_FALLBACK_MODELS": "gemini-3.5-flash,gemini-3.5-flash-lite"}), \
             patch("oracle.scifact_predict.GeminiJSONProvider", StubGemini):
            provider = _default_provider("gemini-3.8-flash")
        self.assertIsInstance(provider, ProviderRouter)
        self.assertEqual(created, ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"])

    def test_provider_router_falls_back_after_transient_503(self):
        class Unavailable:
            model = "primary"

            def generate_json(self, prompt):
                raise GeminiAgentError("Gemini HTTP 503: temporarily unavailable")

        class Healthy:
            model = "fallback"

            def generate_json(self, prompt):
                return {"ok": True}

        router = ProviderRouter([Unavailable(), Healthy()])
        self.assertEqual(router.generate_json("test"), {"ok": True})
        self.assertEqual(router.model, "fallback")

    def test_bm25_retrieval_is_deterministic_and_returns_abstract_sentences(self):
        corpus = [
            {"doc_id": 2, "title": "Cell cycle", "abstract": ["Cell cycle control uses cyclins."]},
            {"doc_id": 1, "title": "Cell cycle", "abstract": ["Cell cycle control uses cyclins."]},
            {"doc_id": 3, "title": "Unrelated", "abstract": ["Ocean circulation changes."]},
        ]
        retriever = BM25Retriever(corpus)
        self.assertEqual([row["doc_id"] for row in retriever.retrieve("cell cycle cyclins", 2)], ["1", "2"])

    def test_predictions_do_not_expose_gold_labels_and_are_frozen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            claims = root / "claims_dev.jsonl"
            corpus = root / "corpus.jsonl"
            output = root / "predictions.jsonl"
            claims.write_text(json.dumps({
                "id": 7,
                "claim": "Cyclins regulate cell cycle progression.",
                "evidence": {"999": [{"label": "CONTRADICT", "sentences": [0]}]},
                "private_gold_sentinel": "GOLD_MUST_NEVER_REACH_MODEL",
            }) + "\n", encoding="utf-8")
            corpus.write_text(json.dumps({
                "doc_id": 10,
                "title": "Cell cycle control",
                "abstract": ["Cyclins regulate cell cycle progression."],
            }) + "\n", encoding="utf-8")
            provider = FakeProvider({"evidence": [
                {"doc_id": "10", "label": "SUPPORT", "sentences": [0]}
            ]})
            report = generate_predictions(
                claims, corpus, output, provider_factory=lambda _: provider
            )
            self.assertNotIn("GOLD_MUST_NEVER_REACH_MODEL", provider.prompts[0])
            self.assertNotIn('"999"', provider.prompts[0])
            prediction = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(prediction["evidence"]["10"]["label"], "SUPPORT")
            self.assertEqual(report["prediction_coverage"], 1.0)
            self.assertEqual(report["model"], "fake-gemini")
            self.assertTrue(Path(report["metadata_path"]).exists())

    def test_rejects_model_document_not_in_retrieved_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            claims, corpus, output = root / "claims.jsonl", root / "corpus.jsonl", root / "pred.jsonl"
            claims.write_text(json.dumps({"id": 1, "claim": "Cyclins regulate cell cycle."}) + "\n")
            corpus.write_text(json.dumps({
                "doc_id": 10, "title": "Cell cycle", "abstract": ["Cyclins regulate cell cycle."]
            }) + "\n")
            provider = FakeProvider({"evidence": [
                {"doc_id": "999", "label": "SUPPORT", "sentences": [0]}
            ]})
            with self.assertRaisesRegex(ValueError, "unretrieved document"):
                generate_predictions(claims, corpus, output, provider_factory=lambda _: provider)

    def test_rejects_invalid_sentence_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            claims, corpus, output = root / "claims.jsonl", root / "corpus.jsonl", root / "pred.jsonl"
            claims.write_text(json.dumps({"id": 1, "claim": "Cyclins regulate cell cycle."}) + "\n")
            corpus.write_text(json.dumps({
                "doc_id": 10, "title": "Cell cycle", "abstract": ["Cyclins regulate cell cycle."]
            }) + "\n")
            provider = FakeProvider({"evidence": [
                {"doc_id": "10", "label": "SUPPORT", "sentences": [5]}
            ]})
            with self.assertRaisesRegex(ValueError, "invalid abstract sentence indices"):
                generate_predictions(claims, corpus, output, provider_factory=lambda _: provider)


if __name__ == "__main__":
    unittest.main()
