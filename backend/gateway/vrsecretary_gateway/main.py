from fastapi import FastAPI
from .api import vr_chat_router, health_router

app = FastAPI(title="VRSecretary Gateway")

app.include_router(health_router.router, prefix="/health", tags=["health"])
app.include_router(vr_chat_router.router, prefix="/api", tags=["vr_chat"])
