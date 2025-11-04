# VRSecretary Unreal Plugin

The **VRSecretary** Unreal plugin connects your UE5 project to AI backends
(Ollama / watsonx via a FastAPI gateway, or directly to an OpenAI-style
Ollama endpoint, plus fully local llama.cpp via the **Llama-Unreal** plugin).

It exposes a single Blueprint-friendly component you can drop onto any Actor
and start sending/receiving AI messages.

This README covers only the Unreal plugin located at:

`engine-plugins/unreal/VRSecretary/`

---

## 1. Prerequisites

Before using the plugin, make sure you have:

- **Unreal Engine 5.3+**
- A **C++ project** (or a Blueprint project converted to C++)
- At least one AI backend running:

  **Option A – Gateway (recommended for full text+audio)**  
  - FastAPI gateway:  
    `uvicorn vrsecretary_gateway.main:app --host 0.0.0.0 --port 8000`  
  - Ollama server (local LLM)  
  - Chatterbox TTS (for audio synthesis)

  **Option B – Direct Ollama (no Python gateway, text only)**  
  - An OpenAI-compatible endpoint (e.g. Ollama with an OpenAI-style proxy) exposed at  
    `http://localhost:11434/v1/chat/completions`

  **Option C – Local Llama.cpp (in-engine)**  
  - The **Llama-Unreal** plugin (`Llama` with `LlamaCore` module) installed and enabled
  - A GGUF model configured on a `ULlamaComponent` in your project

---

## 2. Installing the Plugin into Your Project

1. **Copy the plugin folder into your project**

   From the VRSecretary repo:

   ```bash
   cd /path/to/VRSecretary
   mkdir -p /path/to/YourUnrealProject/Plugins
   cp -r engine-plugins/unreal/VRSecretary /path/to/YourUnrealProject/Plugins/
   ```

2. **(Optional) Install Llama-Unreal for LocalLlamaCpp**

   * Install the **Llama** plugin (Llama-Unreal) into your engine or your project’s `Plugins`.
   * Make sure the plugin defines the `LlamaCore` module (used by VRSecretary).

3. **Regenerate project files**

   * Right-click your `.uproject` → **Generate Visual Studio project files**

4. **Build the project**

   * Open the generated `.sln` in Visual Studio
   * Build in **Development Editor** for **Win64**

5. **Enable the plugins**

   * Open your project in UE
   * Go to **Edit → Plugins**
   * Search for **VRSecretary** and ensure it is **enabled**
   * If using LocalLlamaCpp, also enable **Llama**

   Restart the editor if prompted.

---

## 3. Configuring the Plugin (Project Settings)

Open:

> **Edit → Project Settings → Plugins → VRSecretary**

You’ll see these settings (backed by `UVRSecretarySettings`):

### 3.1 Gateway URL

**Gateway URL**
Base URL of the FastAPI gateway:

* Example: `http://localhost:8000`

Used when `Backend Mode` is set to one of the **Gateway** modes.

### 3.2 Backend Mode (`EVRSecretaryBackendMode`)

**Backend Mode** – global default for all `VRSecretaryComponent` instances:

* **Gateway (Ollama)**
  UE → Gateway → Ollama → Chatterbox TTS
  Returns **text + base64-encoded audio**.

* **Gateway (watsonx.ai)**
  UE → Gateway → IBM watsonx.ai → Chatterbox TTS
  Returns **text + base64-encoded audio**.

* **DirectOllama**
  UE → OpenAI-style `/v1/chat/completions` endpoint (e.g. Ollama proxy)
  Returns **text only** (no audio).

* **LocalLlamaCpp**
  UE → `ULlamaComponent` (Llama-Unreal) → local llama.cpp model
  Returns **text only** (no audio by default).

Components can override this global mode per instance.

### 3.3 HTTP Timeout

**HTTP Timeout**
Default HTTP request timeout (seconds) for Gateway and DirectOllama calls.

* Example: `60.0`

### 3.4 Direct Ollama URL / Model

Used when `Backend Mode` is **DirectOllama**:

* **Direct Ollama URL**
  Base URL of your OpenAI-style endpoint.
  Example: `http://localhost:11434`

  The plugin calls `${DirectOllamaUrl}/v1/chat/completions`.

* **Direct Ollama Model**
  Default model name to send in the JSON payload.
  Example: `llama3`

---

## 4. VRSecretary Component (Blueprint / C++)

The main entry point is:

* C++: `UVRSecretaryComponent`
* Blueprint class: **VRSecretaryComponent**

### 4.1. Adding the Component to an Actor

