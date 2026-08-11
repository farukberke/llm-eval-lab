import json

import httpx
import pytest

from llm_eval_lab.config import settings
from llm_eval_lab.llm.ollama_client import OllamaClient


def _mock_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_generate_parses_ollama_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/generate"
        payload = json.loads(request.read())
        assert payload == {"model": "qwen2.5:7b", "prompt": "Hi", "stream": False}
        return httpx.Response(
            200,
            json={
                "response": "Hello there",
                "prompt_eval_count": 5,
                "eval_count": 3,
                "done": True,
            },
        )

    client = OllamaClient(host="http://localhost:11434", http_client=_mock_client(handler))
    result = client.generate(model="qwen2.5:7b", prompt="Hi")

    assert result.text == "Hello there"
    assert result.prompt_tokens == 5
    assert result.completion_tokens == 3
    assert result.latency_ms >= 0
    assert result.raw["done"] is True


def test_generate_includes_parameters_as_options():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.read())
        return httpx.Response(200, json={"response": "ok"})

    client = OllamaClient(host="http://localhost:11434", http_client=_mock_client(handler))
    client.generate(model="m", prompt="p", parameters={"temperature": 0.2})

    assert captured["payload"]["options"] == {"temperature": 0.2}


def test_generate_raises_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model not found"})

    client = OllamaClient(host="http://localhost:11434", http_client=_mock_client(handler))

    with pytest.raises(httpx.HTTPStatusError):
        client.generate(model="does-not-exist", prompt="Hi")


@pytest.mark.integration
def test_generate_against_real_ollama():
    client = OllamaClient(host=settings.ollama_host)
    result = client.generate(
        model=settings.ollama_default_model, prompt="Reply with the single word: pong"
    )

    assert result.text
    assert result.latency_ms > 0
