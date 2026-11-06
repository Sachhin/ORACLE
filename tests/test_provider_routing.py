"""Provider routing contract tests; no live provider credentials are required."""
import unittest

from oracle.model_agents import GeminiAgentError, ProviderRouter


class FakeProvider:
    def __init__(self, model, result=None, error=None):
        self.model = model
        self.result = result or {"ok": True}
        self.error = error
        self.calls = 0

    def generate_json(self, prompt):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


class ProviderRouterTests(unittest.TestCase):
    def test_quota_failure_falls_back_and_records_active_model(self):
        primary = FakeProvider("gemini-model", error=GeminiAgentError("Gemini quota appears exhausted"))
        backup = FakeProvider("groq-model", {"answer": "fallback"})
        router = ProviderRouter([primary, backup])
        result = router.generate_json("prompt")
        self.assertEqual(result, {"answer": "fallback"})
        self.assertEqual(primary.calls, 1)
        self.assertEqual(backup.calls, 1)
        self.assertEqual(router.model, "groq-model")
        self.assertIs(router.last_provider, backup)

    def test_permanent_auth_error_does_not_silently_switch_provider(self):
        primary = FakeProvider("gemini-model", error=GeminiAgentError("Gemini HTTP 401: invalid API key"))
        backup = FakeProvider("groq-model")
        router = ProviderRouter([primary, backup])
        with self.assertRaises(GeminiAgentError):
            router.generate_json("prompt")
        self.assertEqual(backup.calls, 0)

    def test_transient_failures_exhaust_configured_chain_with_trace(self):
        primary = FakeProvider("gemini-model", error=GeminiAgentError("HTTP 503 unavailable"))
        backup = FakeProvider("openrouter-model", error=GeminiAgentError("HTTP 429 rate limit"))
        router = ProviderRouter([primary, backup])
        with self.assertRaisesRegex(GeminiAgentError, "All eligible provider attempts failed"):
            router.generate_json("prompt")
        self.assertEqual(primary.calls, 1)
        self.assertEqual(backup.calls, 1)


if __name__ == "__main__":
    unittest.main()
