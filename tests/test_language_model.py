"""Tests for the optional self-hosted language-model bridge."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from oracle.language_model import (
    LanguageModelError,
    SelfHostedLanguageModel,
    SelfHostedModelConfig,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class SelfHostedModelTests(unittest.TestCase):
    def test_config_requires_explicit_http_endpoint_and_model(self):
        with self.assertRaises(ValueError):
            SelfHostedModelConfig("vendor-cloud-default", "model")
        with self.assertRaises(ValueError):
            SelfHostedModelConfig("http://127.0.0.1:8080/v1", "")

    @patch("oracle.language_model.urlopen")
    def test_posts_to_explicit_server_without_authorization_header(self, mock_urlopen):
        mock_urlopen.return_value = FakeResponse({
            "choices": [{"message": {"content": "Reasoned response"}}]
        })
        client = SelfHostedLanguageModel(
            SelfHostedModelConfig("http://127.0.0.1:8080/v1", "open-model")
        )
        answer = client.generate([{"role": "user", "content": "Explain this evidence."}])
        self.assertEqual(answer, "Reasoned response")
        request = mock_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/v1/chat/completions")
        self.assertIsNone(request.get_header("Authorization"))

    @patch("oracle.language_model.urlopen")
    def test_server_failure_is_explicit(self, mock_urlopen):
        mock_urlopen.side_effect = OSError("offline")
        client = SelfHostedLanguageModel(
            SelfHostedModelConfig("http://127.0.0.1:8080/v1", "open-model")
        )
        with self.assertRaises(LanguageModelError):
            client.generate([{"role": "user", "content": "Hello"}])

    def test_invalid_message_is_rejected_before_network(self):
        client = SelfHostedLanguageModel(
            SelfHostedModelConfig("http://127.0.0.1:8080/v1", "open-model")
        )
        with self.assertRaises(ValueError):
            client.generate([{"role": "system", "content": "x", "api_key": "bad"}])


if __name__ == "__main__":
    unittest.main()
