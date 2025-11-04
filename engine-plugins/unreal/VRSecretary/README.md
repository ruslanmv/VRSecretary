# VRSecretary Unreal Plugin

The **VRSecretary** Unreal plugin connects your UE5 project to AI backends (Ollama / watsonx via a FastAPI gateway, or directly to Ollama). It exposes a single Blueprint-friendly component you can drop onto any Actor and start sending/receiving AI messages.

This README covers only the Unreal plugin located at:

`engine-plugins/unreal/VRSecretary/`

---

## 1. Prerequisites

Before using the plugin, make sure you have:

- **Unreal Engine 5.3+**
- A C++ project (or a Blueprint project converted to C++)
- At least one AI backend running:

  **Option A – Gateway (recommended)**  
  - `uvicorn vrsecretary_gateway.main:app --host 0.0.0.0 --port 8000`  
  - Optional: Ollama + Chatterbox TTS for full voice support

  **Option B – Direct Ollama (no Python gateway)**  
  - `ollama serve` running on `http://localhost:11434`

---

## 2. Installing the Plugin into Your Project

1. **Copy the plugin folder into your project**

   From your VRSecretary repo:

   ```bash
   cd /path/to/VRSecretary
   cp -r engine-plugins/unreal/VRSecretary /path/to/YourUnrealProject/Plugins/
````

2. **Regenerate project files**

   * Right-click your `.uproject` → **Generate Visual Studio project files**

3. **Build the project**

   * Open the generated `.sln` in Visual Studio
   * Build in **Development Editor** for **Win64**

4. **Enable the plugin (if needed)**

   * Open your project in UE
   * Go to **Edit → Plugins**
   * Search for **VRSecretary**
   * Make sure it’s **enabled**, then restart the editor if prompted

---

## 3. Configuring the Plugin (Project Settings)

Open:

> **Edit → Project Settings → Plugins → VRSecretary**

You’ll see these settings:

* **Gateway URL**
  Base URL of the FastAPI gateway
  Example: `http://localhost:8000`

* **Backend Mode** (enum `EVRSecretaryBackendMode`)

  * **Gateway (Ollama)** – UE → Gateway → Ollama → TTS
  * **Gateway (watsonx.ai)** – UE → Gateway → Watsonx → TTS
  * **Direct Ollama** – UE → Ollama (no gateway, *no TTS*)
  * **Local Llama.cpp (stub)** – placeholder for in-engine llama.cpp

* **HTTP Timeout**
  Default HTTP request timeout (seconds), e.g. `60.0`

* **Direct Ollama URL**
  Base URL of your Ollama server, e.g. `http://localhost:11434`

* **Direct Ollama Model**
  Default model name, e.g. `llama3`

You can override the backend mode per component, but these are the global defaults.

---

## 4. Using the VRSecretary Component in Blueprints

The main entry point is:

`UVRSecretaryComponent` (Blueprint class: **VRSecretaryComponent**)

### 4.1. Add the Component to an Actor

1. Open or create a Blueprint (e.g. `BP_VRSecretaryManager` or your VR pawn).
2. Click **Add Component** → search for **VRSecretaryComponent**.
3. Select it and configure in the **Details** panel if desired:

   * Set **BackendModeOverride** (optional)
   * Optionally pre-set a **SessionId** (otherwise a GUID is auto-generated at `BeginPlay`)

### 4.2. Bind to Events

`VRSecretaryComponent` exposes these multicast events:

* **OnAssistantResponse(AssistantText, AudioBase64)**

  * `AssistantText` – AI’s text reply
  * `AudioBase64` – base64 encoded WAV audio (non-empty in Gateway mode)

* **OnError(ErrorMessage)**

  * Fired when HTTP/JSON errors occur

In the Blueprint Event Graph:

1. Select the **VRSecretaryComponent**.
2. Right-click in the graph → **Assign OnAssistantResponse**.
3. Right-click → **Assign OnError**.

Example wiring:

* `OnAssistantResponse`:

  * Forward `AssistantText` and `AudioBase64` to your avatar Blueprint (e.g. `BP_SecretaryAvatar → OnNewAssistantText`).
  * Update a widget with subtitles.
* `OnError`:

  * Print to screen / log.
  * Optionally show a notification in VR.

### 4.3. Sending Text to the AI

Function:

```cpp
UFUNCTION(BlueprintCallable, Category = "VRSecretary")
void SendUserText(const FString& UserText, const FVRSecretaryChatConfig& Config);
```

In Blueprint:

