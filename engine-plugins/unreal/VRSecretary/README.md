Here’s an updated, production-ready `engine-plugins/unreal/VRSecretary/README.md` with **all existing content preserved and expanded**, now documenting:

* Project-wide **default TTS language** (English by default).
* Per-component **language override** in `UVRSecretaryComponent`.
* How the plugin sends `"language"` to `/api/vr_chat`.
* How this ties into the **multilingual Chatterbox TTS** backend.

You can paste this directly over your current README:

````markdown
# VRSecretary Unreal Plugin

**Path in repo:** `engine-plugins/unreal/VRSecretary/`

This plugin is the Unreal Engine side of the VRSecretary project.  
It gives you a single Blueprint-friendly component that can talk to:

- A **FastAPI gateway** (VRSecretary backend) → Ollama / watsonx.ai → Chatterbox TTS  
- A **Direct Ollama** OpenAI-style HTTP endpoint (text only)  
- A future **Local Llama.cpp** integration (currently a stub that falls back to the gateway)

You attach the component to any Actor and send user text; the plugin calls the
configured backend and fires Blueprint events with the assistant’s reply.

The plugin is now also **language-aware**:

- A **project-wide default TTS language** (e.g. `en`) is configured in *Project Settings → Plugins → VRSecretary*.
- Each `VRSecretaryComponent` can optionally **override the language per avatar / actor** (e.g. `it`, `fr`, `es`).
- The plugin sends this `language` to the gateway, which forwards it to the **multilingual Chatterbox TTS server**.

This README is **only** about the Unreal plugin. See the root project README
for backend setup and VR sample project details.

---

## 1. Prerequisites

Before using the plugin, you should have:

- **Unreal Engine 5.3+**
- A **C++ Unreal project** (or a Blueprint project converted to C++)
- At least one LLM backend running:

### Option A – FastAPI Gateway (recommended: text + audio, multilingual TTS)

