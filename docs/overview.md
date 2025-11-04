# VRSecretary Overview

VRSecretary is a reference implementation and architecture for building **AI-powered VR assistants**.

It connects:

- A **VR front-end** built with Unreal Engine 5 (VR template + avatar + audio).
- A **Python FastAPI backend** that orchestrates LLMs and TTS.
- **Local or cloud LLMs** such as Ollama (Llama 3, Mistral, Granite, etc.) and IBM watsonx.ai.
- A **TTS engine** (Chatterbox) that generates WAV audio for spoken responses.

The system is designed to be:

- **Engine-agnostic** – any client that can perform HTTP requests can use the backend.
- **Modular** – each component (LLM, TTS, VR front-end) can be swapped or extended.
- **Production-minded** – clear separation of concerns, configuration via environment variables, and Docker support.
- **Educational** – documentation and examples show how to integrate all parts, especially Unreal Engine.

## Core Components

1. **Unreal Engine 5 Front-End**
   - A VR-ready project based on the UE5 VR template.
   - Uses the `VRSecretary` plugin (C++ ActorComponent) to communicate with the backend.
   - Features a VR-friendly user experience: VR motion controllers, teleport, avatar, and subtitles.

2. **`VRSecretary` Unreal Plugin**
   - Provides `UVRSecretaryComponent` to send text to the backend and receive responses + audio.
   - Configured via **Project Settings → Plugins → VRSecretary**.
   - Supports multiple backend modes (Gateway, Direct Ollama, Local Llama.cpp stub).

3. **FastAPI Gateway Backend**
   - Exposed as a single `/api/vr_chat` endpoint (plus `/health`).
   - Implements session handling, prompt building, and LLM/TTS orchestration.
   - Uses a pluggable LLM client abstraction (`BaseLLMClient`) with concrete implementations for:
     - **Ollama** (local OpenAI-compatible API).
     - **IBM watsonx.ai** (cloud LLM SDK).

4. **LLM Backends**
   - **Ollama**: runs locally, supports various models (Llama 3, Mistral, etc.).
   - **Watsonx**: enterprise cloud models (Granite, Llama hosted by IBM, etc.).
   - Future backends (OpenAI, Anthropic, llama.cpp direct) can be added via the same interface.

5. **Chatterbox TTS**
   - Self-hosted TTS engine that exposes an OpenAI-style `/v1/audio/speech` endpoint.
   - Converts assistant text into WAV audio.
   - Results are returned as base64-encoded WAV data to Unreal.

6. **Persona “Ailey”**
   - A default system prompt defines Ailey, a professional but friendly VR secretary.
   - Persona is fully configurable in the backend (system prompt) and documented in `persona-ailey.md`.

## Typical Interaction Flow

1. User in VR speaks or types a message.
2. Unreal (via `UVRSecretaryComponent`) sends JSON to `/api/vr_chat` on the backend.
3. FastAPI builds a chat context (system + (optional) history + user message).
4. LLM client (Ollama or watsonx.ai) generates assistant text.
5. TTS client (Chatterbox) converts text to WAV audio.
6. Backend returns:
   - `assistant_text`
   - `audio_wav_base64`

7. Unreal decodes/plays the audio and displays subtitles above the avatar.
8. The user sees & hears the AI secretary respond in VR.

## Use Cases

- Virtual receptionist or office assistant in VR.
- VR training/tutoring assistant.
- AI-powered NPCs in games, simulations, or experiences.
- Exhibition/museum guides.
- Any context where natural language + VR presence is valuable.

## Non-Goals

- VRSecretary itself is **not a product**; it is a **reference implementation**.
- It is not optimized out-of-the-box for high concurrency or multi-tenant usage.
- It does not fully solve voice activity detection, lip-sync, or complex animation (these are left for you to integrate).

For architecture details, see `architecture.md`. For deployment and installation, see `deployment-guide.md`.
