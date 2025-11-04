# Unreal Engine Integration Guide

This guide walks through integrating the **VRSecretary** Unreal plugin into
your own UE5 project, wiring it up to the backend, and driving a VR avatar.

If you just want to try things quickly, also see the sample project in
`/samples/unreal-vr-secretary-demo/`.

---

## 1. Installing the Plugin

### 1.1 Copy the plugin

From the VRSecretary repo:

```bash
cd /path/to/VRSecretary
mkdir -p /path/to/YourUEProject/Plugins
cp -r engine-plugins/unreal/VRSecretary /path/to/YourUEProject/Plugins/
```

If you cloned VRSecretary recently and haven’t run the patch script yet, do:

```bash
cd /path/to/VRSecretary
chmod +x tools/scripts/apply_vrsecretary_patch.sh
./tools/scripts/apply_vrsecretary_patch.sh
```

This ensures the plugin source code is up to date (Gateway + DirectOllama +
LocalLlamaCpp via Llama-Unreal).

### 1.2 Regenerate project files & build

1. Right-click your `.uproject` → **Generate Visual Studio project files**.
2. Open the generated `.sln`.
3. Build in **Development Editor / Win64**.

### 1.3 Enable plugin(s)

In Unreal:

1. Go to **Edit → Plugins**.
2. Search for **VRSecretary** and ensure it’s enabled.
3. If you plan to use the **LocalLlamaCpp** mode, also enable the **Llama**
   plugin (Llama-Unreal).

Restart the editor if prompted.

---

## 2. Project Settings (Global Configuration)

Open:

> **Edit → Project Settings → Plugins → VRSecretary**

Key settings:

- **Gateway URL** – base URL of the FastAPI gateway, e.g. `http://localhost:8000`.
- **Backend Mode** – default backend mode for all components:
  - Gateway (Ollama)
  - Gateway (watsonx.ai)
  - DirectOllama
  - LocalLlamaCpp
- **HTTP Timeout** – default timeout for HTTP calls (Gateway + DirectOllama).
- **Direct Ollama URL** – base URL of your OpenAI-style endpoint, e.g. `http://localhost:11434`.
- **Direct Ollama Model** – default model name, e.g. `llama3`.

You can override the backend mode per component, but these settings are the
sensible global defaults for your project.

---

## 3. Adding VRSecretaryComponent to an Actor

The main integration point is `UVRSecretaryComponent` (Blueprint class:
`VRSecretaryComponent`).

### 3.1 Choose an Actor

Common choices:

- A dedicated **manager** Blueprint (e.g. `BP_VRSecretaryManager`).
- The **VR Pawn** or Player Controller.

As a rule of thumb:

- Use a manager if you want to control multiple avatars or share the same
  session across them.
- Use the VR Pawn if you want a fully self-contained player experience.

### 3.2 Add the Component

1. Open your chosen Blueprint.
2. Click **Add Component** → search for **VRSecretaryComponent**.
3. Select it and inspect the **Details** panel:

   - **Override Backend Mode** (`bOverrideBackendMode`):
     - If true, this component uses its own `BackendMode` instead of the global default.
   - **Backend Mode**:
     - One of the four modes described in the overview.
   - **Default Chat Config** (`FVRSecretaryChatConfig`):
     - Default temperature, max tokens, etc.
   - **Llama Component** (`ULlamaComponent*`):
     - Optional reference used in `LocalLlamaCpp` mode. If not set, the component will
       auto-discover a `ULlamaComponent` on the same actor.

### 3.3 Events

`VRSecretaryComponent` exposes two multicast events:

- **OnAssistantResponse (AssistantText, AudioBase64)**
- **OnError (ErrorMessage)**

To bind them in Blueprint:

1. Select the `VRSecretaryComponent` in the Components panel.
2. In the Event Graph:
   - Right-click → search for **Assign OnAssistantResponse**.
   - Right-click → search for **Assign OnError**.
3. Implement the bound events, e.g.:
   - For `OnAssistantResponse`:
     - Update a subtitles widget with `AssistantText`.
     - If `AudioBase64` is not empty:
       - Decode it to a WAV sound and play it at the avatar’s location.
   - For `OnError`:
     - Print to screen and log.
     - Optionally show a “connection issue” message to the user.

---

## 4. Sending User Text from Blueprint

The core function is:

```cpp
UFUNCTION(BlueprintCallable, Category="VRSecretary")
void SendUserText(const FString& UserText, const FVRSecretaryChatConfig& Config);
```

There is also a shorthand:

```cpp
UFUNCTION(BlueprintCallable, Category="VRSecretary")
void SendUserTextWithDefaultConfig(const FString& UserText);
```

### 4.1 Typical Blueprint Pattern

