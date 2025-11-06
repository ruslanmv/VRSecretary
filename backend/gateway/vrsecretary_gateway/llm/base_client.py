# backend/gateway/vrsecretary_gateway/llm/base_client.py

from abc import ABC, abstractmethod
from typing import List

from ..models.chat_schemas import ChatMessage
from ..config import settings


class BaseLLMClient(ABC):
    """Abstract LLM client interface."""

    @abstractmethod
    async def generate(self, messages: List[ChatMessage]) -> str:
        """
        Generate a chat completion for the given messages.

        messages: list of ChatMessage (system, user, assistant)
        returns: assistant's reply (string)
        """
        ...


# Import concrete clients here (after BaseLLMClient is defined)
from .ollama_client import OllamaClient  # noqa: E402


def get_llm_client() -> BaseLLMClient:
    """
    Factory that picks the appropriate LLM backend.

    For now:
      - offline_local_ollama  -> OllamaClient
      - anything else         -> OllamaClient (default)
    """
    if settings.mode == "offline_local_ollama":
        return OllamaClient()
    # elif settings.mode == "online_watsonx":
    #     return WatsonxClient()
    return OllamaClient()
