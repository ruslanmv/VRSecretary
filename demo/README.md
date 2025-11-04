# VRSecretary – End-to-End Example (Oculus Quest 3)

This example explains, **step by step**, how to go from a fresh clone of **VRSecretary** to **talking with Ailey** (your VR Secretary) in **Unreal Engine 5** using an **Oculus Quest 3**.

It assumes:

- You are on **Windows 10/11** (recommended for UE + Oculus).
- You have an **NVIDIA GPU** (for LLM/TTS performance).
- You’re comfortable with a terminal (PowerShell or CMD) and basic Unreal usage.

---

## 0. Overview: What You’ll Run

You’ll run **four main pieces**:

1. **Ollama** – local LLM server (e.g. `llama3`).
2. **Chatterbox TTS** – local text-to-speech server.
3. **VRSecretary Gateway** – FastAPI backend that glues LLM + TTS together.
4. **Unreal Engine** – VR project with the `VRSecretary` plugin + avatar.

Your Oculus Quest 3 connects to the PC via **Link** or **Air Link**, and Unreal runs in **VR Preview**.

---

## 1. Prerequisites

### 1.1 Hardware

- Windows PC with:
  - Quad-core CPU or better
  - **16 GB RAM** minimum (32 GB recommended)
  - **NVIDIA GPU** with recent drivers
- **Oculus Quest 3** + USB-C cable (Link) or good Wi-Fi (Air Link)

### 1.2 Software

Install these before you start:

1. **Oculus PC App**
   - Download and install from Meta.
   - Log in and set up your **Quest 3** for **Link / Air Link**.

2. **Unreal Engine 5.3+**
   - Install via Epic Games Launcher.
   - Add **C++** support (Visual Studio 2022 with “Game development with C++” workload).

3. **Python 3.11**
   - Install Python 3.11 from python.org.
   - Check with:
     ```bash
     py -3.11 -V
     ```
     or
     ```bash
     python3.11 -V
     ```

4. **Git**
   - Any recent version.

5. **Ollama**
   - Install from: https://ollama.com/download

6. **Chatterbox TTS**
   - Follow the install instructions from:
     https://github.com/rsxdalv/chatterbox

---

## 2. Clone the Repository

Open **PowerShell** or **CMD** and run:

```bash
git clone https://github.com/yourusername/VRSecretary.git
cd VRSecretary
````

(Replace the URL with your actual repo when you host it.)

---

## 3. Backend Setup (LLM + TTS + Gateway)

We’ll use the **Makefile** at the repo root to set up a Python virtual environment and install the backend.

### 3.1 Create the virtual environment and install everything

From the repo root:

```bash
# Ensure you’re in VRSecretary/
make install
```

This will:

* Create `.venv` (Python 3.11 venv)
* Install the root “simple-environment” (Jupyter + Ollama Python client)
* Install the **VRSecretary backend** (`backend/gateway`)
* Register a Jupyter kernel (optional but handy)
* Check/install **Ollama** on the host (best effort)
* Try to start the Ollama server

> If `make` isn’t available on your system, install it (e.g. `choco install make`, or use Git Bash where `make` is often included).

### 3.2 Configure backend environment

Go to the backend folder:

```bash
cd backend/gateway
```

Copy the example `.env`:

```bash
cp ../docker/env.example .env
```

Edit `.env` so it contains at least:

```env
MODE=offline_local_ollama

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

CHATTERBOX_URL=http://localhost:4123
CHATTERBOX_TIMEOUT=30.0
```

Save the file.
Go back to repo root when done:

```bash
cd ../..
```

### 3.3 Start Ollama and pull a model

In **Terminal 1** (PowerShell or CMD):

```bash
ollama serve
```

Then pull a model:

```bash
ollama pull llama3
```

You can check:

```bash
curl http://localhost:11434/v1/models
```

> Make sure the name matches `OLLAMA_MODEL` in `.env` (e.g., `llama3`).

### 3.4 Start Chatterbox TTS

In **Terminal 2**:

```bash
chatterbox-server --port 4123
```

To verify TTS:

```bash
curl -X POST http://localhost:4123/v1/audio/speech ^
  -H "Content-Type: application/json" ^
  -d "{ \"input\": \"Hello from Ailey\", \"temperature\": 0.6, \"cfg_weight\": 0.5, \"exaggeration\": 0.35 }" ^
  --output test.wav
