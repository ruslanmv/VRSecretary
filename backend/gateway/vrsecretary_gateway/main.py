# backend/gateway/vrsecretary_gateway/main.py

from fastapi import FastAPI
from .api import vr_chat_router, health_router

app = FastAPI(
    title="VRSecretary Gateway",
    version="0.2.0",
    description="LLM + TTS gateway for the VRSecretary Unreal plugin.",
)

# Health endpoints
app.include_router(health_router.router, prefix="/health", tags=["health"])

# Main VR chat API for Unreal (POST /api/vr_chat)
app.include_router(vr_chat_router.router, prefix="/api", tags=["vr_chat"])


@app.get("/")
async def root():
    """
    Simple root endpoint to confirm the gateway is running.
    """
    return {
        "message": "VRSecretary gateway running",
        "docs": "/docs",
        "health": "/health",
    }


# Optional: allow running directly via `python -m vrsecretary_gateway.main`
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "vrsecretary_gateway.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        http="h11",  # IMPORTANT: avoid httptools on Windows
    )
