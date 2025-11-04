# Deployment & Installation Guide

This guide focuses on **deploying** VRSecretary’s backend and Unreal plugin in
realistic setups, from local development to more production-like environments.

---

## 1. Components Recap

VRSecretary consists of:

- **Unreal plugin** (`engine-plugins/unreal/VRSecretary/`)
  - Built into your game project and distributed with it.
- **FastAPI gateway** (`backend/gateway/`)
  - Python service handling `/api/vr_chat` and LLM/TTS.
- **LLM provider(s)**
  - Local: **Ollama** (via OpenAI-style Chat Completions).
  - Cloud: **IBM watsonx.ai**.
- **TTS provider**
  - **Chatterbox TTS**.

Additionally, you may use:

- **Llama-Unreal plugin** for the `LocalLlamaCpp` mode (fully in-engine models).
- Docker / Docker Compose for containerized deployments.

---

## 2. Local Development Setup

### 2.1 Backend (Python venv)

```bash
cd backend/gateway
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -e .
# Optional watsonx extras:
# pip install -e ".[watsonx]"
```

Copy environment variables template:

```bash
cd ../docker
cp env.example ../gateway/.env
cd ../gateway
```

Edit `.env` to match your setup. For local Ollama + Chatterbox:

```env
MODE=offline_local_ollama

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

CHATTERBOX_URL=http://localhost:4123
SESSION_MAX_HISTORY=10
```

Run the gateway:

```bash
uvicorn vrsecretary_gateway.main:app --reload --host 0.0.0.0 --port 8000
```

Check:

- <http://localhost:8000/health>
- <http://localhost:8000/docs>

### 2.2 Ollama (local LLM)

Install from <https://ollama.ai/> and run:

```bash
ollama serve
ollama pull llama3
```

Confirm models:

```bash
curl http://localhost:11434/v1/models
```

### 2.3 Chatterbox (TTS)

Install per its README and run:

```bash
chatterbox-server --port 4123
```

Sanity check:

```bash
curl -X POST http://localhost:4123/v1/audio/speech   -H "Content-Type: application/json"   -d '{"input": "Hello from Ailey.", "temperature": 0.6, "cfg_weight": 0.5, "exaggeration": 0.35}'   --output test.wav
```

Play `test.wav` to verify audio.

### 2.4 Unreal Project

1. Copy the plugin into your project’s `Plugins/` folder.
2. Run the patch script once (from repo root):

   ```bash
   chmod +x tools/scripts/apply_vrsecretary_patch.sh
   ./tools/scripts/apply_vrsecretary_patch.sh
   ```

3. Generate project files, build, and open in Unreal.
4. Configure **Project Settings → Plugins → VRSecretary**:
   - `Gateway URL` = `http://localhost:8000`
   - `Backend Mode` = `Gateway (Ollama)` (or `Gateway (watsonx.ai)`)
   - `HTTP Timeout` = e.g. `60.0`

---

## 3. Docker-Based Development

A Docker Compose file is provided under `backend/docker/docker-compose.dev.yml`
for local experiments.

From repo root:

```bash
cd backend/docker
docker-compose -f docker-compose.dev.yml up --build
```

Depending on the configuration, this can:

- Build and run the FastAPI gateway in a container.
- Start a local Ollama container.
- Expect Chatterbox on the host (using `host.docker.internal` on supported OSes).

Adjust `env.example` and `docker-compose.dev.yml` to your needs (ports, GPU
access, etc.).

---

## 4. Example Production-Like Setup

A realistic deployment may look like this:

```text
+-----------------------------+
|        Client Devices       |
| (VR headsets / PC clients)  |
+--------------+--------------+
               |
               | HTTPS (reverse proxy)
               v
+-----------------------------+
|    API Gateway / Ingress    |
+-----------------------------+
               |
               v
+-----------------------------+
|   VRSecretary FastAPI App   |
|   (gunicorn/uvicorn, etc.)  |
+-----------------------------+
        |                 |
        | HTTP            | HTTPS / Private API
        v                 v
+---------------+   +--------------------+
|    Ollama     |   |    watsonx.ai      |
| (OpenAI API)  |   | (cloud provider)   |
+---------------+   +--------------------+
        |
        | HTTP
        v
+-----------------+
|  Chatterbox TTS |
+-----------------+
```

### 4.1 Process Layout

- **FastAPI gateway** behind a reverse proxy (NGINX, Caddy, etc.) with HTTPS.
- **Ollama** running on a GPU-capable host with the necessary models pulled.
- **Chatterbox** on the same host as the gateway, or a nearby machine with
  GPU resources.
- Optional: **watsonx.ai** for cloud LLMs (only outbound HTTPS needed).

### 4.2 Configuration Tips

- Use environment variables or `docker-compose` overrides to switch between
  `MODE=offline_local_ollama` and `MODE=online_watsonx` without changing code.
- For production, consider:
  - Setting stricter timeouts and error handling.
  - Using a process manager (systemd, Supervisor) or an orchestrator (Kubernetes).
  - Configuring HTTPS at the ingress level and keeping internal traffic on
    a private network.

### 4.3 Scaling Considerations

- **Gateway scaling**: The FastAPI gateway is stateless except for in-memory
  session history. You can:
  - Keep sessions sticky to a particular instance, or
  - Move session state to a shared store (Redis, database) if you run multiple replicas.

- **LLM throughput**:
  - Ollama’s throughput depends heavily on GPU and model size.
  - For multi-user VR experiences, load-test using the provided k6 script and
    adjust model / hardware accordingly.

- **TTS latency**:
  - TTS is often the latency bottleneck.
  - Consider caching repeated phrases, using fast voices, or pre-generating
    common prompts where appropriate.

---

## 5. Unreal Plugin Distribution

When you build and ship your Unreal project:

- The `VRSecretary` plugin code is compiled into your packaged game.
- Any **Llama-Unreal** plugin and its models (for LocalLlamaCpp) must be included
  as part of your packaging strategy if you use that mode.

The **FastAPI gateway, Ollama, and Chatterbox** are **not** packaged into the
Unreal game; they are external services. You can:

- Host them on the same machine as the game (single-user setups).
- Host them on a local network server (LAN/enterprise).
- Host them in the cloud, accessible over HTTPS.

Your game’s config (e.g. `GatewayUrl`) should be set appropriately for each
target environment.

---

## 6. Testing & Monitoring

### 6.1 Backend Tests

From `backend/gateway`:

```bash
pytest
# or
pytest --cov=vrsecretary_gateway --cov-report=html
```

### 6.2 Load Testing

From `tools/perf`:

```bash
k6 run load_test_vr_chat.k6.js
```

This script hits `/api/vr_chat` with configurable concurrency and lets you
evaluate latency and throughput.

### 6.3 Logging & Tracing

- Configure FastAPI / Uvicorn logging to log requests, LLM and TTS timings.
- Consider adding request IDs to correlate logs with user sessions.
- Instrument with Prometheus / OpenTelemetry if needed.

---

## 7. Security Notes

- Treat any API keys (e.g. watsonx) as secrets. Do not hard-code them in code
  or push them to version control.
- Use HTTPS for external traffic (VR clients to gateway, gateway to cloud LLMs).
- If you expose `/api/vr_chat` on the public internet, consider:
  - Authentication (tokens, API keys, or OAuth2).
  - Rate limiting per IP / client.
  - Input validation and output filtering to prevent abuse.

---

With these patterns, you can run VRSecretary anywhere from a single dev
machine to a small production cluster, while keeping the Unreal integration
simple and stable.
