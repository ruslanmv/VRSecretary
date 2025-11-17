"""
Configuration Management for VRSecretary Gateway.

This module provides centralized configuration management using Pydantic Settings.
Configuration values are loaded from:
    1. Default values defined in the Settings class
    2. Environment variables (highest priority)
    3. .env file (if present in the working directory)

The configuration supports multiple deployment modes:
    - offline_local_ollama: Local Ollama LLM with Chatterbox TTS
    - online_watsonx: IBM watsonx.ai cloud LLM with Chatterbox TTS

Author:
    Ruslan Magana (ruslanmv.com)

License:
    Apache-2.0

Example:
    Basic usage::

        from vrsecretary_gateway.config import settings

        print(f"Using LLM mode: {settings.mode}")
        print(f"Ollama URL: {settings.ollama_base_url}")
        print(f"Session max history: {settings.session_max_history}")

    Override via environment variables::

        $ export MODE=online_watsonx
        $ export WATSONX_API_KEY=your-key-here
        $ python -m vrsecretary_gateway.main

    Use .env file::

        # .env
        MODE=offline_local_ollama
        OLLAMA_MODEL=llama3
        CHATTERBOX_URL=http://localhost:4123

Attributes:
    settings (Settings): Global singleton instance of the Settings class,
        accessible throughout the application.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings for the VRSecretary Gateway.

    This class uses Pydantic Settings for automatic loading from environment
    variables and .env files. All settings have sensible defaults for development.

    Attributes:
        mode: Deployment mode selector (offline_local_ollama | online_watsonx).
        ollama_base_url: Base URL for Ollama API (default: http://localhost:11434).
        ollama_model: Ollama model name (e.g., llama3, mistral, granite).
        ollama_timeout: HTTP timeout for Ollama requests in seconds.
        ollama_temperature: LLM sampling temperature (0.0-1.0).
        ollama_max_tokens: Maximum tokens to generate per response.
        chatterbox_url: Base URL for Chatterbox TTS API.
        chatterbox_timeout: HTTP timeout for TTS requests in seconds.
        chatterbox_default_voice: Default voice profile (female|male|neutral).
        chatterbox_default_language: ISO 639-1 language code (e.g., en, es, fr).
        watsonx_url: watsonx.ai API base URL (required for online_watsonx mode).
        watsonx_project_id: watsonx.ai project ID.
        watsonx_model_id: watsonx.ai model identifier.
        watsonx_api_key: watsonx.ai API authentication key.
        watsonx_timeout: HTTP timeout for watsonx requests in seconds.
        watsonx_temperature: LLM sampling temperature for watsonx.
        watsonx_max_tokens: Maximum tokens for watsonx responses.
        session_max_history: Maximum conversation turns to retain per session.
        log_level: Logging level (DEBUG|INFO|WARNING|ERROR|CRITICAL).

    Raises:
        ValidationError: If required fields are missing or values are invalid.

    Example:
        >>> settings = Settings()
        >>> print(settings.mode)
        'offline_local_ollama'
        >>> print(settings.ollama_model)
        'llama3'
    """

    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown environment variables
        frozen=False,    # Allow runtime modification if needed
    )

    # ===========================================================================
    # Core Settings
    # ===========================================================================

    mode: Literal["offline_local_ollama", "online_watsonx"] = Field(
        default="offline_local_ollama",
        description=(
            "Deployment mode: 'offline_local_ollama' for local Ollama, "
            "'online_watsonx' for IBM watsonx.ai cloud."
        ),
    )

    # ===========================================================================
    # Ollama LLM Configuration
    # ===========================================================================

    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for the Ollama API server.",
        examples=["http://localhost:11434", "http://ollama:11434"],
    )

    ollama_model: str = Field(
        default="llama3",
        description="Ollama model name to use for chat completions.",
        examples=["llama3", "mistral", "granite", "qwen2.5:0.5b-instruct"],
    )

    ollama_timeout: float = Field(
        default=60.0,
        gt=0.0,
        le=300.0,
        description="HTTP timeout for Ollama requests (seconds).",
    )

    ollama_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for Ollama (0.0 = deterministic, 2.0 = very random).",
    )

    ollama_max_tokens: int = Field(
        default=256,
        gt=0,
        le=4096,
        description="Maximum number of tokens to generate per response.",
    )

    # ===========================================================================
    # Chatterbox TTS Configuration
    # ===========================================================================

    chatterbox_url: str = Field(
        default="http://localhost:4123",
        description="Base URL for the Chatterbox TTS API server.",
        examples=["http://localhost:4123", "http://tts:4123"],
    )

    chatterbox_timeout: float = Field(
        default=30.0,
        gt=0.0,
        le=120.0,
        description="HTTP timeout for Chatterbox TTS requests (seconds).",
    )

    chatterbox_default_voice: str = Field(
        default="female",
        description="Default voice profile for TTS synthesis.",
        examples=["female", "male", "neutral"],
    )

    chatterbox_default_language: str = Field(
        default="en",
        min_length=2,
        max_length=5,
        description="Default ISO 639-1 language code for TTS (e.g., en, es, fr, de, it).",
        examples=["en", "es", "fr", "de", "it", "ja", "zh"],
    )

    # ===========================================================================
    # IBM watsonx.ai Configuration (Cloud LLM)
    # ===========================================================================

    watsonx_url: Optional[str] = Field(
        default=None,
        description="IBM watsonx.ai API base URL (required if mode=online_watsonx).",
        examples=["https://us-south.ml.cloud.ibm.com", "https://eu-de.ml.cloud.ibm.com"],
    )

    watsonx_project_id: Optional[str] = Field(
        default=None,
        min_length=36,
        max_length=36,
        description="IBM watsonx.ai project ID (UUID format).",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    watsonx_model_id: Optional[str] = Field(
        default=None,
        description="watsonx.ai model identifier to use for chat completions.",
        examples=[
            "ibm/granite-13b-chat-v2",
            "meta-llama/llama-3-70b-instruct",
            "mistralai/mixtral-8x7b-instruct-v01",
        ],
    )

    watsonx_api_key: Optional[str] = Field(
        default=None,
        description="IBM Cloud API key for watsonx.ai authentication.",
    )

    watsonx_timeout: float = Field(
        default=60.0,
        gt=0.0,
        le=300.0,
        description="HTTP timeout for watsonx.ai requests (seconds).",
    )

    watsonx_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for watsonx.ai models.",
    )

    watsonx_max_tokens: int = Field(
        default=256,
        gt=0,
        le=4096,
        description="Maximum number of tokens to generate per watsonx response.",
    )

    # ===========================================================================
    # Session Management
    # ===========================================================================

    session_max_history: int = Field(
        default=10,
        ge=0,
        le=100,
        description=(
            "Maximum number of conversation turns (user+assistant pairs) "
            "to retain in session history. 0 = no history."
        ),
    )

    # ===========================================================================
    # Logging Configuration
    # ===========================================================================

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Application logging level.",
    )

    # ===========================================================================
    # Validators
    # ===========================================================================

    @field_validator("mode")
    @classmethod
    def validate_mode(
        cls,
        value: str,
    ) -> str:
        """
        Validate deployment mode and ensure it's a supported value.

        Args:
            value: The mode string to validate.

        Returns:
            The validated mode string.

        Raises:
            ValueError: If the mode is not supported.
        """
        valid_modes = {"offline_local_ollama", "online_watsonx"}
        if value not in valid_modes:
            msg = (
                f"Invalid mode '{value}'. "
                f"Must be one of: {', '.join(valid_modes)}"
            )
            raise ValueError(msg)
        return value

    @field_validator("chatterbox_default_language")
    @classmethod
    def validate_language_code(
        cls,
        value: str,
    ) -> str:
        """
        Validate ISO 639-1 language code format.

        Args:
            value: The language code to validate.

        Returns:
            The validated language code in lowercase.

        Note:
            This is a basic format check, not an exhaustive list of valid codes.
        """
        return value.lower()

    def model_post_init(self, __context: object) -> None:
        """
        Post-initialization validation to check mode-specific requirements.

        Raises:
            ValueError: If required fields for the selected mode are missing.

        Note:
            This runs after all fields have been set and validated.
        """
        # Validate watsonx requirements if in online mode
        if self.mode == "online_watsonx":
            required_fields = {
                "watsonx_url": self.watsonx_url,
                "watsonx_project_id": self.watsonx_project_id,
                "watsonx_model_id": self.watsonx_model_id,
                "watsonx_api_key": self.watsonx_api_key,
            }

            missing = [
                name for name, value in required_fields.items()
                if value is None
            ]

            if missing:
                msg = (
                    f"MODE=online_watsonx requires the following environment variables: "
                    f"{', '.join(missing).upper()}"
                )
                raise ValueError(msg)


# ==============================================================================
# Global Settings Instance
# ==============================================================================

# This is the singleton instance used throughout the application
settings = Settings()