- VRSecretary FastAPI gateway running, for example:

  ```bash
  cd backend/gateway
  uvicorn vrsecretary_gateway.main:app --host 0.0.0.0 --port 8000
````

* **Ollama** server for the LLM:

  * `ollama serve`
  * `ollama pull llama3` (or your preferred model)

* **Chatterbox TTS (Multilingual)** for speech:

  * `chatterbox-server --port 4123`
    (or the provided `vr_chatterbox_server_multilingual.py` wrapper)

The gateway exposes:

* `POST /api/vr_chat` → `{ assistant_text, audio_wav_base64 }`
  and (optionally) accepts a `language` field to control TTS language.

### Option B – Direct Ollama (text only)

* An OpenAI-style `/v1/chat/completions` endpoint reachable from Unreal.
  Typical setup:

  ```text
  http://localhost:11434/v1/chat/completions
  ```

This is often Ollama behind a small HTTP proxy that mimics OpenAI Chat
Completions (many exist, or you can write one).

### Option C – Local Llama.cpp (stub for now)

The plugin defines a **LocalLlamaCpp** backend mode, but in the current version:

* `LocalLlamaCpp` simply logs a warning and **falls back to Gateway**.
* There is **no hard dependency** on any extra plugins (like Llama-Unreal) so
  the plugin compiles everywhere.

If you want a true in-engine llama.cpp, you can:

* Bring in Llama-Unreal (or your own llama.cpp wrapper)
* Replace the stub in `SendViaLocalLlamaCpp` and wire in your C++ calls
* Optionally use `ThirdParty/LlamaCpp/` to store headers/libs

See `ThirdParty/LlamaCpp/README.txt` for notes.

---

## 2. Installing the Plugin into a Project

### 2.1 Copy or link the plugin into your project

From the repo root:

```bash
cd C:\workspace\VRSecretary   # adjust to your path
```

**Option 1 – Copy (simple):**

```bash
mkdir -p samples\VRSecretaryGame\Plugins
xcopy /E /I engine-plugins\unreal\VRSecretary samples\VRSecretaryGame\Plugins\VRSecretary
```

**Option 2 – Junction (so you keep a single source of truth):**

```cmd
cd C:\workspace\VRSecretary
rmdir /S /Q samples\VRSecretaryGame\Plugins\VRSecretary  2>NUL
mklink /J "samples\VRSecretaryGame\Plugins\VRSecretary" "engine-plugins\unreal\VRSecretary"
```

(adjust paths if you’re using a different project).

> Any Unreal project that has `Plugins\VRSecretary\` under its root will see
> and build the plugin.

### 2.2 Regenerate project files

In Windows Explorer:

1. Right-click your `.uproject` (e.g. `VRSecretaryGame.uproject`)
2. Choose **Generate Visual Studio project files**

### 2.3 Build in Visual Studio

1. Open the generated `.sln` (e.g. `VRSecretaryGame.sln`)

2. Top toolbar:

   * **Solution Configuration:** `Development Editor`
   * **Solution Platform:** `Win64`

3. Menu → **Build → Build Solution**

If the build finishes with **0 errors**, the plugin is compiled and ready.

### 2.4 Enable the plugin in Unreal

1. Launch Unreal by double-clicking your `.uproject`.
2. Go to **Edit → Plugins**
3. Search for **VRSecretary**.
4. Make sure it’s **enabled**.
5. Restart Unreal if asked.

---

## 3. Plugin Settings (Project-Wide)

Open:

> **Edit → Project Settings → Plugins → VRSecretary**

These settings are implemented by `UVRSecretarySettings`.

### 3.1 Backend Mode

**Backend Mode** (`EVRSecretaryBackendMode`):

* **Gateway (Ollama)**
  UE → FastAPI gateway → Ollama → Chatterbox
  Returns `assistant_text` + `audio_wav_base64` (speech).

* **Gateway (watsonx.ai)**
  UE → FastAPI gateway → IBM watsonx.ai → Chatterbox
  Same return shape as above.

* **Direct Ollama**
  UE → OpenAI-style `/v1/chat/completions` endpoint
  Returns text only (no audio).

* **Local Llama.cpp (stub)**
  Currently logs a warning and calls the **Gateway** mode under the hood.

This is the **global default** for every `VRSecretaryComponent` unless they
explicitly override it.

### 3.2 Gateway URL

**Gateway URL**

* Base URL for the FastAPI gateway.
* Example: `http://localhost:8000`

Used when the effective backend mode is a **Gateway** mode.

### 3.3 HTTP Timeout

**HTTP Timeout** (seconds)

* Default: `60.0`
* Used for both Gateway and DirectOllama HTTP requests.

### 3.4 Direct Ollama URL / Model

Only used when the effective backend mode is **DirectOllama**:

* **Direct Ollama URL**
  Example: `http://localhost:11434`
  The plugin calls `DirectOllamaUrl + "/v1/chat/completions"`.

* **Direct Ollama Model**
  Example: `llama3`
  Sent as the `"model"` field in the JSON payload.

### 3.5 Default TTS Language (project-wide)

The plugin is multilingual-aware via a **default TTS language**:

* **Default TTS Language** (`DefaultLanguage` in `UVRSecretarySettings`)

  * An **ISO 639-1 code** (e.g. `en`, `it`, `fr`, `es`, `de`, `ru`, `zh`…).
  * Default value: `en` (English).
  * Used by the plugin whenever a component does **not** override the language.

**Flow:**

1. On each Gateway call, the plugin chooses an *EffectiveLanguage*:

   * If the component’s `LanguageOverride` is non-empty, it uses that.
   * Else, it uses `DefaultLanguage` from project settings.
   * If both are empty for some reason, it falls back to `"en"`.

2. The plugin sends that language to the gateway in the JSON body:

   ```json
   {
     "session_id": "<SessionId or GUID>",
     "user_text": "<UserText>",
     "language": "en"
   }
   ```

