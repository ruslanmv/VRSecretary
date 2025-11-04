# VRSecretary Architecture

This document describes the **internal architecture** of VRSecretary and how the
different services and plugins interact. It is meant to complement the high-level
overview in `overview.md`.

---

## 1. Top-Level Diagram

```text
                    +-------------------------------+
                    |         Unreal Engine         |
                    |         (VR Front-end)        |
                    |                               |
                    |  +-------------------------+  |
User in VR  <-----> |  | VRSecretaryComponent    |  |
(controllers, mic)  |  |                         |  |
                    |  +-------------------------+  |
                    |        ^           ^          |
                    |        |           |          |
                    +--------|-----------|----------+
                             |           |
            Gateway / Direct |           | LocalLlamaCpp
             (HTTP)          |           | (in-process)
                             |           |
                  +----------v-----------v---------+
                  |         Backends               |
                  |                                |
                  |  +--------------------------+  |
                  |  | FastAPI Gateway          |  |
                  |  |  - /api/vr_chat          |  |
                  |  |  - LLM clients           |  |
                  |  |  - TTS client            |  |
                  |  +--------------------------+  |
                  |                |               |
                  |                | LLM calls     |
                  |                v               |
                  |   +------------------------+   |
                  |   |  LLM Providers         |   |
                  |   |  - Ollama (OpenAI)     |   |
                  |   |  - IBM watsonx.ai      |   |
                  |   +------------------------+   |
                  |                |               |
                  |                | TTS calls     |
                  |                v               |
                  |   +------------------------+   |
                  |   |  TTS Provider          |   |
                  |   |  - Chatterbox          |   |
                  |   +------------------------+   |
                  +--------------------------------+
```

In addition, the **Llama-Unreal** plugin provides an in-engine llama.cpp backend,
which VRSecretary uses for the `LocalLlamaCpp` mode.

---

## 2. Unreal Engine Layer

### 2.1 VRSecretaryComponent

The `UVRSecretaryComponent` is the main integration point between Unreal and the
AI backends.

**Responsibilities:**

- Provide a Blueprint/C++ function to send the user’s message:

  ```cpp
  void SendUserText(const FString& UserText, const FVRSecretaryChatConfig& Config);
  void SendUserTextWithDefaultConfig(const FString& UserText);
  ```

- Resolve the effective backend mode:

  - Global default from `UVRSecretarySettings`
  - Optional per-component override

- Dispatch to one of three internal paths:

  - `SendViaGateway(...)` – Gateway (Ollama / watsonx)
  - `SendViaDirectOllama(...)` – Direct OpenAI-style `/v1/chat/completions`
  - `SendViaLocalLlamaCpp(...)` – Local llama.cpp via `ULlamaComponent`

- Raise events back to Blueprint:

  - `OnAssistantResponse(AssistantText, AudioBase64)`
  - `OnError(ErrorMessage)`

**Not responsible for:**

- Rendering avatars or UI
- Low-level HTTP configuration beyond basic timeout and URL
- Persona or long-term memory shaping (handled by backend or Llama-Unreal)

### 2.2 VRSecretarySettings (Developer Settings)

`UVRSecretarySettings` is responsible for global plugin configuration:

- `GatewayUrl` – base URL of FastAPI gateway (e.g. `http://localhost:8000`).
- `BackendMode` – default backend mode for all components.
- `HttpTimeout` – global HTTP timeout in seconds.
- `DirectOllamaUrl` – base URL for OpenAI-style endpoint (e.g. `http://localhost:11434`).
- `DirectOllamaModel` – default model name for DirectOllama.

These settings are stored in `DefaultGame.ini` and editable in
**Project Settings → Plugins → VRSecretary**.

### 2.3 Llama-Unreal Integration (LocalLlamaCpp)

When `BackendMode == LocalLlamaCpp` (or the component override says so):

- `SendViaLocalLlamaCpp(...)` looks for a `ULlamaComponent`:
  - Uses the explicit `LlamaComponent` pointer (if assigned), else
  - Searches the owning Actor (`GetOwner()->FindComponentByClass<ULlamaComponent>()`).

- It binds to `OnResponseGenerated` on the `ULlamaComponent` and sends a `FLlamaChatPrompt`.

- Once a response is generated, `HandleLlamaResponse(...)` is invoked and the text is
  forwarded to Blueprint via `OnAssistantResponse(AssistantText, "")`.

This design keeps VRSecretary’s llama-specific logic minimal and delegates the details
(loading models, templates, embeddings, vector DB, etc.) to the Llama-Unreal plugin.

---

## 3. FastAPI Gateway Layer

The gateway lives under `backend/gateway/vrsecretary_gateway`. Its main job is
to expose a stable, engine-agnostic API while hiding provider-specific details.

### 3.1 API: /health

