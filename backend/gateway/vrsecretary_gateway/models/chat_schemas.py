# backend/gateway/vrsecretary_gateway/models/chat_schemas.py

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class VRChatRequest(BaseModel):
    """
    Request from Unreal’s VRSecretaryComponent (Gateway mode).

    The plugin typically sends:

        {
          "session_id": "<GUID or any string>",
          "user_text": "Hello Ailey, ..."
        }

    Optionally, to control the TTS language (when using a multilingual TTS
    backend), the client may also send:

        "language": "en"  // ISO 639-1 code, e.g. "en", "it", "fr", ...
    """

    session_id: str = Field(
        ...,
        description="Session identifier (GUID or any stable string used to group turns).",
        examples=["550e8400-e29b-41d4-a716-446655440000", "user-123-session-1"],
    )
    user_text: str = Field(
        ...,
        description="User's message text. Sent to the LLM and used for TTS.",
        examples=["Hello Ailey, can you help me plan my day?"],
    )
    language: Optional[str] = Field(
        None,
        description=(
            "Optional TTS language code (ISO 639-1, e.g. 'en', 'it', 'fr'). "
            "If omitted, the gateway's default TTS language is used."
        ),
        examples=["en", "it", "fr"],
    )


class VRChatResponse(BaseModel):
    """
    Response consumed by the Unreal plugin.

    - assistant_text: AI text reply (for subtitles, logs, etc.)
    - audio_wav_base64: base64-encoded WAV (for TTS playback)
    """

    assistant_text: str = Field(
        ...,
        description="Assistant's reply as plain text.",
    )
    audio_wav_base64: str = Field(
        ...,
        description="Base64-encoded WAV audio for TTS playback in Unreal.",
    )


class ChatMessage(BaseModel):
    """
    Internal representation of chat messages used by LLMs.

    Compatible with OpenAI-style chat completions.
    """

    role: Literal["system", "user", "assistant"] = Field(
        ...,
        description='Role of the message: "system", "user", or "assistant".',
    )
    content: str = Field(
        ...,
        description="Message content as plain text.",
    )