3. The backend gateway forwards this `language` to the **multilingual Chatterbox
   TTS server**, which synthesizes speech in the correct language (assuming
   the text and language are compatible).

---

## 4. Core Types & Component

### 4.1 Chat Config (sampling settings)

`FVRSecretaryChatConfig` is defined in `VRSecretaryChatTypes.h`:

```cpp
USTRUCT(BlueprintType)
struct FVRSecretaryChatConfig
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    float Temperature = 0.7f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    float TopP = 0.9f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    int32 MaxTokens = 256;
};
```

You pass an instance of this struct when sending user text.

### 4.2 Delegates (events)

Also in `VRSecretaryChatTypes.h`:

```cpp
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(
    FVRSecretaryOnAssistantResponse,
    const FString&, AssistantText,
    const FString&, AudioWavBase64
);

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(
    FVRSecretaryOnError,
    const FString&, ErrorMessage
);
```

* `OnAssistantResponse` fires when we get a valid reply.
* `OnError` fires for HTTP / JSON / mode errors.

### 4.3 VRSecretaryComponent

`VRSecretaryComponent` lives in:

* Header: `Source/VRSecretary/Public/VRSecretaryComponent.h`
* Source: `Source/VRSecretary/Private/VRSecretaryComponent.cpp`

Key properties and methods:

```cpp
UCLASS(ClassGroup=(VRSecretary), meta=(BlueprintSpawnableComponent))
class VRSECRETARY_API UVRSecretaryComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UVRSecretaryComponent();

    // Optional per-component override of the backend mode.
    // If left at GatewayOllama, the project-wide BackendMode is used.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    EVRSecretaryBackendMode BackendModeOverride;

    // Optional per-component TTS language override (ISO 639-1).
    // If empty, the project-wide DefaultLanguage is used for this component.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary|TTS")
    FString LanguageOverride;

    // Optional session ID. If empty, a GUID is generated at BeginPlay.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    FString SessionId;

    // Fired on successful response
    UPROPERTY(BlueprintAssignable, Category="VRSecretary")
    FVRSecretaryOnAssistantResponse OnAssistantResponse;

    // Fired on error
    UPROPERTY(BlueprintAssignable, Category="VRSecretary")
    FVRSecretaryOnError OnError;

    // Main call to send text to the configured backend
    UFUNCTION(BlueprintCallable, Category="VRSecretary")
    void SendUserText(const FString& UserText, const FVRSecretaryChatConfig& Config);

protected:
    virtual void BeginPlay() override;

private:
    const UVRSecretarySettings* Settings;

    void EnsureSessionId();

    void SendViaGateway(const FString& UserText);
    void SendViaDirectOllama(const FString& UserText, const FVRSecretaryChatConfig& Config);
    void SendViaLocalLlamaCpp(const FString& UserText, const FVRSecretaryChatConfig& Config);

    void HandleGatewayResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
    void HandleDirectOllamaResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
};
```

---

## 5. Using the Component in Blueprints

### 5.1 Add the component

1. Open (or create) a Blueprint, e.g. your VR pawn, desktop pawn, or avatar:

   * `BP_VRSecretaryManager`, `BP_VRPawn`, `BP_SecretaryAvatar`, etc.

2. Click **Add** in the Components panel.

3. Search for **VRSecretaryComponent** and add it.

### 5.2 Configure the component

Select the `VRSecretaryComponent` in the **Details** panel:

* **Backend Mode Override**

  * Default value: `GatewayOllama`.
  * If you want to use the **project-wide** backend mode from settings,
    you can leave this as `GatewayOllama` and let the settings decide.
  * If you want this component to use a different backend, change it to:

    * `GatewayWatsonx`
    * `DirectOllama`
    * `LocalLlamaCpp` (currently stub → gateway)