```

Play `test.wav` to ensure the voice works.

### 3.5 Start VRSecretary Gateway

In **Terminal 3**, at the repo root:

```bash
make run-gateway
```

or manually:

```bash
cd backend/gateway
..\..\.\.venv\Scripts\python.exe -m uvicorn vrsecretary_gateway.main:app --host 0.0.0.0 --port 8000
```

Check that it’s up:

```bash
curl http://localhost:8000/health
```

You should see JSON like:

```json
{ "status": "ok", "mode": "offline_local_ollama", ... }
```

Optional: test full chat:

```bash
curl -X POST http://localhost:8000/api/vr_chat ^
  -H "Content-Type: application/json" ^
  -d "{ \"session_id\": \"quest3-test\", \"user_text\": \"Hello Ailey, who are you?\" }"
```

If you see `assistant_text` and `audio_wav_base64` in the response, the backend is ready.

---

## 4. Oculus Quest 3: PC & OpenXR Setup

Before opening Unreal, make sure your VR runtime is correct.

1. **Open the Oculus PC app**

   * Log in.
   * Connect your Quest 3 either with **Link cable** or enable **Air Link**.

2. **Set Oculus as OpenXR runtime**

   * In Oculus app: go to **Settings → General / Beta** (depending on version).
   * Find the **OpenXR** toggle or button and set Oculus as the **active OpenXR runtime**.

3. Put on the headset and ensure you can see the **PC desktop** via Link/Air Link.

---

## 5. Unreal Engine – Sample Project Setup

We’ll use the provided **demo project** so you don’t have to wire everything manually at first.

### 5.1 Open the sample project

1. In File Explorer, go to:

   ```text
   VRSecretary/samples/unreal-vr-secretary-demo/
   ```

2. Right-click `VRSecretaryDemo.uproject` →
   **Generate Visual Studio project files**.

3. Double-click `VRSecretaryDemo.uproject` to open it in **Unreal Engine 5.3+**.

4. When prompted, let Unreal build the C++ code (including the `VRSecretary` plugin).

### 5.2 Check the VRSecretary plugin

In Unreal:

1. Go to **Edit → Plugins**.
2. Search for **VRSecretary**.
3. Make sure it’s **enabled** (tick the checkbox).
4. Restart the editor if prompted.

### 5.3 Configure VRSecretary plugin settings

In Unreal:

1. Go to **Edit → Project Settings**.
2. In the left-hand panel, find **Plugins → VRSecretary**.
3. Set:

   * **Gateway URL**: `http://localhost:8000`
   * **Backend Mode**: `Gateway (Ollama)` (or equivalent wording)
   * **HTTP Timeout**: e.g. `60.0`

This tells the Unreal plugin where your FastAPI backend is running.

---

## 6. Avatar (Scifi Girl v.01) Setup

The repo includes a **sample avatar**:

```text
assets/avatars/scifi_girl_v01/scifi_girl_v.01.glb
```

> If the GLB is missing, download it from Sketchfab as described in `assets/avatars/scifi_girl_v01/README.md` and place it there.

### 6.1 Import the GLB into the demo project

In Unreal:

1. Open the **Content Browser**.
2. Choose or create a folder, e.g. `/Game/Characters/ScifiGirl/`.
3. Click **Import**.
4. Select `VRSecretary/assets/avatars/scifi_girl_v01/scifi_girl_v.01.glb`.
5. In the import dialog:

   * Enable **Skeletal Mesh**.
   * Enable **Import Materials** and **Import Textures**.
   * Use a new or existing humanoid skeleton.