```http
GET /health
```

**Use:** Simple health check for monitoring / startup.

**Response:**

```json
{"status": "ok"}
```

### 3.2 API: /api/vr_chat

```http
POST /api/vr_chat
Content-Type: application/json
```

**Request body:**

```json
{
  "session_id": "string",
  "user_text": "string"
}
```

- `session_id` – opaque identifier provided by the client, used to look up
  past messages for conversational continuity.
- `user_text` – what the user just said / typed in the VR experience.

**Processing steps:**

1. Validate body using Pydantic model (`VRChatRequest`).
2. Retrieve or create a chat session for `session_id` in `session_store`.
3. Build a list of messages (in OpenAI chat format):

   - `system` message – Ailey’s persona prompt (from `persona-ailey.md`).
   - `assistant` / `user` turns – prior conversation from the session.
   - `user` – the new `user_text`.

4. Choose an LLM client based on settings:

   - `OllamaClient` if `MODE=offline_local_ollama`
   - `WatsonxClient` if `MODE=online_watsonx`

5. Call the LLM client with the messages, obtain an `assistant` reply string.

6. Call `ChatterboxClient` with that reply to synthesize WAV audio.

7. Save the new assistant message into the session history.

8. Return a `VRChatResponse`:

   ```json
   {
     "assistant_text": "string",
     "audio_wav_base64": "string"
   }
   ```

   - `assistant_text` – plain text for subtitles / logs.
   - `audio_wav_base64` – WAV bytes in base64 for playback.

### 3.3 LLM Clients

**OllamaClient**

- Talks to an OpenAI-compatible `/v1/chat/completions` endpoint.
- Request body includes:
  - `model`
  - `messages`
  - generation parameters (temperature, max tokens, etc.).
- Used by the gateway and by any engine that chooses the same protocol.

**WatsonxClient**

- Wraps IBM watsonx.ai APIs.
- Responsible for:
  - Authentication via API key / IAM.
  - Translating OpenAI-style messages into watsonx’s format.
  - Handling parameters like max tokens, temperature.

### 3.4 TTS Client (Chatterbox)

**ChatterboxClient** encapsulates calls to Chatterbox TTS:

- `POST /v1/audio/speech`
- Inputs:
  - `input` (text)
  - Optional tuning parameters (temperature, cfg_weight, exaggeration, etc.).
- Outputs:
  - WAV bytes

The gateway base64-encodes the WAV bytes before returning to the engine.

---

## 4. Data Flow Examples

### 4.1 Gateway (Ollama) Mode

1. User speaks / types in VR.
2. `VRSecretaryComponent.SendUserText(...)` is called with backend mode = GatewayOllama.
3. Plugin sends `POST /api/vr_chat` to the gateway.
4. Gateway calls `OllamaClient` → local LLM → Chatterbox.
5. Gateway responds with text + audio.
6. Plugin fires `OnAssistantResponse`.
7. Blueprint updates subtitles and plays audio near the avatar.

### 4.2 DirectOllama Mode

1. User speaks / types in VR.
2. `VRSecretaryComponent.SendUserText(...)` backend mode = DirectOllama.
3. Plugin sends `POST {DirectOllamaUrl}/v1/chat/completions`.
4. OpenAI-style server returns `choices[0].message.content`.
5. Plugin fires `OnAssistantResponse(AssistantText, "")`.
6. Blueprint uses text only (no audio) or calls a separate TTS service if desired.

### 4.3 LocalLlamaCpp Mode

1. User speaks / types in VR.
2. `VRSecretaryComponent.SendUserText(...)` backend mode = LocalLlamaCpp.
3. Plugin sends a prompt to `ULlamaComponent` via `InsertTemplatedPromptStruct`.
4. Llama-Unreal runs llama.cpp locally and streams / aggregates tokens into a full reply.
5. Llama-Unreal fires `OnResponseGenerated` with the final text.
6. Plugin forwards it to Blueprint via `OnAssistantResponse(AssistantText, "")`.

---

## 5. Extensibility

You can extend the architecture in a number of ways:

- **New LLM providers**: Add a new client implementing the same interface as `OllamaClient`
  and `WatsonxClient`, then add a new gateway mode and Unreal backend mode.
- **RAG (Retrieval-Augmented Generation)**: Enhance the gateway with vector search over
  documents, injecting relevant context into the messages.
- **Tools / function calling**: Allow the LLM to schedule calendar events, send emails, etc.,
  by adding a tool layer in the gateway.
- **Additional TTS engines**: Add more TTS clients and let Ailey switch voices at runtime.

The separation between Unreal, gateway, LLM providers, and TTS makes these changes mostly
localized to one layer at a time.

---

For API details and payload shapes, see `engine-agnostic-api.md`. For Unreal
integration steps and blueprints, see `unreal-integration.md`.
