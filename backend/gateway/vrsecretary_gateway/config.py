# backend/gateway/vrsecretary_gateway/config.py

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration for the VRSecretary gateway.

    Values come from:
      1. Defaults below
      2. .env file (if present)
      3. Environment variables
    """

    # Pydantic v2 / pydantic-settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unknown env vars instead of failing
    )

    # ---- Mode / LLM selection ----
    # MODE=offline_local_ollama or MODE=online_watsonx (future)
    mode: str = Field("offline_local_ollama", env="MODE")

    # ---- Ollama (LLM) ----
    # OLLAMA_BASE_URL=http://localhost:11434
    ollama_base_url: str = Field("http://localhost:11434", env="OLLAMA_BASE_URL")
    # OLLAMA_MODEL=llama3
    ollama_model: str = Field("llama3", env="OLLAMA_MODEL")
    # OLLAMA_TIMEOUT=60.0
    ollama_timeout: float = Field(60.0, env="OLLAMA_TIMEOUT")

    # ---- Chatterbox TTS ----
    # CHATTERBOX_URL=http://localhost:4123
    chatterbox_url: str = Field("http://localhost:4123", env="CHATTERBOX_URL")
    # CHATTERBOX_TIMEOUT=30.0
    chatterbox_timeout: float = Field(30.0, env="CHATTERBOX_TIMEOUT")
    # CHATTERBOX_VOICE=female|male|neutral
    chatterbox_default_voice: str = Field("female", env="CHATTERBOX_VOICE")
    # CHATTERBOX_LANGUAGE=en  (default multilingual TTS language, ISO 639-1)
    chatterbox_default_language: str = Field("en", env="CHATTERBOX_LANGUAGE")

    # ---- watsonx.ai (future) ----
    watsonx_url: str | None = Field(None, env="WATSONX_URL")
    watsonx_project_id: str | None = Field(None, env="WATSONX_PROJECT_ID")
    watsonx_model_id: str | None = Field(None, env="WATSONX_MODEL_ID")
    watsonx_api_key: str | None = Field(None, env="WATSONX_API_KEY")

    # ---- Conversation history ----
    # SESSION_MAX_HISTORY=10
    session_max_history: int = Field(10, env="SESSION_MAX_HISTORY")


# This is what the rest of the gateway imports
settings = Settings()
