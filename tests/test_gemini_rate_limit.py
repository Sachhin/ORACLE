import io
import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from oracle.model_agents import GeminiAgentError, GeminiJSONProvider


class GeminiPerMinuteRetryTests(unittest.TestCase):
    def test_per_minute_429_waits_for_provider_retry_guidance(self):
        detail = json.dumps({
            "error": {
                "code": 429,
                "message": "Quota exceeded for generate_content_free_tier_requests_per_minute. Please retry in 0.25s."
            }
        }).encode()
        error = _BodyHTTPError(detail)

        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, *_):
                return json.dumps({
                                        "candidates": [{"content": {"parts": [{"text": json.dumps({"ok": True})}]}}]
                }).encode()

        provider = GeminiJSONProvider(api_key="test-key", model="gemini-3.5-flash-lite", max_retries=1)
        with patch("oracle.model_agents.urlopen", side_effect=[error, Response()]) as request, \
             patch("oracle.model_agents.time.sleep") as sleep:
            self.assertEqual(provider.generate_json("prompt"), {"ok": True})
        self.assertEqual(request.call_count, 2)
        sleep.assert_called_once()
        self.assertGreaterEqual(sleep.call_args.args[0], 0.25)

    def test_daily_quota_429_is_not_retried(self):
        detail = json.dumps({
            "error": {
                "code": 429,
                "message": "Generate content requests per day limit exceeded on Free Tier."
            }
        }).encode()
        error = HTTPError("https://example.invalid", 429, "Too Many Requests", {}, io.BytesIO(detail))
        provider = GeminiJSONProvider(api_key="test-key", model="gemini-3.8-flash", max_retries=2)
        with patch("oracle.model_agents.urlopen", side_effect=error) as request:
            with self.assertRaisesRegex(GeminiAgentError, "daily quota appears exhausted"):
                provider.generate_json("prompt")
        self.assertEqual(request.call_count, 1)


if __name__ == "__main__":
    unittest.main()

class _BodyHTTPError(HTTPError):
    def __init__(self, payload):
        super().__init__("https://example.invalid", 429, "Too Many Requests", {}, None)
        self.payload = payload

    def read(self, *_):
        return self.payload

