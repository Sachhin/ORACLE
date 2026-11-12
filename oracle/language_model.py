"""Optional bridge to a user-controlled open-weight model server.

This is not a hosted-model provider and never selects a vendor endpoint. The
operator must explicitly configure a self-hosted OpenAI-compatible server.
The scientific core remains usable when this bridge is disabled or offline.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LanguageModelError(RuntimeError):
    """Raised when the configured self-hosted model cannot complete a request."""


@dataclass(frozen=True)
class SelfHostedModelConfig:
    base_url: str
    model: str
    timeout_seconds: float = 60.0
    max_tokens: int = 2048

    def __post_init__(self) -> None:
        url = self.base_url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("base_url must be an explicit http(s) URL for your own model server.")
        if not self.model.strip():
            raise ValueError("model must not be empty.")
        if not 1 <= self.timeout_seconds <= 600:
            raise ValueError("timeout_seconds must be between 1 and 600.")
        if not 1 <= self.max_tokens <= 32768:
            raise ValueError("max_tokens must be between 1 and 32768.")


class SelfHostedLanguageModel:
    """Minimal provider-neutral client for an operator-owned inference server.

    Supported servers include llama.cpp, Ollama's OpenAI-compatible endpoint,
    and vLLM. No API key, vendor SDK, or model-provider fallback is used.
    """

    def __init__(self, config: SelfHostedModelConfig) -> None:
        self.config = config

    def generate(self, messages: list[dict[str, str]], temperature: float = 0.2,
                 response_format: dict[str, Any] | None = None) -> str:
        if not messages:
            raise ValueError("messages must contain at least one message.")
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("temperature must be between 0 and 2.")
        for message in messages:
            if set(message) != {"role", "content"}:
                raise ValueError("Each message must contain only role and content.")
            if message["role"] not in {"system", "user", "assistant"}:
                raise ValueError("Unsupported message role.")
            if not isinstance(message["content"], str):
                raise ValueError("Message content must be text.")

        base = self.config.base_url.rstrip("/")
        url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self.config.max_tokens,
        }
        if response_format is not None:
            if not isinstance(response_format, dict) or response_format.get("type") != "json_object":
                raise ValueError("response_format must be a supported JSON-object format.")
            payload["response_format"] = response_format
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            # Preserve the local server's diagnostic response (e.g. context overflow)
            # so failed inference can be debugged without exposing credentials.
            try:
                body = exc.read().decode("utf-8", errors="replace")[:2000]
            except OSError:
                body = ""
            detail = f"HTTP {exc.code}: {exc.reason}"
            if body:
                detail += f"; server response: {body}"
            raise LanguageModelError(
                "Self-hosted model request failed; scientific core remains available. "
                f"Details: {detail}"
            ) from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise LanguageModelError(
                "Self-hosted model request failed; scientific core remains available. "
                f"Details: {exc}"
            ) from exc

        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LanguageModelError("Model server returned an unexpected chat-completion response.") from exc
        if not isinstance(content, str) or not content.strip():
            raise LanguageModelError("Model server returned empty content.")
        return content.strip()
