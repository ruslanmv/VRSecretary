# VRSecretary

🤖 **AI-Powered VR Secretary** – An open-source reference implementation that combines **Unreal Engine 5 VR**, **local/cloud LLMs**, and **high-quality TTS** to bring a fully interactive virtual secretary into VR.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Unreal Engine](https://img.shields.io/badge/Unreal-5.3+-blue.svg)](https://www.unrealengine.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org/)

---

## ✨ What Is VRSecretary?

VRSecretary is a **reference architecture** and implementation for building AI-powered VR characters:

- Frontend in **Unreal Engine 5** (VR-ready).
- Backend in **Python / FastAPI**.
- LLM via **Ollama** (local) or **IBM watsonx.ai** (cloud).
- TTS via **Chatterbox** (self-hosted, OpenAI-style).

It ships with:

- A **VR secretary avatar** (Scifi Girl v.01 – non-commercial).
- An **Unreal plugin** (`VRSecretary`) for easy integration.
- A **gateway backend** that exposes a clean `/api/vr_chat` HTTP endpoint.
- Documentation for extending to other engines (e.g., Unity) via the same API.

---

## 🌟 Key Features

- **VR-native UX**
  - Built around UE5’s VR template (controllers, teleport, VR camera).
  - Uses a 3D avatar, audio, and subtitles for a fully immersive experience.

- **Flexible LLM Backends**
  - **Offline (default):** [Ollama](https://ollama.ai/) running locally (e.g. `llama3`, Granite, Mistral, etc.).
  - **Online (optional):** [IBM watsonx.ai](https://www.ibm.com/watsonx) via official SDK/API.

- **High-Quality Voice**
  - [Chatterbox TTS](https://github.com/rsxdalv/chatterbox) for natural-sounding speech.
  - Text → WAV audio streamed back to Unreal and played in real-time.

- **Modular, Engine-Agnostic Architecture**
  - Clean REST API (`/api/vr_chat`) that any engine or application can call.
  - UE plugin is just one client; Unity or custom VR apps can reuse the same backend.

- **Sample Avatar Included**
  - **Scifi Girl v.01** (non-commercial reference character) imported as GLB.
  - Ready to plug into the VR demo level as your first AI secretary.

- **Production-oriented Structure**
  - Clear separation of concerns (backend, engine plugins, assets, tools).
  - Configurable via `.env` and Unreal Project Settings.
  - Ready for Dockerized deployment of the backend.

---

## 🧬 Repository Structure

At a high level:

```text
VRSecretary/
├── assets/                  # 3D avatars and related metadata
│   └── avatars/
│       └── scifi_girl_v01/
│           ├── scifi_girl_v.01.glb          # Example GLB (non-commercial)
│           ├── README.md                    # License & usage info
│           └── DOWNLOAD_INSTRUCTIONS.txt
│
├── backend/
│   ├── gateway/             # FastAPI backend (LLM + TTS gateway)
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   └── vrsecretary_gateway/
│   │       ├── main.py                  # FastAPI app entrypoint
│   │       ├── config.py                # Pydantic settings
│   │       ├── api/                     # HTTP routes (/health, /api/vr_chat)
│   │       ├── llm/                     # Ollama + watsonx.ai clients
│   │       ├── tts/                     # Chatterbox TTS client
│   │       └── models/                  # Pydantic schemas & session store
│   └── docker/
│       ├── Dockerfile.gateway
│       ├── docker-compose.dev.yml
│       └── env.example
│
├── engine-plugins/
│   ├── unreal/
│   │   ├── VRSecretary.uplugin           # Unreal plugin descriptor
│   │   └── Source/VRSecretary/           # Plugin C++ source
│   └── unity/                            # (Future) Unity client skeleton
│
├── samples/
│   ├── unreal-vr-secretary-demo/         # Example UE5 VR project
│   │   ├── VRSecretaryDemo.uproject
│   │   ├── Config/
│   │   └── Content/                      # Blueprints, UI, etc.
│   └── backend-notebooks/                # Jupyter prototyping
│
├── docs/
│   ├── overview.md
│   ├── architecture.md
│   ├── unreal-integration.md
│   ├── engine-agnostic-api.md
│   └── persona-ailey.md
│
├── tools/
│   ├── scripts/
│   │   ├── start_local_stack.sh          # Convenience startup script (optional)
│   │   └── generate_openapi_client.sh
│   └── perf/
│       ├── load_test_vr_chat.k6.js
│       └── profiling_notes.md
│
├── .github/                # CI, issue templates, etc.
├── LICENSE
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
└── README.md               # (This file)
````

---

## 🧩 System Requirements

**Host machine:**

* **OS:** Windows 10/11 (recommended for Unreal), Linux/macOS usable for backend only.
* **CPU:** Modern quad-core or better.
* **RAM:** 16 GB (32 GB recommended for local LLMs).
* **GPU:** NVIDIA GPU with CUDA (recommended for Ollama + Chatterbox acceleration).

**Software:**

* **Unreal Engine:** 5.3+ with C++ and VR modules installed.
* **Visual Studio 2022** (on Windows) with “Game development with C++”.
* **Python:** 3.10+.
* **Node / k6:** only if you run the load tests (optional).
* **Docker:** optional, if you prefer containerized backend.

---

## 🚀 End-to-End Quick Start (Local Machine)

This walks you through:

1. Setting up and running the backend.
2. Starting Ollama (LLM) and Chatterbox (TTS).
3. Opening the Unreal demo and talking to the VR secretary.

### 0. Clone the Repo

```bash
git clone https://github.com/ruslanmv/VRSecretary.git
cd VRSecretary
```

> Replace the URL with your actual Git repo when you publish.

---

### 1. Start the Backend (FastAPI Gateway)

#### 1.1 Create and activate a virtual environment (recommended)

```bash
cd backend/gateway

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
# python3 -m venv .venv
# source .venv/bin/activate
```

#### 1.2 Install dependencies

```bash
pip install -e .
# Optional extra: watsonx support
# pip install -e ".[watsonx]"
```

#### 1.3 Configure environment

Copy the example:

```bash
cp ../docker/env.example .env
```

Edit `.env` and set at least:

```env
MODE=offline_local_ollama

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

CHATTERBOX_URL=http://localhost:4123
```

> For **watsonx.ai** mode, switch `MODE=online_watsonx` and fill the `WATSONX_*` variables too.

#### 1.4 Run the gateway

```bash
uvicorn vrsecretary_gateway.main:app --reload --host 0.0.0.0 --port 8000
```

You should now have:

* OpenAPI docs at: [http://localhost:8000/docs](http://localhost:8000/docs)
* Health endpoint: [http://localhost:8000/health](http://localhost:8000/health)

---

### 2. Start the LLM (Ollama)

Install Ollama from the official site, then:

```bash
# Start the Ollama server
ollama serve
```

In another terminal:

```bash
# Pull a model (example: Llama 3)
ollama pull llama3
```

You can test it quickly:

```bash
curl http://localhost:11434/v1/models
```

Make sure the model name in `.env` matches (e.g. `OLLAMA_MODEL=llama3`).

---

### 3. Start the TTS (Chatterbox)

Install Chatterbox according to its README, then run:

```bash
chatterbox-server --port 4123
```

To smoke-test TTS:

```bash
curl -X POST http://localhost:4123/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{ "input": "Hello from Ailey.", "temperature": 0.6, "cfg_weight": 0.5, "exaggeration": 0.35 }' \
  --output test.wav
```

Play `test.wav` with any audio player to confirm it works.

---

### 4. Test the Backend API (Optional but Recommended)

With gateway + Ollama + Chatterbox running:

```bash
curl -X POST http://localhost:8000/api/vr_chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-123", "user_text": "Hello Ailey, who are you?"}'
```

Expected JSON response:

```json
{
  "assistant_text": "Hi! I'm Ailey, your VR secretary...",
  "audio_wav_base64": "UklGRiQAAABXQVZF..."
}
```

If this works, Unreal will be able to talk to the same endpoint.

---

### 5. Unreal Engine: Plugin & Sample Project

You have two options:

#### 5.1 Use the Sample Project (Recommended First)

1. Open **Unreal Engine 5.3+**.

2. In Explorer / Finder, go to:

   ```text
   VRSecretary/samples/unreal-vr-secretary-demo/
   ```

3. Right-click `VRSecretaryDemo.uproject` → **Generate Visual Studio project files**.

4. Double-click `VRSecretaryDemo.uproject` to open it in Unreal.

5. When prompted, let UE build the project (it will compile the `VRSecretary` C++ plugin).

6. In Unreal, open:

   * **Edit → Plugins** and verify **VRSecretary** is enabled.
   * **Edit → Project Settings → Plugins → VRSecretary** and ensure:

     * Gateway URL = `http://localhost:8000`
     * Backend mode matches `.env` (`offline_local_ollama` or `online_watsonx`).

7. Import or verify the avatar:

   * The GLB `assets/avatars/scifi_girl_v01/scifi_girl_v.01.glb` can be imported into the demo project.
   * In the sample, you may already have a `BP_SecretaryAvatar` blueprint referencing a skeletal mesh. You can retarget that to the Scifi Girl mesh.

8. Connect VR headset and press **Play → VR Preview**.

You should see the secretary avatar in front of you. Using the input configured in `BP_VRSecretaryManager` (e.g., a controller button + keyboard input), you can send messages and hear Ailey answer via TTS.

#### 5.2 Add the Plugin to Your Own Project

1. Copy the plugin:

   ```bash
   cd VRSecretary
   mkdir -p /path/to/YourUEProject/Plugins
   cp -r engine-plugins/unreal/VRSecretary /path/to/YourUEProject/Plugins/
   ```

2. Right-click your project’s `.uproject` → **Generate Visual Studio project files**.

3. Open the project, then in Plugins make sure **VRSecretary** is enabled.

4. Create a Blueprint Manager that owns a `VRSecretaryComponent` and wires `OnResponse` → your Avatar.

For detailed step-by-step with screenshots, see:
`docs/unreal-integration.md`

---

## ⚙️ Configuration Summary

### Backend (`.env` in `backend/gateway/`)

Key values:

```env
# Mode: offline (Ollama) or online (watsonx.ai)
MODE=offline_local_ollama   # or online_watsonx

# Ollama (local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
OLLAMA_TIMEOUT=60.0

# Chatterbox (TTS)
CHATTERBOX_URL=http://localhost:4123
CHATTERBOX_TIMEOUT=30.0

# watsonx.ai (only if MODE=online_watsonx)
# WATSONX_URL=https://us-south.ml.cloud.ibm.com
# WATSONX_PROJECT_ID=your-project-id
# WATSONX_MODEL_ID=ibm/granite-13b-chat-v2
# WATSONX_API_KEY=your-api-key
# WATSONX_TIMEOUT=60.0

# Session history
SESSION_MAX_HISTORY=10
```

### Unreal Plugin Settings

In **Project Settings → Plugins → VRSecretary** you can configure:

* **Gateway URL** – e.g. `http://localhost:8000`
* **Request Timeout** – e.g. `60.0`
* **Backend Mode** – e.g. `Gateway (Ollama)` / `Gateway (Watsonx)`
* **Default Session ID Behavior** – auto-generate or set explicitly.

---

## 🧠 AI Persona: Ailey

The default secretary persona is defined via a **system prompt** in the backend:

* Professional yet friendly.
* Business-focused (planning, drafting emails, scheduling suggestions).
* VR-aware (reference the “virtual office” context).
* Concise (responses are spoken aloud, so they avoid big monologues).

You can customize Ailey by editing the `SYSTEM_PROMPT` in:

```text
backend/gateway/vrsecretary_gateway/api/vr_chat_router.py
```

See `docs/persona-ailey.md` for detailed examples and variants
(formal, casual, legal assistant, technical assistant, etc.).

---

## 🎭 Avatar: Scifi Girl v.01 (Non-Commercial)

The sample avatar used in this project is:

* **Name:** *Scifi Girl v.01*
* **Author:** patrix
* **Source:** [Sketchfab](https://sketchfab.com/3d-models/scifi-girl-v01-96340701c2ed4d37851c7d9109eee9c0)
* **License:** [CC BY-NC-SA](https://creativecommons.org/licenses/by-nc-sa/4.0/)

In this repository:

```text
assets/avatars/scifi_girl_v01/
  ├── scifi_girl_v.01.glb          # Example model for your local use
  ├── README.md                    # License details & attribution
  └── DOWNLOAD_INSTRUCTIONS.txt
```

**Important:**

* This model is included **only as a non-commercial reference**.
* It must not be used commercially unless you have explicit permission from the creator.
* If you plan to:

  * Sell a game,
  * Distribute a commercial product,
  * Or repackage this repository for commercial use,

  then **replace this avatar** with:

  * A commercial asset you’ve licensed, or
  * A CC0/public domain avatar, or
  * A model you created yourself/commissioned.

The core **VRSecretary code** itself remains **MIT-licensed** and is independent from this asset.

---

## 🛠️ Development & Advanced Usage

### Run Backend with Docker Compose

If you prefer containers:

```bash
cd backend/docker
docker-compose -f docker-compose.dev.yml up
```

This will:

* Start **Ollama** in a container.
* Build and run the **gateway** container.

You still need to run **Chatterbox** separately (often directly on the host for GPU access):

```bash
chatterbox-server --port 4123
```

Adjust `CHATTERBOX_URL` to `http://host.docker.internal:4123` (already set in `docker-compose.dev.yml`).

### Run Tests (Backend)

From `backend/gateway`:

```bash
pytest
```

With coverage:

```bash
pytest --cov=vrsecretary_gateway --cov-report=html
```

### Load Testing

From `tools/perf` you can use the `k6` script:

```bash
k6 run load_test_vr_chat.k6.js
```

This stresses `/api/vr_chat` and gives you latency / throughput metrics.

---

## 🧱 High-Level Architecture

Very briefly:

* **Unreal (VR)**:

  * `VRSecretaryComponent` sends `user_text` + `session_id` via HTTP to the backend.
  * Receives `assistant_text` + `audio_wav_base64`.
  * Blueprint manager forwards text/audio to the avatar for playback + subtitles.

* **Backend (FastAPI)**:

  * Validates request (`VRChatRequest`).
  * Builds dialogue context (system + user messages, optional history).
  * Uses `BaseLLMClient` abstraction to call **Ollama** or **watsonx.ai**.
  * Sends the LLM’s text to **Chatterbox** for speech.
  * Returns the result as `VRChatResponse`.

See `docs/architecture.md` for full diagrams and more detail.

---

## 🤝 Contributing

Contributions are welcome!

* Read the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
* Check out [CONTRIBUTING.md](CONTRIBUTING.md) for:

  * Branching strategy.
  * Code style (Python + C++).
  * How to run tests.
  * How to propose new features or backends.

Ideas for contributions:

* Unity client implementation.
* Mouth/lip-sync integration.
* Additional LLM backends (OpenAI, Anthropic, etc.).
* RAG integration with local documents.
* Better VR UX / interaction patterns.

---

## 📄 License

* **Code:** [Apache 2.0](LICENSE) – do whatever you want with attribution.
* **Scifi Girl v.01 avatar:** CC BY-NC-SA – **non-commercial only** (see `assets/avatars/scifi_girl_v01/README.md`).

When in doubt, treat the code and the avatar as having **separate licenses**. Replace the avatar for any commercial or redistributable product.

---

## 🔗 Related Projects

* [Ollama](https://ollama.ai/)
* [IBM watsonx.ai](https://www.ibm.com/watsonx)
* [Chatterbox TTS](https://github.com/rsxdalv/chatterbox)
* [Unreal Engine](https://www.unrealengine.com/)
* [Llama-Unreal (reference inspiration)](https://github.com/ggerganov/llama.cpp) *(via Unreal integrations)*

---

VRSecretary is meant to be a **solid starting point**. Clone it, run it, break it, and then shape it into your own AI-powered VR experience. ✨
