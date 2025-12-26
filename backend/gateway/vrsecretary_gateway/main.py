"""
VRSecretary Gateway - FastAPI Application Entry Point.

This module defines the FastAPI application for the VRSecretary backend gateway.
It provides REST API endpoints for:
- Health checks and system status monitoring
- VR chat interactions with LLM (Ollama/watsonx.ai) and TTS (Chatterbox)

The gateway acts as an engine-agnostic bridge between VR applications (Unreal Engine,
Unity, etc.) and AI services, handling session management, conversation history,
and audio generation.

Author:
    Ruslan Magana (ruslanmv.com)

License:
    Apache-2.0

Example:
    Run the server directly::

        $ python -m vrsecretary_gateway.main

    Or via uvicorn::

        $ uvicorn vrsecretary_gateway.main:app --reload --host 0.0.0.0 --port 8000

Attributes:
    app (FastAPI): The main FastAPI application instance configured with
        metadata, routers, and CORS settings.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import health_router, vr_chat_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# ==============================================================================
# FastAPI Application Configuration
# ==============================================================================

app = FastAPI(
    title="VRSecretary Gateway",
    version="1.0.0",
    description=(
        "Production-ready AI gateway for VRSecretary Unreal Engine plugin. "
        "Provides LLM chat completion (Ollama/watsonx.ai) and TTS audio generation "
        "(Chatterbox) for immersive VR conversational experiences."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Ruslan Magana",
        "url": "https://ruslanmv.com",
        "email": "contact@ruslanmv.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

# ==============================================================================
# CORS Middleware Configuration
# ==============================================================================
# Allow cross-origin requests from Unreal Engine development servers
# In production, restrict to specific origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# API Router Registration
# ==============================================================================

# Health check endpoints (/health, /health/tts)
app.include_router(
    health_router.router,
    prefix="/health",
    tags=["health"],
)

# Main VR chat API for Unreal (POST /api/vr_chat)
app.include_router(
    vr_chat_router.router,
    prefix="/api",
    tags=["vr_chat"],
)

# ==============================================================================
# Root Endpoint
# ==============================================================================


@app.get("/", response_model=Dict[str, Any])
async def root() -> Dict[str, Any]:
    """
    Root endpoint providing gateway status and API documentation links.

    This endpoint serves as a quick reference for developers to verify the
    gateway is running and discover available API endpoints.

    Returns:
        Dict[str, Any]: Gateway information including:
            - message: Welcome message
            - version: API version
            - docs: Link to interactive API documentation
            - redoc: Link to ReDoc API documentation
            - health: Link to health check endpoint

    Example:
        >>> import httpx
        >>> async with httpx.AsyncClient() as client:
        ...     response = await client.get("http://localhost:8000/")
        ...     print(response.json())
        {
            "message": "VRSecretary Gateway API",
            "version": "1.0.0",
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health"
        }
    """
    logger.debug("Root endpoint accessed")
    return {
        "message": "VRSecretary Gateway API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "author": "Ruslan Magana (ruslanmv.com)",
    }


# ==============================================================================
# Application Startup/Shutdown Events
# ==============================================================================


@app.on_event("startup")
async def startup_event() -> None:
    """
    Application startup event handler.

    Executes when the FastAPI application starts. Used for initialization
    tasks like verifying service connections and pre-loading resources.

    Note:
        This is called once when the server starts, not on every request.
    """
    logger.info("VRSecretary Gateway starting up...")
    logger.info("Gateway version: 1.0.0")
    logger.info("FastAPI docs available at /docs")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Application shutdown event handler.

    Executes when the FastAPI application shuts down. Used for cleanup
    tasks like closing database connections and releasing resources.

    Note:
        This is called once during graceful shutdown, not on every request.
    """
    logger.info("VRSecretary Gateway shutting down...")


# ==============================================================================
# Direct Execution Support
# ==============================================================================

if __name__ == "__main__":
    import uvicorn

    # Direct execution with Python
    # IMPORTANT: Use h11 on Windows to avoid httptools compatibility issues
    uvicorn.run(
        "vrsecretary_gateway.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        http="h11",  # Force h11 HTTP protocol (cross-platform compatibility)
    )
