# VRSecretary Architecture

This document dives into the **high-level architecture** of VRSecretary and how the pieces connect.

## Overview Diagram

```text
┌────────────────────────────────────────────────────────────┐
│                    Unreal Engine 5 (VR)                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  BP_VRSecretaryManager                              │  │
│  │  - Handles user input (VR controllers / UI)         │  │
│  │  - Owns UVRSecretaryComponent                       │  │
│  │  - Manages session state / avatar link              │  │
│  └────────────┬───────────────────────────────────────┘  │
│               │                                           │
│  ┌────────────▼───────────────────────────────────────┐  │
│  │  UVRSecretaryComponent (C++ ActorComponent)        │  │
│  │  - SendUserText(UserText, Config)                  │  │
│  │  - OnAssistantResponse(AssistantText, AudioBase64) │  │
│  │  - OnError(ErrorMessage)                           │  │
│  └────────────┬───────────────────────────────────────┘  │
│               │   HTTP POST /api/vr_chat                  │
└───────────────▼───────────────────────────────────────────┘
                │  JSON: {session_id, user_text}
                │
┌───────────────▼───────────────────────────────────────────┐
│              FastAPI Gateway Backend (Python)             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  /health                                            │ │
│  │  /api/vr_chat                                       │ │
│  │    - Validate VRChatRequest                         │ │
│  │    - Load/save session history (optional)           │ │
│  │    - Build chat messages (system + user + history)  │ │
│  │    - Call LLM client (Ollama / watsonx.ai)          │ │
│  │    - Call Chatterbox TTS for audio                  │ │
│  │    - Return VRChatResponse                          │ │
│  └────────────┬────────────────────────────────────────┘ │
│               │                                           │
│  ┌────────────▼────────────────────────────────────────┐ │
│  │   LLM Client Abstraction                            │ │
│  │   - BaseLLMClient                                   │ │
│  │   - OllamaClient (offline_local_ollama)             │ │
│  │   - WatsonxClient (online_watsonx)                  │ │
│  └────────────┬────────────────────────────────────────┘ │
│               │                                           │
│  ┌────────────▼────────────────────────────────────────┐ │
│  │   Chatterbox TTS Client                             │ │
│  │   - /v1/audio/speech → WAV audio                    │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

## Modules & Responsibilities

### 1. Unreal Plugin (`engine-plugins/unreal/VRSecretary`)

**Key classes:**

- `UVRSecretaryComponent` (C++ ActorComponent)
  - Blueprint spawnable; attach to a manager or avatar.
  - Exposes:
    - `SendUserText(const FString& UserText, const FVRSecretaryChatConfig& Config)`.
    - `OnAssistantResponse` (Blueprint multicast delegate: text + audio base64).
    - `OnError` (Blueprint delegate).
  - Implements backend modes:
    - Gateway (Ollama / watsonx.ai) → `/api/vr_chat` on the FastAPI backend.
    - Direct Ollama mode → `http://localhost:11434/v1/chat/completions` (text only).
    - Local Llama.cpp stub → placeholder to wire a direct llama.cpp integration.

- `UVRSecretarySettings` (Developer Settings)
  - Configurable in **Project Settings → Plugins → VRSecretary**.
  - Holds:
    - `GatewayUrl` (e.g., `http://localhost:8000`).
    - `BackendMode` (enum).
    - HTTP timeout.
    - `DirectOllamaUrl`, `DirectOllamaModel` for direct mode.

- `EVRSecretaryBackendMode`
  - `GatewayOllama`
  - `GatewayWatsonx`
  - `DirectOllama`
  - `LocalLlamaCpp` (stub).

### 2. Backend Gateway (`backend/gateway/vrsecretary_gateway`)

**Main files:**

- `main.py`
  - Creates FastAPI `app`.
  - Mounts routers:
    - `/health` (health check).
    - `/api/vr_chat` (main LLM + TTS endpoint).
  - Adds CORS middleware.

- `config.py`
  - Uses `pydantic-settings` to load configuration from `.env` / environment:
    - `MODE` – `offline_local_ollama` or `online_watsonx`.
    - `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, timeouts.
    - `CHATTERBOX_URL`, timeouts.
    - `WATSONX_*` credentials, if used.

- `api/`:
  - `health_router.py` – `/health` returns `{status, mode, timestamp}`.
  - `vr_chat_router.py` – `/api/vr_chat` endpoint, containing:
    - The **Ailey** system prompt.
    - Request model: `VRChatRequest` with `session_id`, `user_text`.
    - Response model: `VRChatResponse` with `assistant_text`, `audio_wav_base64`.
    - LLM + TTS orchestration logic.

- `models/`:
  - `chat_schemas.py` – `ChatMessage`, `VRChatRequest`, `VRChatResponse` Pydantic models.
  - `session_store.py` – simple in-memory session history (can be replaced with Redis in production).

- `llm/`:
  - `base_client.py` – `BaseLLMClient` (abstract) and `get_llm_client()` factory.
  - `ollama_client.py` – uses `httpx` to call Ollama’s `/v1/chat/completions` (OpenAI-compatible).
  - `watsonx_client.py` – uses IBM Watsonx SDK to call hosted models.

- `tts/`:
  - `chatterbox_client.py` – `synthesize_with_chatterbox(text)` calling `/v1/audio/speech`.

### 3. External Services

- **Ollama**:
  - Runs on host or in Docker (`ollama/ollama` image).
  - Exposes `http://localhost:11434` (or `http://ollama:11434` in Docker compose).
  - Models must be pulled beforehand (`ollama pull llama3`).

- **IBM watsonx.ai**:
  - Cloud LLM platform.
  - Requires API key, URL, project ID, model ID.
  - Only used when `MODE=online_watsonx`.

- **Chatterbox TTS**:
  - Self-hosted TTS server.
  - Exposes `http://localhost:4123/v1/audio/speech` by default.
  - Configured via `CHATTERBOX_URL` in `.env` or Docker env.

## Data Flow Example

1. Unreal calls `SendUserText("Schedule a meeting for tomorrow at 3pm", Config)`.
2. Plugin builds JSON `{session_id, user_text}` and POSTs to `/api/vr_chat`.
3. Backend constructs a list of `ChatMessage` objects:
   - System message (Ailey’s persona prompt).
   - (Optional) previous history for the session.
   - User message.
4. `get_llm_client()` returns an `OllamaClient` or `WatsonxClient` based on `MODE`.
5. LLM returns an assistant reply.
6. TTS client calls Chatterbox to produce WAV audio bytes.
7. Backend base64-encodes the WAV and returns:
   - `assistant_text`
   - `audio_wav_base64`
8. Unreal Blueprint receives `OnAssistantResponse`:
   - Updates subtitles on the avatar.
   - Decodes/plays audio on an `AudioComponent`.

## Scaling & Production Considerations

- Replace in-memory `session_store` with Redis or a database.
- Add authentication/JWT to the backend if exposed over the internet.
- Use gunicorn/uvicorn workers behind a reverse proxy (nginx, Traefik).
- Consider streaming responses (server-sent events / WebSockets) for long replies.
- Implement rate limiting per user/session/IP.

For the concrete HTTP API specification (routes, payloads, error formats), see `engine-agnostic-api.md`.
