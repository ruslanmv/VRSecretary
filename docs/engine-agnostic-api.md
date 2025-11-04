# Engine-Agnostic API Reference

This document describes the HTTP API exposed by the VRSecretary backend that any
engine (Unreal, Unity, etc.) can use. The design is intentionally small and
stable so you can evolve your front-end independently.

The primary engine-facing endpoint is:

- `POST /api/vr_chat` – combined LLM + TTS call for the VR secretary.

Internally, the gateway also speaks **OpenAI-style** to LLM providers
(e.g. `/v1/chat/completions`), but that protocol is considered an implementation
detail rather than a public API of VRSecretary itself.

---

## 1. Base URL

For development, the default base URL is:

```text
http://localhost:8000
```

The actual host/port can be configured via environment variables or the
Docker compose configuration.

All paths in this document are relative to this base URL.

---

## 2. Health Check

### 2.1 `GET /health`

Simple liveness probe.

**Request:**

```http
GET /health
```

**Response:**

```json
{"status": "ok"}
```

Use this for:

- Manual debugging: check that the gateway is running.
- Liveness checks in Docker / Kubernetes.

---

## 3. VR Chat Endpoint

### 3.1 `POST /api/vr_chat`

This is the main endpoint used by the Unreal plugin and intended for other
engines. It wraps:

- Persona management (Ailey’s system prompt)
- Session history
- LLM provider selection
- TTS synthesis

#### 3.1.1 Request

**Method:**

```http
POST /api/vr_chat
Content-Type: application/json
```

**Body:**

```json
{
  "session_id": "string",
  "user_text": "string"
}
```

- `session_id` (string, required)  
  A unique identifier chosen by the client (e.g. a UUID or player ID). The
  backend uses this to maintain short-term conversation history for that
  session.

- `user_text` (string, required)  
  The latest message from the user. In a VR context, this is typically the
  result of voice-to-text or a text input widget.

#### 3.1.2 Response

On success, the gateway returns:

```json
{
  "assistant_text": "string",
  "audio_wav_base64": "string"
}
```

- `assistant_text` – The assistant’s reply, as plain text.
- `audio_wav_base64` – The assistant’s reply synthesized to WAV and encoded
  as base64. When decoded, this is a valid WAV file.

A minimal example:

```json
{
  "assistant_text": "Hi! I'm Ailey, your VR secretary. How can I help?",
  "audio_wav_base64": "UklGRiQAAABXQVZF..."
}
```

#### 3.1.3 Error Responses

Errors are returned with an appropriate HTTP status code (e.g. 400/500) and a
JSON body with an `detail` field, e.g.:

```json
{
  "detail": "Invalid request body"
}
```

Or, in case of a provider error:

```json
{
  "detail": "Failed to call LLM provider"
}
```

The Unreal plugin surfaces these as `OnError(ErrorMessage)` events.

---

## 4. Internal LLM Protocol (OpenAI-Style)

While not strictly part of the public engine-facing API, understanding the
internal LLM protocol can help you integrate directly with providers if you
wish.

VRSecretary’s LLM clients (e.g. `OllamaClient`) typically call an endpoint like:

```http
POST /v1/chat/completions
Content-Type: application/json
```

with a body:

```json
{
  "model": "model-name",
  "messages": [
    {"role": "system", "content": "You are Ailey, a helpful VR secretary..."},
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "top_p": 1.0,
  "max_tokens": 256
}
```

and expect a response:

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Hello! I'm Ailey..."
      }
    }
  ]
}
```

This protocol is **not required** for engine integrations. Engines that prefer
to talk directly to an OpenAI-style server (bypassing the gateway) can replicate
what the Unreal plugin’s `DirectOllama` mode does:

- Build the same payload.
- Send it to the appropriate server.
- Parse `choices[0].message.content`.

In that case, you’ll also need to decide how to handle TTS (e.g. call a TTS
service directly or forward the text to the VRSecretary gateway just for audio).

---

## 5. Sessions & History

VRSecretary keeps a small per-session history for `/api/vr_chat`:

- Sessions are keyed by `session_id`.
- History length is bounded by a configuration parameter
  (e.g. `SESSION_MAX_HISTORY` in the gateway config).
- Each new request appends the latest turns and may evict older turns when the
  limit is reached.

This design keeps the client protocol simple (you only send the last user
message) while still providing multi-turn conversations.

If you need **fine-grained control over history** (e.g. you want to push a
large prompt or specific context), you can:

1. Implement a separate endpoint in the gateway for advanced usage, or
2. Talk directly to the OpenAI-style LLM endpoint (like DirectOllama) and build
   your own `messages` array client-side.

---

## 6. CORS & Cross-Origin Access

If you build web-based tooling (e.g. a browser-based debugging console) that
calls the VRSecretary API, you may need CORS enabled.

The FastAPI app can be configured with CORS middleware to allow specific
origins; see its `main.py` and FastAPI documentation for details.

---

## 7. Versioning

At the moment the API surface is small enough that we do not version paths.
If/when breaking changes are introduced, they should be introduced as new
paths (e.g. `/api/v2/vr_chat`) while keeping `/api/vr_chat` stable for existing
clients.

For internal LLM protocol changes (e.g. switching providers), the goal is to
keep `/api/vr_chat` behavior equivalent so engines don’t need to be updated.
