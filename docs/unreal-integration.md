# Unreal Engine Integration Guide

This guide explains how to integrate the **VRSecretary** backend into
an Unreal Engine 5 project using the `VRSecretary` plugin and the sample VR project.

## Prerequisites

- Unreal Engine **5.3+**
- C++ toolchain:
  - Windows: Visual Studio 2022 with “Game development with C++”.
  - macOS: Xcode + Command Line Tools.
- A VR headset & runtime (SteamVR, Oculus, etc.) if you want to run in VR.
- VRSecretary backend running (see `deployment-guide.md`),
  or at least `make run-gateway` working.

---

## 1. Using the Sample Project (Recommended)

The fastest way to see VRSecretary in action is to use the sample:

```text
VRSecretary/samples/unreal-vr-secretary-demo/
```

1. Open **Unreal Engine 5**.
2. In your file browser, go to:
   ```text
   VRSecretary/samples/unreal-vr-secretary-demo/
   ```
3. Right-click `VRSecretaryDemo.uproject` → **Generate Visual Studio project files**.
4. Double-click `VRSecretaryDemo.uproject` to open in UE5.
5. Let UE build the C++ project (this compiles the `VRSecretary` plugin).

### 1.1 Enable and Configure the Plugin

1. In Unreal, go to **Edit → Plugins**.
2. Ensure **VRSecretary** is enabled (it should be in the “AI” category).
3. Go to **Edit → Project Settings → Plugins → VRSecretary** and verify:

   - **Gateway URL**: `http://localhost:8000` (or wherever your backend runs).
   - **Backend Mode**: `Gateway (Ollama)` or `Gateway (Watsonx)` depending on `MODE` in `.env`.
   - **HTTP Timeout**: e.g., `60.0` seconds.

### 1.2 Avatar & Level

- The sample project contains a secretary avatar Blueprint (e.g., `BP_SecretaryAvatar`)
  wired to:

  - An `AudioComponent` for voice playback.
  - A 3D widget for subtitles.
  - Simple animations (idle/talking).

- In the main VR level, you should see:
  - Player start / VR pawn.
  - The secretary avatar placed in front of the player.
  - A `BP_VRSecretaryManager` actor that owns a `VRSecretaryComponent`.

### 1.3 Try It

1. Start backend & services as described in `deployment-guide.md`:
   - `make start-stack` (or at least `make run-gateway` + manual Ollama + Chatterbox).
2. Connect your VR headset.
3. In Unreal, click **Play → VR Preview**.
4. Use the input configured in `BP_VRSecretaryManager` (e.g., a controller button + software keyboard)
   to send a message like “Hello Ailey, who are you?”.
5. You should see subtitles above the avatar and hear Ailey respond.

---

## 2. Adding the Plugin to Your Own Project

If you want to integrate VRSecretary into an existing UE5 project:

### 2.1 Copy the Plugin

1. In your repo, the plugin lives at:

   ```text
   VRSecretary/engine-plugins/unreal/VRSecretary/
   ```

2. Copy it to your project’s `Plugins` folder:

   ```bash
   cd VRSecretary
   mkdir -p /path/to/YourUEProject/Plugins
   cp -r engine-plugins/unreal/VRSecretary /path/to/YourUEProject/Plugins/
   ```

3. Right-click your project’s `.uproject` → **Generate Visual Studio project files**.
4. Open the project in Unreal, then build when prompted.

### 2.2 Enable & Configure Settings

1. In Unreal, go to **Edit → Plugins** and ensure `VRSecretary` is enabled.
2. Go to **Edit → Project Settings → Plugins → VRSecretary** and configure:

   - `GatewayUrl` – `http://localhost:8000` or your backend URL.
   - `BackendMode` – typically `GatewayOllama` or `GatewayWatsonx`.
   - `HttpTimeout` – e.g., `60.0` seconds.
   - `DirectOllamaUrl`, `DirectOllamaModel` – for direct Ollama mode if you use it.

### 2.3 Add the Component in Your Level

1. Create a new Blueprint actor, e.g. `BP_VRSecretaryManager`.
2. Add a **VRSecretary Component** (from the Components panel).
3. Optionally expose variables like `SessionId` or `BackendModeOverride`.

Example Blueprint logic:

- **Event BeginPlay**
  - Ensure a `SessionId` is set (or let the component auto-generate).
  - Find your avatar actor (e.g., `BP_SecretaryAvatar`) and keep a reference.

- **User Input Event** (e.g., triggered by a VR controller button):
  - Show a text input UI (or use speech-to-text).
  - When text is submitted, call:
    ```
    VRSecretaryComponent → SendUserText(UserText, ChatConfig)
    ```

- **OnAssistantResponse (text, audioBase64)**:
  - Forward `AssistantText` and `AudioBase64` to your avatar Blueprint:
    - Update subtitles widget.
    - Decode `AudioBase64` into a `USoundWave` (via Runtime Audio Importer or custom code).
    - Play via an `AudioComponent`.

- **OnError (errorMessage)**:
  - Display an error message to the user (e.g., UMG, VR HUD).

---

## 3. Handling Audio (Base64 WAV) in Unreal

The backend response contains `audio_wav_base64` (WAV bytes, base64-encoded). There are multiple ways to handle this:

1. **Runtime Audio Importer Plugin**
   - Install a plugin such as “Runtime Audio Importer” from the Unreal Marketplace.
   - Use Blueprint nodes to convert base64/WAV bytes into a `USoundWave` at runtime.
   - Set that sound on an `AudioComponent` and play.

2. **Custom C++ Decoder**
   - Implement a small decoder in C++:
     - Base64 decode → raw WAV bytes.
     - Parse WAV header + PCM data into a `USoundWave`.
   - This requires familiarity with Unreal’s audio APIs.

3. **Alternative Approach**
   - Instead of streaming audio, you could:
     - Save the audio to disk from the backend and return a URL.
     - Unreal downloads the file and loads it as a sound asset.
   - This is less real-time but simpler in some setups.

---

## 4. Backend Mode Choices

In the plugin settings, you can choose:

- **Gateway (Ollama / Watsonx)** – Recommended
  - Unreal → FastAPI gateway → LLM + TTS.
  - Supports both offline and online LLMs, plus TTS integration.
  - Central place to manage prompts, logging, and future features (RAG, tools).

- **Direct Ollama**
  - Unreal → Ollama HTTP API directly.
  - Only text responses (no TTS by default).
  - Useful if you want a very simple, all-in-Unreal workflow.

- **Local Llama.cpp (Stub)**
  - Placeholder to integrate directly with `llama.cpp` as a third-party library.
  - Requires adding headers and static libraries into `ThirdParty/LlamaCpp` and wiring calls.

---

## 5. VR UX Tips

- Keep responses **short** (Ailey’s prompt already encourages this).
- Provide a clear interaction cue (e.g., a “Talk to Secretary” button or gesture).
- Use subtitles even when playing audio (accessibility + clarity).
- Consider adding a “Thinking…” indicator while waiting for responses.

For persona details and how Ailey behaves, see `persona-ailey.md`.
For deployment and backend setup, see `deployment-guide.md`.
