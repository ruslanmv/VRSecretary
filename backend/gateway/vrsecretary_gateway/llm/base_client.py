from abc import ABC, abstractmethod
from typing import List
from ..models.chat_schemas import ChatMessage
from ..config import settings

class BaseLLMClient(ABC):
    @abstractmethod
    async def generate(self, messages: List[ChatMessage]) -> str:
        ...

from .ollama_client import OllamaClient
# from .watsonx_client import WatsonxClient  # stub for future

def get_llm_client() -> BaseLLMClient:
    if settings.mode == "offline_local_ollama":
        return OllamaClient()
    # elif settings.mode == "online_watsonx":
    #     return WatsonxClient()
    else:
        return OllamaClient()
