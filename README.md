# VRSecretary

🤖 **AI-Powered VR Secretary** – An open-source reference implementation that combines **Unreal Engine 5 VR**, **local/cloud LLMs**, and **high-quality TTS** to bring a fully interactive virtual secretary into VR.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Unreal Engine](https://img.shields.io/badge/Unreal-5.3+-blue.svg)](https://www.unrealengine.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org/)

---

## ✨ What Is VRSecretary?

VRSecretary is a **production-ready reference architecture** and implementation for building AI-powered VR characters:

- Frontend in **Unreal Engine 5** (VR-ready).
- Backend in **Python / FastAPI**.
- LLM via **Ollama** (local) or **IBM watsonx.ai** (cloud).
- TTS via **Chatterbox** (self-hosted, OpenAI-style).

It ships with:

- A **VR secretary avatar** (Scifi Girl v.01 – non-commercial demo, GLB ready to import).
- An **Unreal plugin** (`VRSecretary`) exposing a simple Blueprint-friendly component.
- A **gateway backend** that exposes a clean `/api/vr_chat` HTTP endpoint.
- A **direct Ollama mode** (Unreal → Ollama, no Python), plus a **llama.cpp stub** for in-engine integration later.
- Documentation to extend the same API to other engines (e.g., Unity).

---

## 🌟 Key Features

- **VR-native UX**
  - Built around UE5’s VR template (controllers, teleport, VR camera).
  - Uses a 3D avatar, audio, and subtitles for an immersive conversational assistant.

- **Flexible LLM Backends**
  - **Offline (default):** [Ollama](https://ollama.ai/) on your machine (e.g. `llama3`, Granite, Mistral).
  - **Online (optional):** [IBM watsonx.ai](https://www.ibm.com/watsonx) via official SDK/API.

- **High-Quality Voice**
  - [Chatterbox TTS](https://github.com/rsxdalv/chatterbox) for natural-sounding speech.
  - Text → WAV audio streamed back to Unreal and played at runtime.

- **Multiple Backend Modes in Unreal**
  - **Gateway (Ollama / watsonx)** – UE → FastAPI → LLM → TTS → UE (full text + audio).
  - **Direct Ollama** – UE → Ollama (OpenAI-style chat completions, text only).
  - **Local Llama.cpp (stub)** – ready for in-engine llama.cpp binding via `ThirdParty/LlamaCpp`.

- **Modular, Engine-Agnostic Architecture**
  - Clean REST API (`/api/vr_chat`) that any engine or app can call.
  - Unreal plugin is only one possible client; Unity and others can reuse the same backend.

- **Sample Avatar Included & Ready to Use**
  - **Scifi Girl v.01** GLB included under CC BY-NC-SA for non-commercial use.
  - Ready to import and hook up to the secretary Blueprint in the demo project.

- **Production-Oriented Layout**
  - Clear separation of backend, engine plugins, assets, and tools.
  - Configurable via `.env` (backend) and Project Settings (Unreal).
  - Dockerized backend, load test scripts, and extensible plugin architecture.

---

## 🧬 Repository Structure

High-level layout:

```text
VRSecretary/
├── assets/
│   └── avatars/
│       └── scifi_girl_v01/
│           ├── scifi_girl_v.01.glb          # Sample GLB (non-commercial demo)
│           ├── README.md                    # License & usage info
│           └── DOWNLOAD_INSTRUCTIONS.txt
│
├── backend/
│   ├── gateway/                             # FastAPI backend (LLM + TTS gateway)
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   └── vrsecretary_gateway/
│   │       ├── main.py                      # FastAPI app entrypoint
│   │       ├── config.py                    # Pydantic settings
│   │       ├── api/                         # /health, /api/vr_chat
│   │       ├── llm/                         # Ollama + watsonx.ai clients
│   │       ├── tts/                         # Chatterbox TTS client
│   │       └── models/                      # Pydantic schemas & session store
│   └── docker/
│       ├── Dockerfile.gateway
│       ├── docker-compose.dev.yml
│       └── env.example
│
├── engine-plugins/
│   ├── unreal/
│   │   ├── VRSecretary.uplugin              # Unreal plugin descriptor
│   │   └── Source/VRSecretary/
│   │       ├── VRSecretary.Build.cs
│   │       ├── Public/
│   │       │   ├── VRSecretaryComponent.h   # Main C++ component (Blueprint-ready)
│   │       │   ├── VRSecretarySettings.h    # Project settings (Gateway URL, modes, etc.)
│   │       │   ├── VRSecretaryChatTypes.h   # Enums, config structs, delegates
│   │       │   └── VRSecretaryLog.h
│   │       └── Private/
│   │           ├── VRSecretaryModule.cpp
│   │           ├── VRSecretaryComponent.cpp
│   │           ├── VRSecretarySettings.cpp
│   │           ├── VRSecretaryLog.cpp
│   │           └── (optional llama.cpp glue)
│   │   └── ThirdParty/
│   │       └── LlamaCpp/
│   │           ├── Include/                 # Place llama.cpp headers here
│   │           └── Lib/                     # Place built libs here
│   └── unity/                               # (Future) Unity client skeleton
│
├── samples/
│   ├── unreal-vr-secretary-demo/            # Example UE5 VR project
│   │   ├── VRSecretaryDemo.uproject
│   │   ├── Config/
│   │   └── Content/                         # Blueprints, UI, secretary avatar BP, etc.
│   └── backend-notebooks/
│       └── prototype-calls.ipynb            # Jupyter prototyping
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
│   │   ├── apply_vrsecretary_patch.sh       # Plugin patch/upgrade script
│   │   ├── start_local_stack.sh             # Convenience stack startup (optional)
│   │   └── generate_openapi_client.sh
│   └── perf/
│       ├── load_test_vr_chat.k6.js
│       └── profiling_notes.md
│
├── .github/                                 # CI/CD workflows, issue templates
├── LICENSE
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
└── README.md                                # (This file)
````

For plugin-specific usage, see
`engine-plugins/unreal/VRSecretary/README.md`.

---

## 🧩 System Requirements

**Host machine:**

* **OS:** Windows 10/11 (recommended for Unreal). Linux/macOS fine for backend-only.
* **CPU:** Modern quad-core or better.
* **RAM:** 16 GB minimum (32 GB recommended for local LLMs).
* **GPU:** NVIDIA GPU with CUDA is highly recommended for Ollama + Chatterbox acceleration.

**Software:**

* **Unreal Engine:** 5.3+ (with C++ and VR templates).
* **Visual Studio 2022** (Windows) with *Game development with C++* workload.
* **Python:** 3.10+.
* **Docker:** optional (for running backend via compose).
* **Node + k6:** optional (for load testing).

---

## 🚀 End-to-End Quick Start

This flow gets you from clone → VR secretary answering you in VR.

### 0. Clone the Repository

```bash
git clone https://github.com/ruslanmv/VRSecretary.git
cd VRSecretary
```

> Update the URL if you’ve forked or renamed the repo.

---

### 1. Backend: FastAPI Gateway

#### 1.1 Create and activate a virtual environment

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
# Optional watsonx support:
# pip install -e ".[watsonx]"
```

#### 1.3 Configure environment

Copy the template:

```bash
cp ../docker/env.example .env
```

Open `.env` and set at least:

```env
MODE=offline_local_ollama

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

CHATTERBOX_URL=http://localhost:4123
```

For **watsonx.ai**, switch and fill the credentials:

```env
MODE=online_watsonx

WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_PROJECT_ID=your-project-id
WATSONX_MODEL_ID=ibm/granite-13b-chat-v2
WATSONX_API_KEY=your-api-key
```

#### 1.4 Run the gateway

```bash
uvicorn vrsecretary_gateway.main:app --reload --host 0.0.0.0 --port 8000
```

Check:

* API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
* Health: [http://localhost:8000/health](http://localhost:8000/health)

---

### 2. LLM: Start Ollama

Install from [https://ollama.ai/](https://ollama.ai/).

Then in a terminal:

```bash
# Run Ollama server
ollama serve
```

In a second terminal:

```bash
# Download a model
ollama pull llama3
```

Confirm it’s available:

```bash
curl http://localhost:11434/v1/models
```

Ensure `.env` has `OLLAMA_MODEL=llama3` (or whichever you use).

---

### 3. TTS: Start Chatterbox

Install [Chatterbox](https://github.com/rsxdalv/chatterbox) per its README, then:

```bash
chatterbox-server --port 4123
```

Quick sanity check:

```bash
curl -X POST http://localhost:4123/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello from Ailey.", "temperature": 0.6, "cfg_weight": 0.5, "exaggeration": 0.35}' \
  --output test.wav
```

Play `test.wav` to verify audio.

---

### 4. Sanity Check: Backend `/api/vr_chat`

With gateway + Ollama + Chatterbox running:

```bash
curl -X POST http://localhost:8000/api/vr_chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-123", "user_text": "Hello Ailey, who are you?"}'
```

Expected response:

```json
{
  "assistant_text": "Hi! I'm Ailey, your VR secretary...",
  "audio_wav_base64": "UklGRiQAAABXQVZF..."
}
```

If this works, Unreal can use the same endpoint.

---

### 5. Unreal: Sample Project (Recommended First Run)

1. In Explorer/Finder, go to:

   ```text
   VRSecretary/samples/unreal-vr-secretary-demo/
   ```

2. Right-click `VRSecretaryDemo.uproject` → **Generate Visual Studio project files**.

3. Open `VRSecretaryDemo.uproject` with Unreal Engine 5.3+.

4. Let Unreal build the C++ modules (including the `VRSecretary` plugin).

5. In the editor:

   * **Edit → Plugins** → search for **VRSecretary** and confirm it’s **enabled**.
   * **Edit → Project Settings → Plugins → VRSecretary**:

     * Gateway URL: `http://localhost:8000`
     * Backend Mode: **Gateway (Ollama)** (or **Gateway (watsonx)** if using cloud mode).
     * Timeout: ~60 seconds is safe while experimenting.

6. Avatar:

   * Sample GLB is at `assets/avatars/scifi_girl_v01/scifi_girl_v.01.glb`.
   * Import it into the demo project’s Content folder (e.g., `/Game/Characters/ScifiGirl/`).
   * Use or retarget the sample `BP_SecretaryAvatar` to this skeletal mesh if needed.

7. Connect your VR headset and hit **Play → VR Preview**.

Use the included Blueprint (`BP_VRSecretaryManager`) input actions (e.g., controller + keyboard) to send text. You should see and hear Ailey respond.

---

### 6. Unreal: Using the Plugin in Your Own Project

You can integrate VRSecretary into any UE 5.3+ C++ project.

1. Copy the plugin:

   ```bash
   cd VRSecretary
   mkdir -p /path/to/YourUEProject/Plugins
   cp -r engine-plugins/unreal/VRSecretary /path/to/YourUEProject/Plugins/
   ```

2. Right-click your `.uproject` → **Generate Visual Studio project files**.

3. Open and build the project in Visual Studio (**Development Editor / Win64**).

4. In Unreal:

   * **Edit → Plugins** → enable **VRSecretary** if not already.
   * **Edit → Project Settings → Plugins → VRSecretary**:

     * Set **Gateway URL**, **Backend Mode**, and **HTTP Timeout**.

5. In your Blueprint:

   * Add a **VRSecretaryComponent** to an Actor (e.g., VR manager or Player Pawn).
   * Bind to:

     * `OnAssistantResponse(AssistantText, AudioBase64)` → update subtitles, trigger avatar voice.
     * `OnError(ErrorMessage)` → show user feedback.

6. Call:

   ```cpp
   SendUserText(UserText, ChatConfig)
   ```

   from Blueprint (e.g., on button press). The component will:

   * Use **Gateway** mode: call the FastAPI backend → LLM → TTS → return text + base64 audio.
   * Use **DirectOllama** mode: call Ollama directly → return text only.
   * Use **LocalLlamaCpp** (stub): currently logs and falls back to Gateway; ready for in-engine llama.cpp once you wire up `ThirdParty/LlamaCpp`.

For detailed, step-by-step integration (Blueprint graphs, widget setup, etc.), see:
`docs/unreal-integration.md` and `engine-plugins/unreal/VRSecretary/README.md`.

---

## ⚙️ Backend & Plugin Configuration Summary

### Backend (`backend/gateway/.env`)

Key options:

```env
# Core mode: offline (Ollama) or online (watsonx.ai)
MODE=offline_local_ollama        # or online_watsonx

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

### Unreal Plugin Settings (Project Settings → Plugins → VRSecretary)

* **Gateway URL** – e.g. `http://localhost:8000`
* **HTTP Timeout** – e.g. `60.0`
* **Backend Mode** (`EVRSecretaryBackendMode`):

  * Gateway (Ollama)
  * Gateway (watsonx.ai)
  * DirectOllama
  * LocalLlamaCpp (stub)
* **Direct Ollama URL** – e.g. `http://localhost:11434`
* **Direct Ollama Model** – e.g. `llama3`

You can also override the backend mode per component via `BackendModeOverride` on `VRSecretaryComponent`.

---

## 🧠 AI Persona: Ailey

The default secretary persona **Ailey** is defined in the backend as a system prompt. She is:

* Professional yet friendly.
* Good at planning, drafting, and structuring work.
* VR-aware (references the “virtual office” context).
* Concise (responses are spoken aloud).

You can customize Ailey by editing `SYSTEM_PROMPT` in:

```text
backend/gateway/vrsecretary_gateway/api/vr_chat_router.py
```

More persona variants (formal, casual, legal, technical, etc.) are documented in:
`docs/persona-ailey.md`.

---

## 🎭 Avatar: Scifi Girl v.01 (Non-Commercial Demo)

The sample avatar used in the demo:

* **Name:** *Scifi Girl v.01*
* **Author:** patrix
* **Source:** [https://sketchfab.com/3d-models/scifi-girl-v01-96340701c2ed4d37851c7d9109eee9c0](https://sketchfab.com/3d-models/scifi-girl-v01-96340701c2ed4d37851c7d9109eee9c0)
* **License:** [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)

In this repo:

```text
assets/avatars/scifi_girl_v01/
  ├── scifi_girl_v.01.glb          # Sample 3D model (non-commercial reference)
  ├── README.md                    # Detailed license & attribution
  └── DOWNLOAD_INSTRUCTIONS.txt
```

**Important license notes:**

* This avatar is **non-commercial only**.
* You **must not** use it in commercial products without explicit permission from the creator.
* For commercial use:

  * Replace with a marketplace avatar (Unreal Marketplace, Sketchfab commercial asset, etc.).
  * Or use a CC0/public domain model.
  * Or create/commission your own model.

The avatar is **licensed separately** from the VRSecretary code.

---

## 🛠️ Development, Docker & Testing

### Dockerized Backend

From the repo root:

```bash
cd backend/docker
docker-compose -f docker-compose.dev.yml up
```

This will:

* Start **Ollama** in a container.
* Build & run the **gateway** container.

Chatterbox is typically run on the host for GPU access:

```bash
chatterbox-server --port 4123
```

The compose file already uses `CHATTERBOX_URL=http://host.docker.internal:4123`.

### Backend Tests

From `backend/gateway`:

```bash
pytest
# or
pytest --cov=vrsecretary_gateway --cov-report=html
```

### Load Testing

From `tools/perf`:

```bash
k6 run load_test_vr_chat.k6.js
```

This load-tests `/api/vr_chat` to measure latency/throughput under concurrent users.

---

## 🧱 Architecture Snapshot

Very briefly:

**Unreal (VR Frontend)**

* `VRSecretaryComponent` (C++/Blueprint):

  * Accepts `UserText` + `FVRSecretaryChatConfig`.
  * Chooses backend mode (Gateway / DirectOllama / LocalLlamaCpp).
  * Sends HTTP requests and exposes two events:

    * `OnAssistantResponse(AssistantText, AudioBase64)`
    * `OnError(ErrorMessage)`
* Blueprint manager (`BP_VRSecretaryManager`) orchestrates:

  * User input (VR controllers, widgets).
  * Forwarding to `VRSecretaryComponent`.
  * Driving the avatar (`BP_SecretaryAvatar`) with text + audio.

**Gateway (FastAPI Backend)**

* `POST /api/vr_chat`:

  * Validates `VRChatRequest` (`session_id`, `user_text`).
  * Assembles messages (system prompt + user + optional history).
  * Calls the selected LLM (Ollama or watsonx.ai) via `BaseLLMClient`.
  * Sends the LLM response text to **Chatterbox** for speech synthesis.
  * Returns `VRChatResponse { assistant_text, audio_wav_base64 }`.

Detailed diagrams and explanations are in:
`docs/architecture.md` and `docs/engine-agnostic-api.md`.

---

## 🤝 Contributing

Contributions are welcome!

* Please read the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
* See [CONTRIBUTING.md](CONTRIBUTING.md) for:

  * Branching & workflow.
  * Coding standards (Python, C++, Blueprint).
  * How to run tests & style checks.

Ideas for contributions:

* Full **Unity** client implementation.
* In-engine **llama.cpp** integration using `ThirdParty/LlamaCpp`.
* RAG (Retrieval-Augmented Generation) with local docs.
* Additional LLM backends (OpenAI, Anthropic, etc.).
* Better VR UX, gestures, and spatial interactions.

---

## 📄 License

* **Code:** [Apache 2.0](LICENSE) – you can use, modify, and ship it (with attribution).
* **Scifi Girl v.01 avatar:** CC BY-NC-SA – **non-commercial only** (see `assets/avatars/scifi_girl_v01/README.md`).

Treat code and assets as having **separate licenses**. For any commercial product, replace or remove non-commercial assets.

---

## 🔗 Related Projects

* [Ollama](https://ollama.ai/)
* [IBM watsonx.ai](https://www.ibm.com/watsonx)
* [Chatterbox TTS](https://github.com/rsxdalv/chatterbox)
* [Unreal Engine](https://www.unrealengine.com/)
* [llama.cpp](https://github.com/ggerganov/llama.cpp) (for potential in-engine integration)

---

VRSecretary is designed as a **solid, realistic starting point** for AI characters in VR.
Run it, explore it, and then bend it into whatever virtual assistant your world needs. ✨


