"""Local-only model client for an on-device ORACLE reasoning engine.

The client talks only to a loopback inference server such as llama.cpp server.
There is no hosted-provider integration, API-key handling, or external network
fallback. Scientific validation remains the responsibility of deterministic
tools and the evidence auditor.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class LocalModelError(RuntimeError):
    """Raised when the local inference runtime is unavailable or invalid."""


@dataclass(frozen=True)
class LocalModelConfig:
    base_url: str = "http://127.0.0.1:8080"
    timeout_seconds: float = 120.0
    max_tokens: int = 512
    temperature: float = 0.2

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Local model endpoint must use HTTP loopback only.")
        if not 1 <= self.timeout_seconds <= 900:
            raise ValueError("timeout_seconds must be between 1 and 900.")
        if not 1 <= self.max_tokens <= 8192:
            raise ValueError("max_tokens must be between 1 and 8192.")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0 and 2.")


class LocalModelClient:
    """Small dependency-free client for a local llama.cpp-compatible server."""

    def __init__(self, config: LocalModelConfig | None = None) -> None:
        self.config = config or LocalModelConfig()

    @property
    def completion_url(self) -> str:
        return self.config.base_url.rstrip("/") + "/v1/chat/completions"

    def is_ready(self) -> bool:
        request = Request(self.config.base_url.rstrip("/") + "/health", method="GET")
        try:
            with urlopen(request, timeout=min(self.config.timeout_seconds, 5)) as response:
                return 200 <= response.status < 300
        except (HTTPError, URLError, TimeoutError, OSError):
            return False

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not system_prompt.strip() or not user_prompt.strip():
            raise ValueError("System and user prompts must not be empty.")
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False,
        }
        request = Request(
            self.completion_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise LocalModelError(
                "Local model inference failed; check that the on-device runtime is running."
            ) from exc
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LocalModelError("Local model returned an invalid completion response.") from exc
        if not isinstance(content, str) or not content.strip():
            raise LocalModelError("Local model returned an empty response.")
        return content.strip()
