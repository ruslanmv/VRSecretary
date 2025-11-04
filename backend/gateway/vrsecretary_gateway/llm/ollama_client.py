from typing import List
import httpx
from .base_client import BaseLLMClient
from ..models.chat_schemas import ChatMessage
from ..config import settings

class OllamaClient(BaseLLMClient):
    async def generate(self, messages: List[ChatMessage]) -> str:
        async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=60.0) as client:
            payload = {
                "model": settings.ollama_model,
                "messages": [m.model_dump() for m in messages],
            }
            resp = await client.post("/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