1. Create a variable of type **VRSecretaryChatConfig** (struct).
2. Set its fields as needed (default values are usually fine):

   * `Temperature` (e.g. 0.7)
   * `TopP` (e.g. 0.9)
   * `MaxTokens` (e.g. 256)
3. From your input logic (button press, voice-to-text, etc.):

   * Call **SendUserText(UserText, ChatConfig)** on the `VRSecretaryComponent`.

The call returns immediately; the response arrives asynchronously through **OnAssistantResponse**.

---

## 5. Backend Modes – What They Actually Do

### 5.1. Gateway Modes (Ollama / watsonx.ai)

* UE calls: `POST {GatewayUrl}/api/vr_chat`

* Request body:

  ```json
  {
    "session_id": "your-session-id",
    "user_text": "Hello!"
  }
  ```

* Python gateway:

  * Builds messages: `system` + `user` (Ailey persona)
  * Calls:

    * Ollama or watsonx.ai, depending on mode
  * Uses Chatterbox TTS to synthesize speech
  * Returns:

    ```json
    {
      "assistant_text": "...",
      "audio_wav_base64": "UklGRiQAAABXQVZF..."
    }
    ```

* UE `OnAssistantResponse`:

  * `AssistantText` – show in UI
  * `AudioBase64` – decode and play (e.g. via Runtime Audio Importer)

**Use this mode when you want:**

* Multi-turn convo & persona managed in Python
* Higher flexibility (watsonx.ai, RAG, tools)
* Audio (TTS) out of the box

### 5.2. Direct Ollama

* UE calls: `POST {DirectOllamaUrl}/v1/chat/completions`

* JSON payload:

  ```json
  {
    "model": "<DirectOllamaModel>",
    "messages": [
      {"role": "system", "content": "You are Ailey, a helpful VR secretary..."},
      {"role": "user", "content": "<UserText>"}
    ],
    "stream": false,
    "temperature": <Config.Temperature>,
    "top_p": <Config.TopP>,
    "max_tokens": <Config.MaxTokens>
  }
  ```

* Parses `choices[0].message.content` and fires `OnAssistantResponse` with:

  * `AssistantText` – AI text
  * `AudioBase64` – **empty string** (no TTS)

**Use this mode when you want:**

* Zero Python backend
* Direct, simple integration with your local Ollama
* You are OK with **text-only** responses (you must handle TTS separately)

### 5.3. Local Llama.cpp (Stub)

* Currently just logs a warning and falls back to `SendViaGateway`.
* Placeholder for a future **in-engine llama.cpp** integration.

To enable real llama.cpp later:

* Put headers in `ThirdParty/LlamaCpp/Include`
* Put libs in `ThirdParty/LlamaCpp/Lib/Win64`
* Update `VRSecretary.Build.cs` accordingly
* Replace the stub logic in `SendViaLocalLlamaCpp`

---

## 6. Typical Step-by-Step Flow (Gateway Mode)

1. **Run backend stack**:

   * Ollama, Chatterbox, and the FastAPI gateway

2. **Open Unreal project** with VRSecretary plugin installed.

3. **Configure** in Project Settings:

   * Backend Mode: **GatewayOllama** (or **GatewayWatsonx**)
   * Gateway URL: `http://localhost:8000`

4. **Add VRSecretaryComponent** to a manager Actor or the VR pawn.

5. **Create Blueprint logic**:

   * On button press / UI input:

     * Collect text → call `SendUserText`
   * On `OnAssistantResponse`:

     * Update avatar subtitles
     * Decode `AudioBase64` and play sound

6. **Play in Editor (VR or normal)**:

   * Interact and observe the AI secretary responses.

---

## 7. Troubleshooting

**No response / timeouts**

* Check backend:

  * `curl http://localhost:8000/health`
  * Ensure Ollama / watsonx / Chatterbox are running (for Gateway)

**Error: “Failed to parse JSON / missing fields”**

* Check gateway or Ollama response format (enable logging on both sides).

**No audio (Gateway mode)**

* Ensure Chatterbox is reachable from the gateway
* Check that `audio_wav_base64` is non-empty in the response
* Verify your Blueprint decoding & audio pipeline

**DirectOllama works but Gateway doesn’t**

* Confirms plugin HTTP works; issue likely in Python gateway configuration.

---

That’s it. Once this plugin is in your project, the main loop is:

> **Blueprint input → VRSecretaryComponent.SendUserText → LLM/TTS → OnAssistantResponse → Avatar UI+Audio**

You can evolve the backend independently (RAG, tools, calendar, email) without changing the Unreal layer.
