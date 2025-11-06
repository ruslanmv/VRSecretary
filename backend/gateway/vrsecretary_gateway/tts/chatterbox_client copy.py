# backend/gateway/vrsecretary_gateway/tts/chatterbox_client.py
"""
Chatterbox TTS client for VRSecretary.

This module talks to the optimized Chatterbox server implemented in
`tools/vr_chatterbox_server.py`.

Key points:

- Uses the non-streaming endpoint: POST /v1/audio/speech
- Always sets `stream = False` so we get ONE full WAV per request
  (no chunked streaming).
- Returns either raw WAV bytes or base64-encoded WAV for Unreal.

Configuration (env vars):

- CHATTERBOX_URL      (default: "http://localhost:4123")
- CHATTERBOX_TIMEOUT  (default: 30.0 seconds)
- CHATTERBOX_VOICE    (default: "female")
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Literal, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CHATTERBOX_URL = os.getenv("CHATTERBOX_URL", "http://localhost:4123").rstrip("/")
CHATTERBOX_TIMEOUT = float(os.getenv("CHATTERBOX_TIMEOUT", "30.0"))

# Default voice if caller does not specify one
DEFAULT_VOICE = os.getenv("CHATTERBOX_VOICE", "female")

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
        raise ChatterboxTtsError(f"Error calling Chatterbox at {CHATTERBOX_URL}{path}: {exc}") from exc
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
# Public API
# ---------------------------------------------------------------------------


def tts_wav_bytes(
    text: str,
    *,
    voice: VoiceType = DEFAULT_VOICE,
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
    text : str
        Text to synthesize.
    voice : {"female", "male", "neutral"}
        Voice profile to use. "neutral" means no voice cloning.
    temperature : float
        Sampling temperature (0.1–1.5).
    cfg_weight : float
        Guidance weight (0.0–1.0).
    exaggeration : float
        Expressiveness level (0.0–1.0).
    speed : float
        Playback speed multiplier (0.5–2.0).
    timeout : float, optional
        Request timeout in seconds. Defaults to CHATTERBOX_TIMEOUT.

    Returns
    -------
    bytes
        Raw WAV bytes (ready to base64-encode or write to a .wav file).

    Raises
    ------
    ChatterboxTtsError
        If the TTS server is unreachable or returns an error.
    """
    if not text or not text.strip():
        raise ValueError("tts_wav_bytes: text must be non-empty")

    payload = {
        "input": text,
        "voice": voice,
        "temperature": float(temperature),
        "cfg_weight": float(cfg_weight),
        "exaggeration": float(exaggeration),
        "speed": float(speed),

        # IMPORTANT: force non-streaming mode
        "stream": False,

        # We can leave chunking flags at defaults for non-streaming. They are
        # ignored in synthesize(), but we set them explicitly for clarity.
        "chunk_by_sentences": False,
        "max_chunk_words": None,
        "max_chunk_sentences": None,
    }

    logger.debug("Calling Chatterbox TTS at %s/v1/audio/speech", CHATTERBOX_URL)
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
    temperature: float = 0.7,
    cfg_weight: float = 0.4,
    exaggeration: float = 0.3,
    speed: float = 1.0,
    timeout: Optional[float] = None,
) -> str:
    """
    Synthesize `text` to WAV and return a base64-encoded string.

    This is the most convenient function to call from your FastAPI route
    that builds the `/api/vr_chat` response for Unreal, since the plugin
    expects `audio_wav_base64` in the JSON.

    Example
    -------
    >>> audio_b64 = tts_wav_base64("Hello from Ailey.")
    >>> response = {
    ...     "assistant_text": "Hello from Ailey.",
    ...     "audio_wav_base64": audio_b64,
    ... }

    Returns
    -------
    str
        Base64-encoded WAV audio (ASCII string).
    """
    wav = tts_wav_bytes(
        text,
        voice=voice,
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

    Returns
    -------
    dict
        Parsed JSON payload from /health, e.g.:

        {
          "status": "ready",
          "device": "cuda",
          "model_ready": true,
          "voices_loaded": {
            "female": true,
            "male": false
          },
          "active_requests": 0
        }

    Raises
    ------
    ChatterboxTtsError
        If the server is unreachable or returns an error.
    """
    logger.debug("Calling Chatterbox health at %s/health", CHATTERBOX_URL)
    resp = _post_json("/health", json={}, timeout=timeout)
    try:
        return resp.json()
    except Exception as exc:
        raise ChatterboxTtsError(f"Failed to parse Chatterbox /health response: {exc}") from exc
