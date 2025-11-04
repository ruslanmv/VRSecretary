# Deployment & Installation Guide

This guide shows you how to set up the **VRSecretary backend** and supporting
services (Ollama + Chatterbox) using the provided **Makefile**, and how to
optionally run the backend in Docker.

It assumes you’re in the repository root:

```bash
cd VRSecretary
```

---

## 1. Requirements

- **OS**: Windows 10/11, Linux, or macOS.
- **Python**: 3.11.x (Makefile will verify).
- **Unreal Engine**: 5.3+ (for the VR client; not needed for backend-only usage).
- **Docker** (optional) if you want containerized deployments.
- **Ollama** installed on the host (Makefile can help install & start it).
- **Chatterbox TTS** installed on the host (or another machine).

---

## 2. Quick Start Using the Makefile

The root `Makefile` provides convenient targets for setup and development.

### 2.1 Install Everything (Environment + Backend + Ollama)

From the repo root:

```bash
make install
```

This will:

1. Create a Python 3.11 virtual environment in `.venv` (if it doesn’t exist).
2. Install the root `simple-environment` (Jupyter + Ollama Python client) via `pyproject.toml`.
3. Install the VRSecretary backend (`backend/gateway`) into the same `.venv`.
4. Register a Jupyter kernel named **"Python 3.11 (VRSecretary)"**.
5. Attempt to install **Ollama** on the host (if missing).
6. Attempt to start the **Ollama server** and verify it is reachable at `http://localhost:11434`.

> If Ollama installation fails, install it manually from <https://ollama.com/download>.

### 2.2 Start the Backend Gateway

Once `make install` completes successfully, run:

```bash
make run-gateway
```

This will:

- Use `.venv`'s Python interpreter.
- Run `uvicorn vrsecretary_gateway.main:app` on `http://0.0.0.0:8000`.

Check that it’s working:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "mode": "offline_local_ollama",
  "timestamp": "..."
}
```

### 2.3 Configure `.env` for the Backend

The backend reads its settings from environment variables via `pydantic-settings`.
To set them conveniently, use the example file:

```bash
cp backend/docker/env.example backend/gateway/.env
```

Then edit `backend/gateway/.env`:

```env
MODE=offline_local_ollama

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

CHATTERBOX_URL=http://localhost:4123

# Optional watsonx.ai settings if using MODE=online_watsonx
# WATSONX_URL=...
# WATSONX_PROJECT_ID=...
# WATSONX_MODEL_ID=...
# WATSONX_API_KEY=...
```

Restart the gateway if you change `.env`.

---

## 3. Running Supporting Services

### 3.1 Ollama (LLM)

You can let the Makefile handle it via:

```bash
make ensure-ollama-running
```

Or do it manually:

```bash
# Start server
ollama serve

# In another terminal, pull a model
ollama pull llama3
```

Confirm the API is up:

```bash
curl http://localhost:11434/api/tags
```

### 3.2 Chatterbox TTS

Install Chatterbox according to its README, then run:

```bash
chatterbox-server --port 4123
```

Quick test:

```bash
curl -X POST http://localhost:4123/v1/audio/speech           -H "Content-Type: application/json"           -d '{ "input": "Hello from Ailey.", "temperature": 0.6, "cfg_weight": 0.5, "exaggeration": 0.35 }'           --output test.wav
```

Play `test.wav` to ensure audio is correct.

---

## 4. Docker-Based Backend Deployment

There are two Docker-related flows:

1. **Dev container for Jupyter + Ollama** (root Dockerfile + Make targets).
2. **Backend + Ollama stack** via `docker-compose.dev.yml`.

### 4.1 Dev Container (Jupyter + Ollama + simple-environment)

From the repo root:

```bash
make build-container
make run-container
```

This uses the root **Dockerfile** to build an image `simple-env:latest` which contains:

- Ollama server.
- Python 3.11 virtualenv.
- `simple-environment` installed (Jupyter + Ollama Python client).

After running `make run-container`, you should have:

- Jupyter at `http://localhost:8888`.
- Ollama at `http://localhost:11434` (inside the container).

Logs:

```bash
make logs
```

Stop & remove the container:

```bash
make stop-container
make remove-container
```

### 4.2 Backend Dev Stack (Gateway + Ollama via docker-compose)

Under `backend/docker`, there is a `docker-compose.dev.yml` which starts:

- `ollama` service.
- `gateway` service (FastAPI).

Use the Makefile helpers:

```bash
# From repo root
make docker-dev-up      # starts gateway + Ollama
make docker-dev-logs    # tail logs
make docker-dev-down    # stop and remove
```

By default, it maps:

- `gateway` → `http://localhost:8000`
- `ollama`  → `http://localhost:11434` (inside compose)

In this configuration, you likely want `CHATTERBOX_URL=http://host.docker.internal:4123`
so that gateway can reach a Chatterbox instance running on the host.

---

## 5. Testing the Backend API

With backend + Ollama + Chatterbox running (either locally or in Docker):

```bash
curl -X POST http://localhost:8000/api/vr_chat           -H "Content-Type: application/json"           -d '{
    "session_id": "test-session-1",
    "user_text": "Hello Ailey, who are you?"
  }'
```

You should see a JSON response similar to:

```json
{
  "assistant_text": "Hi! I'm Ailey, your VR secretary. I'm here to help with planning and tasks...",
  "audio_wav_base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YcQAAA..."
}
```

If this works, Unreal (or any client) can consume the same endpoint.

---

## 6. Unreal Configuration

Once the backend is running, configure Unreal as follows:

1. In UE5, open your VR project (sample or custom).
2. Go to **Edit → Project Settings → Plugins → VRSecretary**.
3. Set:
   - **Gateway URL** = `http://localhost:8000`
   - **Backend Mode** = `Gateway (Ollama)` or `Gateway (Watsonx)`
4. Ensure any Blueprint that uses `UVRSecretaryComponent` forwards the `OnAssistantResponse`
   into your avatar’s subtitle widget and audio playback logic.

For step-by-step Unreal integration details, see `unreal-integration.md`.

---

## 7. Production Tips

- Use a **reverse proxy** (nginx, Traefik, API gateway) in front of FastAPI.
- Terminate TLS at the proxy and forward requests to the gateway.
- Run multiple instances of the gateway (uvicorn workers or separate containers).
- Externalize logging and monitoring.
- Consider secrets management for API keys (e.g., watsonx.ai).

VRSecretary is meant to be a solid starting point. Adapt and harden it according to your own production requirements.
