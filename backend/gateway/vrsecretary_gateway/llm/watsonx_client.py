# backend/gateway/vrsecretary_gateway/llm/watsonx_client.py
"""
Chatterbox TTS client for VRSecretary.

Talks to the optimized (multilingual) TTS server.

- Uses POST /v1/audio/speech
- Forces non-streaming mode (stream = False)
- Returns one full WAV (bytes or base64)
"""

from __future__ import annotations

import base64
import logging
from typing import Literal

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

VoiceType = Literal["female", "male", "neutral"]


class ChatterboxTtsError(RuntimeError):
    """Raised when the Chatterbox TTS server fails or returns an error."""
    pass


def _build_payload(
    text: str,
    voice: VoiceType,
    temperature: float,
    cfg_weight: float,
    exaggeration: float,
    speed: float,
    language: str,
) -> dict:
    """
    Build the JSON payload for the Chatterbox TTS server.

    `language` is the ISO 639-1 language code expected by the multilingual
    TTS backend (e.g. "en", "it", "fr", "de", ...).
    """
    if not text or not text.strip():
        raise ValueError("Chatterbox TTS text must be non-empty")

    return {
        "input": text,
        "language": language,
        "voice": voice,
        "temperature": float(temperature),
        "cfg_weight": float(cfg_weight),
        "exaggeration": float(exaggeration),
        "speed": float(speed),

        # IMPORTANT: force non-streaming + no chunking
        "stream": False,
        "chunk_by_sentences": False,
        "max_chunk_words": None,
        "max_chunk_sentences": None,
    }


async def tts_wav_bytes_async(
    text: str,
    *,
    voice: VoiceType | None = None,
    language: str | None = None,
    temperature: float = 0.7,
    cfg_weight: float = 0.4,
    exaggeration: float = 0.3,
    speed: float = 1.0,
    timeout: float | None = None,
) -> bytes:
    """
    Synthesize text into a single WAV (bytes) asynchronously.

    Parameters
    ----------
    text:
        Text to synthesize (must be non-empty).
    voice:
        Optional override for the voice ("female", "male", "neutral").
        If omitted, `settings.chatterbox_default_voice` is used.
    language:
        Optional ISO 639-1 language code (e.g. "en", "it", "fr").
        If omitted, `settings.chatterbox_default_language` is used.
    """
    effective_voice: VoiceType = voice or settings.chatterbox_default_voice  # type: ignore[assignment]
    effective_language: str = language or settings.chatterbox_default_language
    effective_timeout: float = timeout if timeout is not None else settings.chatterbox_timeout

    payload = _build_payload(
        text=text,
        voice=effective_voice,
        temperature=temperature,
        cfg_weight=cfg_weight,
        exaggeration=exaggeration,
        speed=speed,
        language=effective_language,
    )

    base_url = settings.chatterbox_url.rstrip("/")
    logger.debug("Calling Chatterbox TTS at %s/v1/audio/speech (lang=%s)", base_url, effective_language)

    async with httpx.AsyncClient(base_url=base_url, timeout=effective_timeout) as client:
        try:
            resp = await client.post("/v1/audio/speech", json=payload)
        except httpx.HTTPError as exc:
            raise ChatterboxTtsError(
                f"Error calling Chatterbox at {base_url}/v1/audio/speech: {exc}"
            ) from exc

    if resp.status_code >= 400:
        detail = None
        try:
            data = resp.json()
            detail = data.get("detail") or data.get("error")
        except Exception:
            pass

        msg = f"Chatterbox HTTP {resp.status_code}"
        if detail:
            msg += f": {detail}"
        else:
            msg += f": {resp.text}"
        raise ChatterboxTtsError(msg)

    wav_bytes = resp.content
    if not wav_bytes:
        raise ChatterboxTtsError("Chatterbox returned empty audio content")

    return wav_bytes


async def tts_wav_base64_async(
    text: str,
    *,
    voice: VoiceType | None = None,
    language: str | None = None,
    temperature: float = 0.7,
    cfg_weight: float = 0.4,
    exaggeration: float = 0.3,
    speed: float = 1.0,
    timeout: float | None = None,
) -> str:
    """
    Synthesize text to WAV and return base64-encoded WAV string.
    Suitable for returning to Unreal as `audio_wav_base64`.

    `language` behaves the same as in `tts_wav_bytes_async`:
    - if provided, that language is used;
    - otherwise, the gateway default (`settings.chatterbox_default_language`) is used.
    """
    wav = await tts_wav_bytes_async(
        text=text,
        voice=voice,
        language=language,
        temperature=temperature,
        cfg_weight=cfg_weight,
        exaggeration=exaggeration,
        speed=speed,
        timeout=timeout,
    )
    return base64.b64encode(wav).decode("ascii")


async def chatterbox_health_async(timeout: float | None = None) -> dict:
    """
    Call the /health endpoint of the Chatterbox server.
    """
    effective_timeout: float = timeout if timeout is not None else settings.chatterbox_timeout
    base_url = settings.chatterbox_url.rstrip("/")

    async with httpx.AsyncClient(base_url=base_url, timeout=effective_timeout) as client:
        try:
            resp = await client.get("/health")
        except httpx.HTTPError as exc:
            raise ChatterboxTtsError(f"Error calling Chatterbox /health: {exc}") from exc

    if resp.status_code >= 400:
        raise ChatterboxTtsError(f"Chatterbox /health HTTP {resp.status_code}: {resp.text}")

    try:
        return resp.json()
    except Exception as exc:
        raise ChatterboxTtsError(f"Failed to parse Chatterbox /health response: {exc}") from exc
