# VRSecretary Overview

VRSecretary is a **reference implementation** for building AI-powered characters
in virtual reality. It combines:

- A **VR front-end** built with **Unreal Engine 5.3+**
- A **Python / FastAPI backend** that orchestrates LLMs and TTS
- Support for **local** and **cloud** LLM providers (Ollama, IBM watsonx.ai)
- High-quality **speech synthesis** via Chatterbox TTS
- An Unreal plugin (`VRSecretary`) that exposes a simple Blueprint interface

The goal is to give you a **realistic but approachable starting point** for
shipping AI assistants in VR, not just a toy demo.

---

## 1. High-Level Architecture

At a high level VRSecretary looks like this:

```text
+---------------------+      HTTP      +-------------------------+
|   Unreal Engine     |  <---------->  | FastAPI Gateway         |
|   VR Front-end      |                | (Python)                |
|                     |                |                         |
|  - VRSecretary      |                |  - /api/vr_chat         |
|    Component        |                |  - LLM clients          |
|  - Avatar + UI      |                |  - TTS client           |
+---------------------+                +-------------------------+
                                              |
                                              |
                                        +-----+-----+
                                        |  LLMs     |
                                        | (Ollama,  |
                                        |  watsonx) |
                                        +-----------+
                                              |
                                              |
                                        +-----+-----+
                                        |  TTS      |
                                        | Chatterbox|
                                        +-----------+
```

There is also an **in-engine path** for fully local models:

- Unreal → **Llama-Unreal** plugin → **llama.cpp**

This bypasses HTTP and keeps everything inside the game process.

---

## 2. Backend Modes

The Unreal plugin exposes four backend modes (enum `EVRSecretaryBackendMode`):

1. **Gateway (Ollama)**  
   - UE → FastAPI → Ollama → Chatterbox → UE  
   - Returns text **and** base64-encoded WAV audio.

2. **Gateway (watsonx.ai)**  
   - UE → FastAPI → IBM watsonx.ai → Chatterbox → UE  
   - Same interface as `Gateway (Ollama)`, different LLM provider.

3. **DirectOllama**  
   - UE → OpenAI-style `/v1/chat/completions` endpoint (e.g. Ollama with an OpenAI proxy).  
   - Returns **text-only** (no TTS).  
   - This path is engine-agnostic: any client that speaks the OpenAI Chat Completions
     protocol can use it.

4. **LocalLlamaCpp**  
   - UE → Llama-Unreal plugin (`ULlamaComponent`) → local llama.cpp model.  
   - No HTTP, everything is in-process.  
   - Returns **text-only** by default; you can add TTS by calling the gateway just for
     audio if desired.

The engine-agnostic API exposed by the gateway is `/api/vr_chat`, which handles
LLM + TTS and hides provider-specific details from the client.

---

## 3. Components & Responsibilities

### 3.1 Unreal Side

**VRSecretaryComponent (C++ / Blueprint)**

- Accepts user text + generation config (`FVRSecretaryChatConfig`).
- Chooses a backend mode (global default + per-component override).
- Sends HTTP requests for Gateway/DirectOllama modes.
- Talks to `ULlamaComponent` for LocalLlamaCpp mode.
- Exposes events:
  - `OnAssistantResponse(AssistantText, AudioBase64)`
  - `OnError(ErrorMessage)`

**Avatar & UI**

- A separate Blueprint (e.g. `BP_SecretaryAvatar`) is responsible for:
  - Displaying subtitles.
  - Playing audio returned from the backend.
  - Handling animation, facial expressions, etc.

This separation keeps the plugin **framework-level**, not tied to any specific avatar.

### 3.2 Backend Side (FastAPI)

**Gateway service** (`backend/gateway/vrsecretary_gateway`):

- `/api/vr_chat`:
  - Applies the **Ailey** system prompt and past history for the session.
  - Calls the selected LLM provider (Ollama or watsonx.ai).
  - Sends the assistant reply to Chatterbox TTS.
  - Returns text and audio in a small JSON envelope.

- `llm/`:
  - `OllamaClient`: talks to Ollama using an OpenAI-style `/v1/chat/completions` API.
  - `WatsonxClient`: talks to IBM watsonx.ai.

- `tts/`:
  - `ChatterboxClient`: sends text to Chatterbox and receives WAV bytes.

- `models/`:
  - Pydantic schemas for requests / responses.
  - A simple in-memory session store for chat history.

---

## 4. Design Principles

VRSecretary is designed around a few key principles:

1. **Engine-agnostic API**  
   The `/api/vr_chat` endpoint is the main contract. Any engine (Unreal, Unity, etc.) can integrate by calling it.

2. **OpenAI-style LLM interface**  
   Internally the LLM clients use the `/v1/chat/completions` protocol. This makes it easy
   to swap Ollama for another provider without rewriting your engine code.

3. **Pluggable TTS**  
   TTS is abstracted into its own client (Chatterbox). You can swap it out or add multiple
   voices by changing the backend only.

4. **Separation of concerns**  
   - Unreal handles rendering, VR input, and moment-to-moment gameplay.  
   - The backend handles persona, history, LLM selection, and TTS.  
   - Llama-Unreal handles local llama.cpp models.

5. **Patchable / Upgradable Unreal Plugin**  
   A single script (`tools/scripts/apply_vrsecretary_patch.sh`) can rewrite the Unreal
   plugin to the latest structure, ensuring consistent behavior across projects.

---

## 5. When to Use Which Mode

- Use **Gateway (Ollama)** when you want the full feature set with minimal engine code:
  - Persona and memory handled in Python.
  - Text and audio in one call.
  - Easy to extend with RAG, tools, or different providers.

- Use **Gateway (watsonx.ai)** when you need enterprise-grade LLMs or on-prem deployments.

- Use **DirectOllama** when you want:
  - No Python backend.
  - A simple, text-only conversation loop with an OpenAI-compatible server.

- Use **LocalLlamaCpp (Llama-Unreal)** when you need:
  - Completely offline inference.
  - Maximum control over latency and memory.
  - No external services except what you choose to add (e.g., local TTS).

---

## 6. Where to Go Next

- **`architecture.md`** – deeper dive into the data flow and components.
- **`engine-agnostic-api.md`** – exact API shapes (paths, JSON, error codes).
- **`unreal-integration.md`** – step-by-step Unreal setup and Blueprint wiring.
- **`persona-ailey.md`** – how the Ailey persona works and how to customize it.
- **`deployment-guide.md`** – dev and production deployment patterns (Docker, envs, scaling).
