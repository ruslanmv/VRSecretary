# backend/gateway/vrsecretary_gateway/api/health_router.py

import logging
from fastapi import APIRouter

from ..tts.chatterbox_client import chatterbox_health_async, ChatterboxTtsError

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
async def health():
    """
    Simple health endpoint for the VRSecretary gateway.

    Returns both gateway status and (if available) Chatterbox TTS status.
    """
    base = {"status": "ok"}

    try:
        tts_info = await chatterbox_health_async(timeout=2.0)
        return {
            **base,
            "tts": {
                "status": "ready",
                "info": tts_info,
            },
        }
    except ChatterboxTtsError as exc:
        logger.warning("Chatterbox health check failed: %s", exc)
        return {
            **base,
            "tts": {
                "status": "unavailable",
                "error": str(exc),
            },
        }
