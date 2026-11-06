"""HTTP contract tests for the real Gemini JSON provider.

These tests exercise request construction, bounded retries, quota handling,
and response validation without requiring a live API key or network access.
"""
import io
import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from oracle.model_agents import GeminiAgentError, GeminiJSONProvider


def response(payload):
    raw = json.dumps(payload).encode("utf-8")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit=-1):
            return raw[:limit]

    return FakeResponse()


def http_error(status, detail, headers=None):
    return HTTPError(
        "https://generativelanguage.googleapis.com/test",
        status,
        "provider error",
        headers or {},
        io.BytesIO(detail.encode("utf-8")),
    )


class GeminiJSONProviderTests(unittest.TestCase):
    def setUp(self):
        self.provider = GeminiJSONProvider(
            api_key="test-secret-key", model="gemini-2.5-flash",
            timeout=3, max_retries=2,
        )

    @patch("oracle.model_agents.urlopen")
    def test_success_sends_key_in_header_and_parses_json_object(self, urlopen):
        urlopen.return_value = response({
            "candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}],
        })

        result = self.provider.generate_json("Return JSON.")

        self.assertEqual(result, {"ok": True})
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("X-goog-api-key"), "test-secret-key")
        self.assertNotIn("test-secret-key", request.full_url)
        self.assertEqual(json.loads(request.data)["generationConfig"]["responseMimeType"],
                         "application/json")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 3)

    @patch("oracle.model_agents.time.sleep")
    @patch("oracle.model_agents.urlopen")
    def test_transient_server_error_retries_then_succeeds(self, urlopen, sleep):
        urlopen.side_effect = [
            http_error(503, "temporarily unavailable", {"Retry-After": "0"}),
            response({"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]}),
        ]

        self.assertEqual(self.provider.generate_json("prompt"), {"ok": True})
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(0.0)

    @patch("oracle.model_agents.time.sleep")
    @patch("oracle.model_agents.urlopen")
    def test_explicit_quota_exhaustion_stops_without_retry(self, urlopen, sleep):
        urlopen.side_effect = http_error(
            429, '{"error":{"status":"RESOURCE_EXHAUSTED","message":"quota exceeded"}}'
        )

        with self.assertRaisesRegex(GeminiAgentError, "quota appears exhausted"):
            self.provider.generate_json("prompt")

        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()

    @patch("oracle.model_agents.time.sleep")
    @patch("oracle.model_agents.urlopen")
    def test_non_quota_rate_limit_uses_bounded_retry(self, urlopen, sleep):
        urlopen.side_effect = [
            http_error(429, '{"error":{"message":"rate limit; retry later"}}',
                       {"Retry-After": "0"}),
            response({"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]}),
        ]

        self.assertEqual(self.provider.generate_json("prompt"), {"ok": True})
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(0.0)

    @patch("oracle.model_agents.time.sleep")
    @patch("oracle.model_agents.urlopen")
    def test_authentication_error_is_not_retried(self, urlopen, sleep):
        urlopen.side_effect = http_error(401, '{"error":{"message":"invalid API key"}}')

        with self.assertRaisesRegex(GeminiAgentError, "Gemini HTTP 401"):
            self.provider.generate_json("prompt")

        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()

    @patch("oracle.model_agents.urlopen")
    def test_malformed_provider_response_is_reported(self, urlopen):
        urlopen.return_value = response({"candidates": []})

        with self.assertRaisesRegex(GeminiAgentError, "no valid JSON candidate"):
            self.provider.generate_json("prompt")

    @patch("oracle.model_agents.urlopen")
    def test_non_object_model_json_is_rejected(self, urlopen):
        urlopen.return_value = response({
            "candidates": [{"content": {"parts": [{"text": '["not", "an", "object"]'}]}}],
        })

        with self.assertRaisesRegex(GeminiAgentError, "must be a JSON object"):
            self.provider.generate_json("prompt")

    def test_provider_rejects_invalid_timeout_and_retry_budget(self):
        with self.assertRaisesRegex(ValueError, "timeout must be positive"):
            GeminiJSONProvider(api_key="x", timeout=0)
        with self.assertRaisesRegex(ValueError, "max_retries"):
            GeminiJSONProvider(api_key="x", max_retries=4)


if __name__ == "__main__":
    unittest.main()
