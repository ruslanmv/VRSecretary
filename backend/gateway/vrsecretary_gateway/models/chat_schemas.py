"""
Data Models for VRSecretary Chat API.

This module defines Pydantic models used for request/response validation
and serialization in the VRSecretary gateway. All models use Pydantic v2
for runtime validation, JSON schema generation, and OpenAPI documentation.

The models support:
    - VR chat requests from Unreal Engine / Unity clients
    - AI assistant responses with text and audio
    - Internal LLM message representation (OpenAI-compatible)

Author:
    Ruslan Magana (ruslanmv.com)

License:
    Apache-2.0

Example:
    Creating a chat request::

        from vrsecretary_gateway.models.chat_schemas import VRChatRequest

        request = VRChatRequest(
            session_id="user-123-session-1",
            user_text="Hello Ailey, how are you?",
            language="en"
        )

    Parsing a response::

        from vrsecretary_gateway.models.chat_schemas import VRChatResponse

        response = VRChatResponse(
            assistant_text="Hello! I'm doing well, thank you for asking.",
            audio_wav_base64="UklGRiQAAABXQVZF..."
        )
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class VRChatRequest(BaseModel):
    """
    Request model for the /api/vr_chat endpoint.

    Sent by VR clients (Unreal Engine, Unity, etc.) to initiate a conversation
    turn with the AI assistant. The gateway uses this to:
        1. Retrieve conversation history for the session
        2. Generate LLM response
        3. Synthesize TTS audio
        4. Return combined text + audio response

    Attributes:
        session_id: Unique identifier for the conversation session.
            Can be a GUID, user ID, or any stable string. Used for
            tracking conversation history.
        user_text: User's message text to send to the AI assistant.
            This is both sent to the LLM and can be used for TTS.
        language: Optional ISO 639-1 language code for TTS synthesis.
            If omitted, uses the gateway's default language (typically "en").
            Examples: "en", "es", "fr", "de", "it", "ja", "zh"

    Example:
        >>> request = VRChatRequest(
        ...     session_id="550e8400-e29b-41d4-a716-446655440000",
        ...     user_text="What's the weather like today?",
        ...     language="en"
        ... )
        >>> print(request.model_dump_json())
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "user_text": "What's the weather like today?",
            "language": "en"
        }
    """

    session_id: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description=(
            "Session identifier (GUID or any stable string) used to group "
            "conversation turns and maintain history."
        ),
        examples=[
            "550e8400-e29b-41d4-a716-446655440000",
            "user-123-session-1",
            "unreal-client-42",
        ],
    )

    user_text: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description=(
            "User's message text. Sent to the LLM for chat completion "
            "and optionally used for TTS synthesis."
        ),
        examples=[
            "Hello Ailey, can you help me plan my day?",
            "What's the status of my project?",
            "Set a reminder for tomorrow at 9 AM",
        ],
    )

    language: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=5,
        description=(
            "Optional TTS language code (ISO 639-1, e.g. 'en', 'es', 'fr'). "
            "If omitted, the gateway's default TTS language is used."
        ),
        examples=["en", "es", "fr", "de", "it", "ja", "zh", "pt", "ru"],
    )

    @field_validator("language")
    @classmethod
    def normalize_language_code(cls, value: Optional[str]) -> Optional[str]:
        """
        Normalize language code to lowercase.

        Args:
            value: The language code to normalize.

        Returns:
            Lowercase language code, or None if not provided.
        """
        return value.lower() if value else None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "user_text": "Hello Ailey, introduce yourself.",
                    "language": "en",
                },
                {
                    "session_id": "user-456",
                    "user_text": "Qual è la capitale d'Italia?",
                    "language": "it",
                },
            ]
        }
    }


class VRChatResponse(BaseModel):
    """
    Response model for the /api/vr_chat endpoint.

    Returned by the gateway after processing a VRChatRequest. Contains both
    text and audio representations of the AI assistant's response, allowing
    VR clients to display subtitles and play spatial audio simultaneously.

    Attributes:
        assistant_text: AI assistant's response as plain text.
            Can be displayed as subtitles in VR, logged, or used for
            other text-based features.
        audio_wav_base64: Base64-encoded WAV audio file of the assistant's
            response synthesized via TTS. Clients should decode this to
            binary and play as spatial audio in the VR environment.

    Example:
        >>> response = VRChatResponse(
        ...     assistant_text="Hello! I'm Ailey, your VR secretary.",
        ...     audio_wav_base64="UklGRiQAAABXQVZF..."
        ... )
        >>> print(len(response.audio_wav_base64))  # Base64 length
        20
    """

    assistant_text: str = Field(
        ...,
        min_length=1,
        max_length=8192,
        description=(
            "AI assistant's reply as plain text. Use for subtitles, "
            "logging, or text-based UI elements."
        ),
        examples=[
            "Hello! I'm Ailey, your VR secretary. How can I assist you today?",
            "I've scheduled your meeting for tomorrow at 2 PM.",
            "The weather forecast shows sunny skies with a high of 75°F.",
        ],
    )

    audio_wav_base64: str = Field(
        default="",
        description=(
            "Base64-encoded WAV audio for TTS playback in VR. "
            "Decode to binary and play as spatial audio. "
            "Empty string if TTS fails or is disabled."
        ),
        examples=["UklGRiQAAABXQVZF...", ""],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "assistant_text": "Hello! I'm Ailey, your VR secretary.",
                    "audio_wav_base64": "UklGRiQAAABXQVZF...",
                },
                {
                    "assistant_text": "I've set a reminder for you.",
                    "audio_wav_base64": "",  # TTS unavailable
                },
            ]
        }
    }


class ChatMessage(BaseModel):
    """
    Internal representation of chat messages for LLM APIs.

    Compatible with OpenAI-style chat completions and used throughout the
    gateway for conversation history management. This model follows the
    standard role/content structure supported by most modern LLM APIs
    (OpenAI, Ollama, watsonx.ai, etc.).

    Attributes:
        role: Message role indicating the source of the message.
            - "system": Initial instructions/context for the AI
            - "user": Messages from the human user
            - "assistant": Responses from the AI assistant
        content: The actual message text.

    Example:
        >>> messages = [
        ...     ChatMessage(role="system", content="You are a helpful assistant."),
        ...     ChatMessage(role="user", content="What is 2+2?"),
        ...     ChatMessage(role="assistant", content="2+2 equals 4."),
        ... ]
        >>> for msg in messages:
        ...     print(f"{msg.role}: {msg.content}")
        system: You are a helpful assistant.
        user: What is 2+2?
        assistant: 2+2 equals 4.
    """

    role: Literal["system", "user", "assistant"] = Field(
        ...,
        description=(
            'Role of the message sender:\n'
            '- "system": Initial instructions/context for the AI\n'
            '- "user": Messages from the human user\n'
            '- "assistant": Responses from the AI assistant'
        ),
    )

    content: str = Field(
        ...,
        min_length=1,
        max_length=16384,
        description="Message content as plain text.",
        examples=[
            "You are Ailey, a professional VR secretary.",
            "What's on my schedule today?",
            "You have three meetings scheduled for today.",
        ],
    )

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, value: str) -> str:
        """
        Ensure content is not just whitespace.

        Args:
            value: The content string to validate.

        Returns:
            The validated content string.

        Raises:
            ValueError: If content is empty or only whitespace.
        """
        if not value.strip():
            msg = "Message content cannot be empty or only whitespace"
            raise ValueError(msg)
        return value

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "role": "system",
                    "content": "You are Ailey, a professional VR secretary.",
                },
                {
                    "role": "user",
                    "content": "What's the weather today?",
                },
                {
                    "role": "assistant",
                    "content": "The weather is sunny with a high of 75°F.",
                },
            ]
        }
    }
