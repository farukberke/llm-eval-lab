from typing import Any

from llm_eval_lab.llm.base import LLMClient
from llm_eval_lab.llm.ollama_client import OllamaClient

_PROVIDERS: dict[str, type] = {
    "ollama": OllamaClient,
}


def get_llm_client(provider: str, **kwargs: Any) -> LLMClient:
    try:
        client_cls = _PROVIDERS[provider]
    except KeyError:
        raise ValueError(
            f"Unknown LLM provider: {provider!r}. Available: {sorted(_PROVIDERS)}"
        ) from None
    return client_cls(**kwargs)