1. Open or create a Blueprint (e.g. `BP_VRSecretaryManager` or your VR Pawn).
2. Click **Add Component** → search for **VRSecretaryComponent**.
3. Select it and configure in the **Details** panel:

   * **Override Backend Mode** (bool, `bOverrideBackendMode`):
     If checked, this component uses its own backend mode instead of the global default.
   * **Backend Mode** (enum, `BackendMode`):
     Per-component override value (same options as the global setting).
   * **Default Chat Config** (`FVRSecretaryChatConfig`):
     Per-component default for temperature, max tokens, etc.
   * **Llama Component** (`ULlamaComponent*`):
     Optional reference to a `ULlamaComponent` used when Backend Mode == `LocalLlamaCpp`.
     If not set, the component will try to auto-discover a `ULlamaComponent` on the same Actor at runtime.

### 4.2. Events

`VRSecretaryComponent` exposes two Blueprint multicast events:

* **OnAssistantResponse(AssistantText, AudioBase64)**

  * `AssistantText` – AI’s text reply.
  * `AudioBase64` – base64-encoded WAV audio:

    * Non-empty in **Gateway** modes (if TTS succeeded).
    * Empty string in **DirectOllama** and **LocalLlamaCpp** modes.

* **OnError(ErrorMessage)**

  * Fired when HTTP/JSON errors occur, or other backend issues arise.

In the Blueprint Event Graph:

1. Select the **VRSecretaryComponent** on your Actor.
2. Right-click in the graph → search for **Assign OnAssistantResponse**.
3. Same for **Assign OnError**.
4. Implement your logic (update subtitles, play audio, show error messages, etc.).

### 4.3. Sending Text to the AI

The primary call is:

```cpp
UFUNCTION(BlueprintCallable, Category="VRSecretary")
void SendUserText(const FString& UserText, const FVRSecretaryChatConfig& Config);
```

There is also a convenience function in C++:

```cpp
UFUNCTION(BlueprintCallable, Category="VRSecretary")
void SendUserTextWithDefaultConfig(const FString& UserText);
```

In Blueprint:

1. Create a variable of type **VRSecretaryChatConfig** (struct) or use the **Default Chat Config** on the component.

2. Set fields as needed:

   * `Temperature` (e.g. 0.7)
   * `TopP` (e.g. 1.0)
   * `MaxTokens` (e.g. 256)
   * `PresencePenalty` / `FrequencyPenalty` (often 0.0 initially)

3. From your input logic (e.g. button press, VR UI):

   * Call `SendUserText(UserText, ChatConfig)` or `SendUserTextWithDefaultConfig(UserText)`.

The call returns immediately; the response arrives asynchronously via **OnAssistantResponse**.

---

## 5. Backend Modes – Behavior Details

### 5.1. Gateway (Ollama / watsonx.ai)

**Flow:**

1. VRSecretaryComponent builds a JSON body:

   ```json
   {
     "session_id": "<GUID generated at BeginPlay>",
     "user_text": "<UserText>"
   }
   ```

2. Sends `POST {GatewayUrl}/api/vr_chat`.

3. The FastAPI gateway:

   * Adds the Ailey system prompt (persona).
   * Appends the user text and any prior history for this `session_id`.
   * Routes to Ollama **or** watsonx.ai depending on backend mode.
   * Calls Chatterbox TTS with the assistant’s reply to obtain WAV audio.
   * Returns:

     ```json
     {
       "assistant_text": "...",
       "audio_wav_base64": "UklGRiQAAABXQVZF..."
     }
     ```

4. The plugin parses the JSON and fires:

   * `OnAssistantResponse(AssistantText, AudioBase64)`.

**Good for:**

* Full text + voice experience.
* Centralized persona and history management.
* Flexibility to change LLM provider or add RAG/tools in Python without changing UE.

### 5.2. DirectOllama (OpenAI-style HTTP)

**Flow:**

1. VRSecretaryComponent builds a minimal OpenAI-style request:

   ```json
   {
     "model": "<DirectOllamaModel>",
     "messages": [
       { "role": "user", "content": "<UserText>" }
     ],
     "temperature": <Config.Temperature>,
     "top_p": <Config.TopP>,
     "presence_penalty": <Config.PresencePenalty>,
     "frequency_penalty": <Config.FrequencyPenalty>,
     "max_tokens": <Config.MaxTokens>
   }
   ```

   > Note: if you want a system prompt / persona **in DirectOllama mode**, you can
   > either add that in your upstream proxy, or extend the plugin to include a
   > system message here.

2. Sends `POST {DirectOllamaUrl}/v1/chat/completions`.

3. Expects a response compatible with OpenAI Chat Completions:

   ```json
   {
     "choices": [
       {
         "message": {
           "role": "assistant",
           "content": "..."
         }
       }
     ]
   }
   ```

4. It extracts `choices[0].message.content` and fires:

   * `OnAssistantResponse(AssistantText, "")` (no audio).

**Good for:**

* Very simple deployments (no Python if you don’t want it).
* Direct experimentation with local models (text-only).
* Consistent with the gateway’s OpenAI-style LLM API.

### 5.3. LocalLlamaCpp (via Llama-Unreal)

**Flow:**

