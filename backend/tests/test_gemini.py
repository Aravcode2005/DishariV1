import httpx
import pytest

from app.services.gemini import AIProviderError, GeminiProvider, MockGeminiProvider


KEY = "synthetic-unit-test-key"


def provider(handler):
    return GeminiProvider(KEY, "example-model", 2, transport=httpx.MockTransport(handler))


def test_mock_is_explicit():
    assert MockGeminiProvider().generate("synthetic").provider == "mock"


def test_gemini_wire_contract_with_mock_transport():
    def handler(request):
        assert request.headers["x-goog-api-key"] == KEY
        assert KEY not in str(request.url)
        assert request.url.path.endswith("/models/example-model:generateContent")
        assert request.extensions["timeout"]["read"] == 2
        return httpx.Response(200, json={"candidates": [{"finishReason": "STOP", "content": {"parts": [
            {"text": "internal", "thought": True}, {"text": "Synthetic response"}
        ]}}]})

    result = provider(handler).generate("synthetic")
    assert result.provider == "gemini"
    assert result.text == "Synthetic response"


@pytest.mark.parametrize("status,payload", [
    (429, {"error": KEY}), (500, {"error": "private"}),
    (200, {"candidates": []}), (200, {"candidates": [{"finishReason": "SAFETY"}]}),
    (200, {"candidates": [{"finishReason": "STOP", "content": {"parts": []}}]}),
])
def test_provider_errors_are_safe(status, payload):
    with pytest.raises(AIProviderError) as failure:
        provider(lambda request: httpx.Response(status, json=payload)).generate("synthetic")
    assert KEY not in str(failure.value)
    assert "private" not in str(failure.value)


def test_timeout_is_safe():
    def handler(request):
        raise httpx.ReadTimeout(KEY, request=request)

    with pytest.raises(AIProviderError, match="timed out") as failure:
        provider(handler).generate("synthetic")
    assert KEY not in str(failure.value)
