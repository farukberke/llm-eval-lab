import time
from typing import Any

import httpx

from llm_eval_lab.llm.base import LLMResponse

# Generous timeout: a model that isn't already loaded into memory can take
# a while to spin up on the first call.
DEFAULT_TIMEOUT_SECONDS = 120.0


class OllamaClient:
    def __init__(
        self,
        host: str,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        http_client: httpx.Client | None = None,
    ):
        self._host = host.rstrip("/")
        self._http_client = http_client or httpx.Client(timeout=timeout)

    def generate(
        self,
        model: str,
        prompt: str,
        parameters: dict[str, Any] | None = None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {"model": model, "prompt": prompt, "stream": False}
        if parameters:
            payload["options"] = parameters

        start = time.perf_counter()
        response = self._http_client.post(f"{self._host}/api/generate", json=payload)
        latency_ms = (time.perf_counter() - start) * 1000
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            text=data["response"],
            latency_ms=latency_ms,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
            raw=data,
        )
