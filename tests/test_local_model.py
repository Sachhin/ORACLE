"""Tests for the local-only model runtime boundary."""
import json
import unittest
from unittest.mock import patch

from oracle.local_model import LocalModelClient, LocalModelConfig, LocalModelError


class LocalModelTests(unittest.TestCase):
    def test_default_endpoint_is_loopback(self):
        self.assertEqual(LocalModelClient().completion_url, "http://127.0.0.1:8080/v1/chat/completions")

    def test_rejects_non_loopback_endpoint(self):
        with self.assertRaises(ValueError):
            LocalModelConfig(base_url="https://example.com")

    def test_rejects_invalid_generation_limits(self):
        with self.assertRaises(ValueError):
            LocalModelConfig(max_tokens=0)

    def test_generate_sends_chat_messages_without_credentials(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self):
                return json.dumps({"choices": [{"message": {"content": "Reasoned result"}}]}).encode()
        with patch("oracle.local_model.urlopen", return_value=Response()) as mocked:
            result = LocalModelClient().generate("You are an auditor.", "Check claim X.")
        self.assertEqual(result, "Reasoned result")
        request = mocked.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/v1/chat/completions")
        self.assertNotIn("Authorization", request.headers)
        self.assertEqual(json.loads(request.data.decode())["messages"][1]["content"], "Check claim X.")

    def test_empty_prompt_rejected(self):
        with self.assertRaises(ValueError):
            LocalModelClient().generate(" ", "question")

    def test_invalid_response_rejected(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"choices": []}'
        with patch("oracle.local_model.urlopen", return_value=Response()):
            with self.assertRaises(LocalModelError):
                LocalModelClient().generate("system", "question")


if __name__ == "__main__":
    unittest.main()