1. In LocalLlamaCpp mode, `SendUserText` calls `SendViaLocalLlamaCpp`.

2. The component locates a `ULlamaComponent`:

   * Uses the explicit **Llama Component** reference if set, or
   * Auto-discovers a `ULlamaComponent` on the same Actor (`GetOwner()->FindComponentByClass<ULlamaComponent>()`).

3. It binds to `LlamaComponent->OnResponseGenerated` and sends a `FLlamaChatPrompt`:

   ```cpp
   FLlamaChatPrompt Prompt;
   Prompt.Prompt           = UserText;
   Prompt.Role             = EChatTemplateRole::User;
   Prompt.bAddAssistantBOS = true;
   Prompt.bGenerateReply   = true;

   LlamaComponent->InsertTemplatedPromptStruct(Prompt);
   ```

4. When Llama-Unreal finishes generating a reply, it triggers its own delegate,
   which flows into `HandleLlamaResponse` on `VRSecretaryComponent`:

   * `OnAssistantResponse(AssistantText, "")` (no audio).

**Setup notes:**

* Make sure the **Llama plugin** is installed and enabled (Llama-Unreal).

* On the same Actor as `VRSecretaryComponent`:

  1. Add a **LlamaComponent**.
  2. Configure it with:

     * Path to your GGUF model.
     * System prompt / context length as needed.
  3. Call its `LoadModel()` at startup (BeginPlay or similar).

* Alternatively, assign the `LlamaComponent` reference directly in the
  `VRSecretaryComponent` details panel.

**Good for:**

* Completely offline, in-process LLM.
* No external HTTP for generation.
* Full control over llama.cpp configuration from Unreal.

---

## 6. Typical Blueprints (Gateway Mode Example)

A minimal setup in a Blueprint (e.g. `BP_VRSecretaryManager`):

1. **Components**

   * `VRSecretaryComponent`

2. **Events**

   * On `Event BeginPlay`:

     * (Optional) Do a quick health check to the backend or show a “Connecting…” UI.

   * On a UI or input event (button / VR controller):

     * Get user text from your widget.
     * Call `SendUserTextWithDefaultConfig(UserText)` on `VRSecretaryComponent`.

   * `OnAssistantResponse`:

     * Update subtitles widget with `AssistantText`.
     * If `AudioBase64` is not empty:

       * Decode base64 → WAV bytes (e.g. using a Runtime Audio Importer plugin).
       * Play sound at the avatar’s location.

   * `OnError`:

     * Print error to log + optionally show message in UI.

3. **Project Settings**

   * Plugin → VRSecretary:

     * `Gateway URL` = `http://localhost:8000`
     * `Backend Mode` = Gateway (Ollama)
     * `HTTP Timeout` ~ 60s

---

## 7. Troubleshooting

**Plugin fails to compile**

* Confirm you ran `apply_vrsecretary_patch.sh` after cloning the repo.
* Make sure the `VRSecretary` folder inside your project matches the patched version.
* If using LocalLlamaCpp:

  * Ensure the **Llama** plugin (Llama-Unreal) is installed and enabled.
  * The VRSecretary module depends on `LlamaCore`; missing this will cause linker errors.

**Gateway mode: errors / no response**

* Check FastAPI logs for exceptions.
* Ensure:

  * `MODE` in `.env` is set correctly (`offline_local_ollama` or `online_watsonx`).
  * `OLLAMA_BASE_URL` and `CHATTERBOX_URL` are reachable from the gateway.
  * `/api/vr_chat` works via `curl` (see root README).

**DirectOllama: “choices[0] missing” or JSON parse errors**

* Verify your OpenAI-style endpoint actually returns the Chat Completions shape.
* Check that `DirectOllamaUrl` and `DirectOllamaModel` match your setup.

**LocalLlamaCpp: no response / fallback to gateway**

* Make sure a `ULlamaComponent` exists on the same Actor (or assigned in the details panel).
* Confirm the model is loaded successfully (check Llama-Unreal logs).
* Ensure the Llama plugin is enabled and compatible with your engine version.

---

## 8. Extending the Plugin

You can extend VRSecretary easily:

* Add new backend modes to `EVRSecretaryBackendMode`.
* Introduce streaming responses for DirectOllama using Unreal’s HTTP streaming APIs.
* Add a small TTS-only endpoint to the FastAPI gateway and call it from DirectOllama/LocalLlamaCpp to
  get audio for those modes as well.

Because all logic is funneled through `VRSecretaryComponent`, most changes can
happen in one place while your Blueprints stay the same.

---

With the plugin installed and configured, your main loop becomes:

> **Blueprint input → VRSecretaryComponent.SendUserText →
> (Gateway / DirectOllama / LocalLlamaCpp) → OnAssistantResponse → Avatar text + audio**

Everything behind that interface (which LLM, which TTS, local vs remote) can be swapped
out or upgraded without touching your gameplay logic.