* **Language Override** (NEW)

  * ISO 639-1 code (e.g. `en`, `it`, `fr`, `es`, `de`…).

  * If left empty, the plugin uses `DefaultLanguage` from project settings.

  * If set, this language is sent on every `/api/vr_chat` call from this component:

    ```json
    {
      "session_id": "...",
      "user_text": "Qual è la capitale d'Italia?",
      "language": "it"
    }
    ```

  * This is ideal for having:

    * An English-speaking assistant in one level/actor.
    * An Italian or French-speaking assistant in another.

* **Session Id**

  * Optional; if empty the component generates a new GUID at `BeginPlay`.
  * If you want persistent conversation per-player or per-avatar, you can set
    a fixed session ID.

### 5.3 Bind to events

In the Blueprint Event Graph:

1. Select the `VRSecretaryComponent` in the Components list.

2. Right-click in the Event Graph and search for:

   * **Assign On Assistant Response**
   * **Assign On Error**

3. Add both event nodes and hook them up to your UI / audio logic:

* **OnAssistantResponse:**

  * Use `AssistantText` to update a 3D widget, subtitles, or debug logs.
  * If `AudioWavBase64` is non-empty (Gateway modes):

    * Decode base64 to bytes (e.g. with a runtime audio importer plugin).
    * Play the decoded sound at your avatar’s head or attached audio component.

* **OnError:**

  * Print to screen / log.
  * Optionally show an on-screen error panel.

### 5.4 Sending a message from Blueprint

To send the user’s text:

1. Create or reuse a `FVRSecretaryChatConfig` variable:

   * e.g. `ChatConfig`
   * Set `Temperature`, `TopP`, `MaxTokens` as desired.

2. From your input event (button, VR trigger, UI button):

   * Read the text from your widget (e.g. `EditableTextBox`).
   * Call:

     * **Send User Text** with:

       * `UserText` = string from the widget.
       * `Config`   = your `ChatConfig` struct.

The call returns instantly. When the backend responds, `OnAssistantResponse` fires.

---

## 6. Backend Mode Details

### 6.1 Gateway (Ollama / watsonx.ai, multilingual TTS)

**What it does:**

* Builds JSON like:

  ```json
  {
    "session_id": "<SessionId or GUID>",
    "user_text": "<UserText>",
    "language": "en"
  }
  ```

  * `language` is chosen as:

    * Component `LanguageOverride`, if set, otherwise
    * Project `DefaultLanguage`, otherwise
    * `"en"`.

* Calls:

  ```text
  POST {GatewayUrl}/api/vr_chat
  ```

* The gateway:

  * Builds a conversation with system prompt + history.
  * Calls the configured LLM (Ollama, watsonx.ai, etc.).
  * Calls **Chatterbox TTS** non-streaming with the assistant’s text and the
    received `language`, using a multilingual TTS model.
  * Returns:

    ```json
    {
      "assistant_text": "Certo! La capitale d'Italia è Roma.",
      "audio_wav_base64": "UklGRiQAAABXQVZF..."
    }
    ```

* On success, the plugin:

  * Fires `OnAssistantResponse(AssistantText, AudioBase64)`.

**When to use:**

* You want **speech** out of the box (audio_wav_base64).
* You want persona & history handled in Python.
* You want **multilingual voices** driven by simple language codes.
* You want to swap LLM providers (Ollama, watsonx.ai, etc.) without touching Unreal.

### 6.2 DirectOllama (text only)

**What it does:**

* Builds OpenAI-style payload:

  ```json
  {
    "model": "<DirectOllamaModel>",
    "messages": [
      { "role": "system", "content": "You are Ailey, a helpful VR secretary inside a virtual office." },
      { "role": "user", "content": "<UserText>" }
    ],
    "temperature": <Config.Temperature>,
    "top_p": <Config.TopP>,
    "max_tokens": <Config.MaxTokens>,
    "stream": false
  }
  ```

* Calls:

  ```text
  POST {DirectOllamaUrl}/v1/chat/completions
  ```

* Expects:

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

* On success:

  * Extracts `choices[0].message.content` and fires:

    ```text
    OnAssistantResponse(Text, "")
    ```

  * No audio is generated in this mode; if you want TTS, you must add your own
    TTS call from the gateway or another service.