After import you should have:

* `SK_ScifiGirl` (skeletal mesh)
* Skeleton
* Materials & textures

### 6.2 Link the avatar in the sample blueprint

The demo project should include a blueprint like `BP_SecretaryAvatar` (name may vary).

1. Open `BP_SecretaryAvatar`.
2. Select the **Skeletal Mesh Component**.
3. In details, set **Skeletal Mesh** to `SK_ScifiGirl`.
4. Compile and save.

Now your VR Secretary has a body. 😄

---

## 7. VR Secretary Component & Blueprints (High Level)

The demo project is set up roughly like this:

* **Actor:** `BP_VRSecretaryManager`

  * Has a `VRSecretaryComponent` attached.
  * Handles user input (e.g., controller button).
  * Calls `SendUserText(UserText, ChatConfig)` on the component.
  * Binds `OnAssistantResponse` → calls avatar’s `OnNewAssistantText(AssistantText, AudioBase64)`.

* **Actor:** `BP_SecretaryAvatar`

  * Placed in front of the player in the level.
  * Has Skeletal Mesh, Audio Component, and a Subtitles Widget.
  * Implements `OnNewAssistantText` to:

    * Update subtitles.
    * Decode `audio_wav_base64` (optional but recommended with Runtime Audio Importer plugin).
    * Play voice audio.

As long as the sample project is intact and the plugin compiled successfully, you shouldn’t need to rewire these manually for your first test.

---

## 8. Run in VR on Oculus Quest 3

With everything above running:

1. **Backend services**:

   * Terminal 1: `ollama serve`
   * Terminal 2: `chatterbox-server --port 4123`
   * Terminal 3: `make run-gateway` (or uvicorn command)

2. **Oculus Quest 3**:

   * Oculus PC app open.
   * Quest 3 connected via Link / Air Link.
   * OpenXR runtime set to Oculus.

3. **Unreal**:

   * `VRSecretaryDemo.uproject` open.
   * Level with `BP_SecretaryAvatar` and `BP_VRSecretaryManager` loaded.
   * `VRSecretary` plugin enabled and configured.

### 8.1 Start VR Preview

In Unreal:

1. Click the **Play** dropdown (top toolbar).
2. Choose **VR Preview**.
3. Put on your Quest 3 – you should see the level.

### 8.2 Talk to Ailey

Depending on the blueprint setup (in the sample):

* A specific **controller button** (e.g. Right Grip or Trigger) may open a text input UI or send a preset phrase.
* Once you send a message, you should see Ailey:

  * Respond via **subtitles**.
  * Speak via **Chatterbox TTS** (if audio decoding is wired in).

If you only see text and no audio, that usually means the blueprint is not yet decoding base64 audio into a `USoundWave`. You can:

* Still test the conversation via subtitles, and
* Later install **Runtime Audio Importer** or a similar plugin and wire it up.

---

## 9. Common Pitfalls

* **VR Preview is greyed out**

  * Unreal doesn’t see a valid VR runtime/headset.
  * Check Oculus app, Link/Air Link, and OpenXR runtime.

* **Gateway errors in Unreal**

  * Check `Gateway URL` in Project Settings.
  * Ensure backend is running and `http://localhost:8000/health` works.

* **No LLM response / timeouts**

  * Confirm `ollama serve` is running and `ollama pull llama3` succeeded.
  * Check `.env` has the correct `OLLAMA_BASE_URL` and `OLLAMA_MODEL`.

* **Silent avatar (no voice)**

  * Chatterbox not running, or
  * Blueprint not decoding `audio_wav_base64`.

---

## 10. Summary

Once this example is set up, you can:

* Use it as a **reference template** for your own VR projects.
* Swap in different LLMs via **Ollama** or **watsonx.ai**.
* Replace the avatar with your own character for commercial use.
* Extend blueprints to support gestures, UI panels, or advanced interactions.
