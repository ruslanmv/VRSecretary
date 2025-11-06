from typing import List

import httpx

from .base_client import BaseLLMClient
from ..models.chat_schemas import ChatMessage
from ..config import settings


class OllamaClient(BaseLLMClient):
    """
    Simple OpenAI-style chat completion client for Ollama.

    Assumes Ollama is running with an OpenAI-compatible API, e.g.:

        base_url = http://localhost:11434
        POST /v1/chat/completions

    and that `settings.ollama_model` is a valid model name (e.g. "llama3").
    """

    async def generate(self, messages: List[ChatMessage]) -> str:
        async with httpx.AsyncClient(
            base_url=settings.ollama_base_url.rstrip("/"),
            timeout=settings.ollama_timeout,
        ) as client:
            payload = {
                "model": settings.ollama_model,
                "messages": [m.model_dump() for m in messages],
                # You can add more sampling params here if desired
            }
            resp = await client.post("/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()

        # Expect standard OpenAI-style response
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected Ollama response shape: {data}") from exc