**When to use:**

* You don’t want Python.
* You just need **text** replies.
* You already have or can deploy an OpenAI-style Ollama endpoint.

### 6.3 LocalLlamaCpp (stub)

In the current plugin:

* `SendViaLocalLlamaCpp` simply logs:

  > `LocalLlamaCpp backend is not wired yet; falling back to Gateway.`

* Then internally calls `SendViaGateway`.

The idea is:

* You or a future version of the project can integrate real llama.cpp here.
* The plugin already sets up the enum and call site so gameplay code doesn’t change.

See `ThirdParty/LlamaCpp/README.txt` for guidance if you want to implement
native llama.cpp.

---

## 7. Troubleshooting

### “VRSecretary module could not be found” / plugin doesn’t compile

Check:

1. Folder structure:

   ```text
   YourProject/
     Plugins/
       VRSecretary/
         VRSecretary.uplugin
         Source/VRSecretary/...
   ```

2. You regenerated project files after copying the plugin.

3. You are building **Development Editor** | **Win64**.

If you still have errors, look at the first red C++ error in Visual Studio’s
**Error List** and adjust accordingly.

### Gateway mode: no response or error

* Verify gateway is running and reachable:

  * `curl http://localhost:8000/health`
  * `curl -X POST http://localhost:8000/api/vr_chat -H "Content-Type: application/json" -d '{"session_id":"test","user_text":"Hello","language":"en"}'`

* Check `GatewayUrl` in project settings.

* Confirm environment variables (`MODE`, `OLLAMA_BASE_URL`, `CHATTERBOX_URL`,
  `CHATTERBOX_DEVICE`, etc.) in your `.env`.

### DirectOllama: “choices” missing or JSON parse error

* Confirm your endpoint returns a valid OpenAI Chat Completions response.
* Make sure the URL & model name match your setup.
* Try a raw `curl` to the endpoint to inspect the payload.

### Imported character appears dark / almost black

That’s not plugin-specific, but common after importing GLB/FBX:

* Make sure there is at least one **light** in the level (DirectionalLight,
  SkyLight, RectLight, etc.).

* Double-check the material:

  * If the model uses unlit / very dark base color, tweak the material instance.

* Try **Lit** vs **Unlit** viewport modes to diagnose lighting/material issues.

### Audio is always English, even when language is set

* Confirm that:

  * The plugin is actually sending `language` in the JSON body (check logs or use a proxy).
  * The gateway `VRChatRequest` model has an optional `language` field and forwards it.
  * The multilingual Chatterbox TTS server is using the `language` field (e.g. `language_id` parameter).
  * The text you send matches the target language (Italian text + `language="it"`, etc.).

---

## 8. Extending the Plugin

The plugin is intentionally thin and focused:

* One Blueprint component
* Clear backends:

  * Gateway (multilingual TTS capable)
  * DirectOllama
  * LocalLlamaCpp stub

You can extend it by:

* Adding new `EVRSecretaryBackendMode` entries and implementations.
* Supporting streaming responses (Server-Sent Events / websockets) in DirectOllama.
* Plugging in a native llama.cpp implementation for LocalLlamaCpp.
* Adding a separate TTS HTTP call for DirectOllama/LocalLlamaCpp to get audio.
* Surfacing more TTS parameters to Blueprints (voice selection, speaking rate, etc.).

Because **all** Unreal gameplay code talks only to `UVRSecretaryComponent`, you
can swap or upgrade backends without changing Blueprints.

---

With the plugin configured, the gateway running, and the multilingual TTS server online, your loop is:

> **Player input → VRSecretaryComponent.SendUserText (with language) →
> Backend (Gateway / DirectOllama / LocalLlamaCpp stub) →
> OnAssistantResponse → Update avatar text & voice in the chosen language**

That gives you a flexible, multilingual VR secretary that can live in English, Italian, or any other supported language without changing your gameplay logic.
