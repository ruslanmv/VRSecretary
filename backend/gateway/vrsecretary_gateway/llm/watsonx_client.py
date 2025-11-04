"""IBM watsonx.ai LLM client"""

import logging
from typing import List

from .base_client import BaseLLMClient
from ..models.chat_schemas import ChatMessage
from ..config import settings

logger = logging.getLogger(__name__)


class WatsonxClient(BaseLLMClient):
    """Client for IBM watsonx.ai text generation"""
    
    def __init__(self):
        try:
            from ibm_watsonx_ai import APIClient
            from ibm_watsonx_ai import Credentials
            from ibm_watsonx_ai.foundation_models import ModelInference
            
            # Validate configuration
            if not all([
                settings.watsonx_url,
                settings.watsonx_api_key,
                settings.watsonx_project_id,
                settings.watsonx_model_id,
            ]):
                raise ValueError(
                    "watsonx mode requires: WATSONX_URL, WATSONX_API_KEY, "
                    "WATSONX_PROJECT_ID, WATSONX_MODEL_ID"
                )
            
            # Initialize watsonx client
            credentials = Credentials(
                url=settings.watsonx_url,
                api_key=settings.watsonx_api_key,
            )
            
            self.client = APIClient(credentials)
            self.model = ModelInference(
                model_id=settings.watsonx_model_id,
                api_client=self.client,
                project_id=settings.watsonx_project_id,
            )
            
            logger.info(f"Initialized watsonx client with model: {settings.watsonx_model_id}")
        
        except ImportError:
            raise ImportError(
                "watsonx dependencies not installed. "
                "Run: pip install 'vrsecretary-gateway[watsonx]'"
            )
    
    async def generate(self, messages: List[ChatMessage]) -> str:
        """Generate response using watsonx.ai"""
        
        # Convert chat messages to prompt format
        # watsonx typically uses a single prompt string
        prompt_parts = []
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")
        
        prompt_parts.append("Assistant:")
        prompt = "

".join(prompt_parts)
        
        try:
            logger.debug(f"Calling watsonx.ai with prompt length: {len(prompt)}")
            
            # Generate using watsonx
            # Note: This is synchronous; wrap in asyncio if needed
            response = self.model.generate(
                prompt=prompt,
                params={
                    "max_new_tokens": 200,
                    "temperature": 0.7,
                    "top_p": 0.9,
                },
            )
            
            # Extract generated text
            generated_text = response["results"][0]["generated_text"].strip()
            
            return generated_text
        
        except Exception as e:
            logger.error(f"watsonx.ai error: {e}", exc_info=True)
            raise RuntimeError(f"watsonx.ai generation failed: {str(e)}")
