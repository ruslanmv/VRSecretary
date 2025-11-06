"""
Chatterbox TTS client for VRSecretary.

Talks to the optimized TTS server defined in `tools/vr_chatterbox_server.py`.

- Uses POST /v1/audio/speech
- Forces non-streaming mode (stream = False)
- Returns one full WAV (bytes or base64)
"""

from __future__ import annotations

import base64
import logging
from typing import Literal, Optional

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
) -> dict:
    if not text or not text.strip():
        raise ValueError("Chatterbox TTS text must be non-empty")

    return {
        "input": text,
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
    voice: VoiceType = None,
    temperature: float = 0.7,
    cfg_weight: float = 0.4,
    exaggeration: float = 0.3,
    speed: float = 1.0,
    timeout: Optional[float] = None,
) -> bytes:
    """
    Synthesize text into a single WAV (bytes) asynchronously.
    """
    voice = voice or settings.chatterbox_default_voice  # type: ignore[arg-type]
    effective_timeout = timeout if timeout is not None else settings.chatterbox_timeout

    payload = _build_payload(
        text=text,
        voice=voice,  # type: ignore[arg-type]
        temperature=temperature,
        cfg_weight=cfg_weight,
        exaggeration=exaggeration,
        speed=speed,
    )

    base_url = settings.chatterbox_url.rstrip("/")
    logger.debug("Calling Chatterbox TTS at %s/v1/audio/speech", base_url)

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
    voice: VoiceType = None,
    temperature: float = 0.7,
    cfg_weight: float = 0.4,
    exaggeration: float = 0.3,
    speed: float = 1.0,
    timeout: Optional[float] = None,
) -> str:
    """
    Synthesize text to WAV and return base64-encoded WAV string.
    Suitable for returning to Unreal as `audio_wav_base64`.
    """
    wav = await tts_wav_bytes_async(
        text=text,
        voice=voice,
        temperature=temperature,
        cfg_weight=cfg_weight,
        exaggeration=exaggeration,
        speed=speed,
        timeout=timeout,
    )
    return base64.b64encode(wav).decode("ascii")


async def chatterbox_health_async(timeout: Optional[float] = None) -> dict:
    """
    Call the /health endpoint of the Chatterbox server.
    """
    effective_timeout = timeout if timeout is not None else settings.chatterbox_timeout
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
