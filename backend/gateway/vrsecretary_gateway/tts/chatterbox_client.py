import httpx
from ..config import settings

async def synthesize_with_chatterbox(text: str) -> bytes:
    payload = {
        "input": text,
        "exaggeration": 0.35,
        "temperature": 0.7,
        "cfg_weight": 0.5,
    }
    async with httpx.AsyncClient(base_url=settings.chatterbox_url, timeout=60.0) as client:
        resp = await client.post("/v1/audio/speech", json=payload)
        resp.raise_for_status()
        return resp.content