1. Create a `VRSecretaryChatConfig` variable (or rely on the component’s default).
2. On a button press or UI event:
   - Read the user’s text from an input field or from a speech-to-text subsystem.
   - Call `SendUserText(UserText, ChatConfig)`.

Example (pseudo-graph):

```text
[VR Button Pressed]
      |
      v
[Get User Text from Widget]
      |
      v
[SendUserTextWithDefaultConfig(UserText)]
```

When the backend finishes, `OnAssistantResponse` will fire.

### 4.2 Handling Audio

The plugin does **not** dictate how you play audio; it just gives you
`AudioBase64` (base64-encoded WAV) when in Gateway modes.

A common setup:

1. Use a plugin or your own code to:
   - Decode base64 → raw bytes.
   - Create a `USoundWave` or runtime audio asset.
2. Play the sound at the avatar’s location.

You can encapsulate this logic in a separate Blueprint or C++ utility so the
rest of your Blueprints only deal with `AssistantText` and `AudioBase64`.

---

## 5. Using Different Backend Modes

### 5.1 Gateway (Ollama / watsonx.ai)

**Requirements:**

- FastAPI gateway running at `Gateway URL`.
- Ollama or watsonx.ai configured in the gateway `.env`.
- Chatterbox running and reachable from the gateway.

**Configure:**

- Project Settings → Plugins → VRSecretary:
  - `Backend Mode` = **Gateway (Ollama)** or **Gateway (watsonx.ai)**.

**Behavior:**

- `SendUserText` → `POST /api/vr_chat`.
- Returns text + `audio_wav_base64`.
- Best choice for most VR experiences (simple Unreal code, rich backend behavior).

### 5.2 DirectOllama (OpenAI-style)

**Requirements:**

- An OpenAI-style `/v1/chat/completions` endpoint, typically:
  - Ollama configured with a proxy that exposes OpenAI Chat Completions.

**Configure:**

- Project Settings → Plugins → VRSecretary:
  - `Backend Mode` = **DirectOllama**.
  - `Direct Ollama URL` = your server, e.g. `http://localhost:11434`.
  - `Direct Ollama Model` = `llama3` or similar.

**Behavior:**

- `SendUserText` → `POST {DirectOllamaUrl}/v1/chat/completions`.
- Sends a simple `messages` array containing the user message (and any system
  prompt you choose to add).
- Expects `choices[0].message.content`.
- Fires `OnAssistantResponse(AssistantText, "")` (no audio).

Use this mode when you want a **very lightweight** stack and are comfortable
handling TTS (if any) yourself.

### 5.3 LocalLlamaCpp (Llama-Unreal)

**Requirements:**

- Llama-Unreal plugin installed and enabled.
- A `ULlamaComponent` configured with a GGUF model on the same Actor as the
  `VRSecretaryComponent` (or referenced explicitly).

**Configure:**

- Project Settings → Plugins → VRSecretary:
  - `Backend Mode` = **LocalLlamaCpp** (or override on the component).

**Behavior:**

- `SendUserText` builds a `FLlamaChatPrompt` and calls
  `LlamaComponent->InsertTemplatedPromptStruct(...)`.
- Llama-Unreal runs inference locally in a background thread.
- When finished, Llama-Unreal fires its own response delegate.
- VRSecretary listens and forwards the final text to `OnAssistantResponse(AssistantText, "")`.

This mode is ideal for **fully offline** scenarios or where you want tight
control over performance and distribution of the model.

---

## 6. Sample Project Walkthrough

The repo includes a sample project under:

```text
/samples/unreal-vr-secretary-demo/
```

Steps:

1. Copy the VRSecretary plugin into the sample’s `Plugins/` if not already present.
2. Right-click `VRSecretaryDemo.uproject` → **Generate Visual Studio project files**.
3. Open in Unreal and build modules if prompted.
4. Configure **Project Settings → Plugins → VRSecretary** as described above.
5. Inspect Blueprints such as:
   - `BP_VRSecretaryManager`
   - `BP_SecretaryAvatar`
6. Run in **VR Preview** and interact with Ailey.

This project is a reference implementation; you can copy patterns from it into
your own game/app.

---

## 7. Tips & Best Practices

- **Keep backend & Unreal in sync**: If you change backend behavior (e.g. LLM
  parameters, persona), document it in your game’s design docs and test in VR.
- **Use `session_id` wisely**: In Gateway mode, assign stable session IDs per
  player to get coherent multi-turn conversations.
- **Handle errors gracefully**: Always bind `OnError` and give users clear,
  non-technical feedback (e.g. “Ailey is thinking…” or “Connection lost”).

---

For more information on backend behavior, see `architecture.md` and
`engine-agnostic-api.md`. For persona details, see `persona-ailey.md`.
