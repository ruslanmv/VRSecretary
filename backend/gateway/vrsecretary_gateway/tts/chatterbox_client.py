# backend/gateway/vrsecretary_gateway/tts/chatterbox_client.py
"""
Chatterbox TTS client for VRSecretary.

This module talks to the optimized (multilingual) Chatterbox server.

Key points:

- Uses the non-streaming endpoint: POST /v1/audio/speech
- Always sets `stream = False` so we get ONE full WAV per request
  (no chunked streaming).
- Returns either raw WAV bytes or base64-encoded WAV for Unreal.

Configuration (env vars or config):

- CHATTERBOX_URL       (default: "http://localhost:4123")
- CHATTERBOX_TIMEOUT   (default: 30.0 seconds)
- CHATTERBOX_VOICE     (default: "female")
- CHATTERBOX_LANGUAGE  (default: "en", via config.chatterbox_default_language)
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from typing import Literal, Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CHATTERBOX_URL = os.getenv("CHATTERBOX_URL", settings.chatterbox_url).rstrip("/")
CHATTERBOX_TIMEOUT = float(os.getenv("CHATTERBOX_TIMEOUT", str(settings.chatterbox_timeout)))

# Default voice if caller does not specify one
DEFAULT_VOICE = os.getenv("CHATTERBOX_VOICE", settings.chatterbox_default_voice)

# Default language if caller does not specify one (ISO 639-1, e.g. "en", "it")
DEFAULT_LANGUAGE = os.getenv("CHATTERBOX_LANGUAGE", settings.chatterbox_default_language)

VoiceType = Literal["female", "male", "neutral"]


class ChatterboxTtsError(RuntimeError):
    """Raised when the Chatterbox TTS server fails or returns an error."""


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _get_client(timeout: Optional[float] = None) -> httpx.Client:
    """
    Create a synchronous HTTP client pointed at the Chatterbox server.
    """
    effective_timeout = timeout if timeout is not None else CHATTERBOX_TIMEOUT
    return httpx.Client(
        base_url=CHATTERBOX_URL,
        timeout=effective_timeout,
    )


def _post_json(path: str, json: dict, timeout: Optional[float] = None) -> httpx.Response:
    """
    POST JSON to the given path on the Chatterbox server.
    """
    client = _get_client(timeout)
    try:
        resp = client.post(path, json=json)
    except httpx.HTTPError as exc:
        raise ChatterboxTtsError(
            f"Error calling Chatterbox at {CHATTERBOX_URL}{path}: {exc}"
        ) from exc
    finally:
        client.close()

    if resp.status_code >= 400:
        # Try to surface server-side error details if present
        detail = None
        try:
            data = resp.json()
            detail = data.get("detail") or data.get("error")
        except Exception:
            # ignore JSON parse errors; we'll just report status + text
            pass

        msg = f"Chatterbox HTTP {resp.status_code}"
        if detail:
            msg += f": {detail}"
        else:
            msg += f": {resp.text}"
        raise ChatterboxTtsError(msg)

    return resp


# ---------------------------------------------------------------------------
# Synchronous public API
# ---------------------------------------------------------------------------


def tts_wav_bytes(
    text: str,
    *,
    voice: VoiceType = DEFAULT_VOICE,
    language: Optional[str] = None,
    temperature: float = 0.7,
    cfg_weight: float = 0.4,
    exaggeration: float = 0.3,
    speed: float = 1.0,
    timeout: Optional[float] = None,
) -> bytes:
    """
    Synthesize `text` into a single WAV file (bytes) using Chatterbox.

    This uses the non-streaming endpoint `/v1/audio/speech` with `stream=false`,
    so the entire input is converted into ONE audio clip.

    Parameters
    ----------
    text:
        Text to synthesize (must be non-empty).
    voice:
        Voice profile: "female", "male", or "neutral".
    language:
        Optional ISO 639-1 code ("en", "it", "fr", ...). If None, defaults
        to DEFAULT_LANGUAGE (typically "en").
    """
    if not text or not text.strip():
        raise ValueError("tts_wav_bytes: text must be non-empty")

    effective_language = language or DEFAULT_LANGUAGE

    payload = {
        "input": text,
        "language": effective_language,
        "voice": voice,
        "temperature": float(temperature),
        "cfg_weight": float(cfg_weight),
        "exaggeration": float(exaggeration),
        "speed": float(speed),

        # IMPORTANT: force non-streaming mode
        "stream": False,

        # Chunking flags are ignored in non-streaming mode, but we set them
        # explicitly for clarity.
        "chunk_by_sentences": False,
        "max_chunk_words": None,
        "max_chunk_sentences": None,
    }

    logger.debug(
        "Calling Chatterbox TTS at %s/v1/audio/speech (voice=%s, language=%s)",
        CHATTERBOX_URL,
        voice,
        effective_language,
    )
    resp = _post_json("/v1/audio/speech", json=payload, timeout=timeout)

    # Non-streaming endpoint returns the full WAV as the response body.
    wav_bytes = resp.content
    if not wav_bytes:
        raise ChatterboxTtsError("Chatterbox returned empty audio content")

    return wav_bytes


def tts_wav_base64(
    text: str,
    *,
    voice: VoiceType = DEFAULT_VOICE,
    language: Optional[str] = None,
    temperature: float = 0.7,
    cfg_weight: float = 0.4,
    exaggeration: float = 0.3,
    speed: float = 1.0,
    timeout: Optional[float] = None,
) -> str:
    """
    Synthesize `text` to WAV and return a base64-encoded string.

    This is convenient for building the `/api/vr_chat` response for Unreal,
    since the plugin expects `audio_wav_base64` in the JSON.

    `language` behaves like in `tts_wav_bytes`:
      - if provided, we send it to the multilingual TTS server,
      - otherwise we default to the gateway's DEFAULT_LANGUAGE.
    """
    wav = tts_wav_bytes(
        text,
        voice=voice,
        language=language,
        temperature=temperature,
        cfg_weight=cfg_weight,
        exaggeration=exaggeration,
        speed=speed,
        timeout=timeout,
    )
    return base64.b64encode(wav).decode("ascii")


def chatterbox_health(timeout: Optional[float] = None) -> dict:
    """
    Call the /health endpoint of the Chatterbox server.
    """
    logger.debug("Calling Chatterbox health at %s/health", CHATTERBOX_URL)
    client = _get_client(timeout)
    try:
        resp = client.get("/health")
    except httpx.HTTPError as exc:
        client.close()
        raise ChatterboxTtsError(
            f"Error calling Chatterbox /health at {CHATTERBOX_URL}/health: {exc}"
        ) from exc
    finally:
        client.close()

    if resp.status_code >= 400:
        raise ChatterboxTtsError(
            f"Chatterbox /health HTTP {resp.status_code}: {resp.text}"
        )

    try:
        return resp.json()
    except Exception as exc:
        raise ChatterboxTtsError(
            f"Failed to parse Chatterbox /health response: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Async wrappers (for FastAPI)
# ---------------------------------------------------------------------------


async def tts_wav_bytes_async(
    text: str,
    *,
    voice: VoiceType = DEFAULT_VOICE,
    language: Optional[str] = None,
    temperature: float = 0.7,
    cfg_weight: float = 0.4,
    exaggeration: float = 0.3,
    speed: float = 1.0,
    timeout: Optional[float] = None,
) -> bytes:
    """
    Async wrapper around `tts_wav_bytes` (runs in a worker thread).
    """
    return await asyncio.to_thread(
        tts_wav_bytes,
        text,
        voice=voice,
        language=language,
        temperature=temperature,
        cfg_weight=cfg_weight,
        exaggeration=exaggeration,
        speed=speed,
        timeout=timeout,
    )


async def tts_wav_base64_async(
    text: str,
    *,
    voice: VoiceType = DEFAULT_VOICE,
    language: Optional[str] = None,
    temperature: float = 0.7,
    cfg_weight: float = 0.4,
    exaggeration: float = 0.3,
    speed: float = 1.0,
    timeout: Optional[float] = None,
) -> str:
    """
    Async wrapper around `tts_wav_base64` (runs in a worker thread).
    """
    return await asyncio.to_thread(
        tts_wav_base64,
        text,
        voice=voice,
        language=language,
        temperature=temperature,
        cfg_weight=cfg_weight,
        exaggeration=exaggeration,
        speed=speed,
        timeout=timeout,
    )


async def chatterbox_health_async(timeout: Optional[float] = None) -> dict:
    """
    Async wrapper around `chatterbox_health` (runs in a worker thread).
    """
    return await asyncio.to_thread(chatterbox_health, timeout=timeout)
