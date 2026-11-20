"""Text-only AI adapter. AI output never supplies deterministic rule criteria."""
from typing import Protocol

import httpx

from app.core.config import Settings
from app.schemas.workflows import AIResult


class AIProviderError(Exception):
    """Sanitized provider failure, without credentials or raw response bodies."""


class AIProvider(Protocol):
    def generate(self, prompt: str) -> AIResult: ...


class MockGeminiProvider:
    def generate(self, prompt: str) -> AIResult:
        return AIResult(provider="mock", text="MOCK: Synthetic offline AI response; no Gemini request was made.")


class GeminiProvider:
    def __init__(self, api_key: str, model: str, timeout: float,
                 transport: httpx.BaseTransport | None = None) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._transport = transport

    def generate(self, prompt: str) -> AIResult:
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport, trust_env=False,
                              follow_redirects=False) as client:
                response = client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent",
                    headers={"x-goog-api-key": self._api_key},
                    json={"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                          "generationConfig": {"maxOutputTokens": 1024}},
                )
                response.raise_for_status()
                payload = response.json()
                candidate = payload["candidates"][0]
                if candidate.get("finishReason") not in {"STOP", "MAX_TOKENS"}:
                    raise AIProviderError("AI provider did not return usable text")
                text = "\n".join(part["text"] for part in candidate["content"]["parts"]
                                 if isinstance(part.get("text"), str) and not part.get("thought"))
                if not text.strip():
                    raise AIProviderError("AI provider did not return usable text")
                return AIResult(provider="gemini", text=text)
        except httpx.TimeoutException:
            raise AIProviderError("AI provider timed out") from None
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise AIProviderError("AI provider request failed") from None


def create_ai_provider(settings: Settings) -> AIProvider:
    if settings.ai_provider == "mock":
        return MockGeminiProvider()
    assert settings.gemini_api_key is not None
    return GeminiProvider(settings.gemini_api_key.get_secret_value(), settings.gemini_model,
                          settings.gemini_timeout_seconds)
