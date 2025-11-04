# VRSecretary – Simple End-to-End Demo (Oculus Quest 3)

This folder contains a **step‑by‑step demo** that shows you how to talk with
your **VR secretary (Ailey)** in **Unreal Engine 5** using an **Oculus Quest 3**.

The goal is to make this as simple as possible, even if you are **not an IT
expert**. Just follow the steps in order.

---

## 1. What You Will Get

When you finish this guide you will be able to:

- Put on your **Quest 3**.
- Start the Unreal demo project.
- Talk to **Ailey**, your VR secretary.
- Hear her answer with a natural‑sounding voice.

Behind the scenes, a few programs will be running on your PC, but the script
and this guide will set them up for you.

---

## 2. What You Need

### 2.1 Hardware

- A **Windows 10 or 11 PC**.
- An **NVIDIA GPU** is recommended (for faster AI and voice).
- An **Oculus Quest 3** with a USB‑C cable or Air Link enabled.

### 2.2 Software (install once)

Please install these before you continue:

1. **Unreal Engine 5.3 or newer**

   - Install from the **Epic Games Launcher**.
   - When installing, enable the **C++ game development** option.

2. **Git**

   - Download from <https://git-scm.com/downloads>.
   - On Windows, this gives you **Git Bash**, which we will use to run scripts.

3. **Python 3.10 or newer**

   - Download from <https://www.python.org/downloads/>.
   - During installation on Windows, **check the box “Add Python to PATH”**.

4. **Ollama**

   - Download from <https://ollama.ai/>.
   - After installation, open a terminal and run once:

     ```bash
     ollama pull llama3
     ```

   - This downloads the AI model that Ailey will use.

5. **Chatterbox (TTS – Text‑To‑Speech)**

   - Go to: <https://github.com/rsxdalv/chatterbox>
   - Follow the “Getting started” instructions to install it.
   - You only need the basic **chatterbox-server** command working.

Once these are installed one time, you don’t need to repeat those installs.

---

## 3. Get the Project

Open **Git Bash** (right‑click inside the folder where you want the project and choose “Git Bash Here”), then run:

```bash
git clone https://github.com/ruslanmv/VRSecretary.git
cd VRSecretary
```

If you already have the repo, just go to its folder:

```bash
cd path/to/VRSecretary
```

---

## 4. Run the Auto‑Setup Script (easy mode)

Inside the `VRSecretary` folder, run:

```bash
bash demo/install.sh
```

This script will:

1. Create a **Python virtual environment** for the backend.
2. Install the **FastAPI gateway** and its dependencies.
3. Create a default **configuration file** (`.env`) for the gateway.
4. Apply the **Unreal plugin patch** so the `VRSecretary` plugin is up to date.

It will **not** start the servers permanently (you will do that in the next step),
but it will make sure everything is installed correctly.

If something goes wrong, the script will show an error message. In that case,
double‑check that Python is installed and try again.

---

## 5. Start the AI Services (every time you want to use Ailey)

You will usually keep three terminals open:

- One for **Ollama** (the brain).
- One for **Chatterbox** (the voice).
- One for the **VRSecretary backend** (the controller).

You can use **PowerShell**, **CMD**, or **Git Bash** for these.

### 5.1 Start Ollama

Open a terminal and run:

```bash
ollama serve
```

Leave this window open.

### 5.2 Start Chatterbox

Open a **second** terminal and run:

```bash
chatterbox-server --port 4123
```

Leave this window open too.

### 5.3 Start the VRSecretary backend

Open a **third** terminal and run:

```bash
cd path/to/VRSecretary/backend/gateway

# On Windows PowerShell:
# .venv\Scripts\Activate.ps1
# On Git Bash:
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate

uvicorn vrsecretary_gateway.main:app --host 0.0.0.0 --port 8000
```

You should see log messages like:

```text
Uvicorn running on http://0.0.0.0:8000
```

To test that it works, open a browser and go to:

- <http://localhost:8000/docs> – you should see the API docs.

---

## 6. Open the Unreal Demo Project

1. Make sure **Unreal Engine 5.3+** is installed.
2. In **File Explorer**, go to:

   ```text
   VRSecretary/samples/unreal-vr-secretary-demo/
   ```

3. Right‑click `VRSecretaryDemo.uproject` and choose:

   > **Generate Visual Studio project files** (first time only)

4. Double‑click `VRSecretaryDemo.uproject` to open the project in Unreal.
5. Let Unreal compile the C++ modules if it asks you.

---

## 7. Check the VRSecretary Plugin Settings

In Unreal:

1. Go to **Edit → Plugins**.
2. Search for **VRSecretary** and make sure it is **enabled**.
3. Then go to:

   > **Edit → Project Settings → Plugins → VRSecretary**

   Set:

   - **Gateway URL:** `http://localhost:8000`
   - **Backend Mode:** `Gateway (Ollama)`
   - **HTTP Timeout:** `60.0` (default is fine)

These settings tell the game how to reach the backend you started earlier.

---

## 8. Connect Your Oculus Quest 3

1. Plug in your Quest 3 with a USB‑C cable **or** use **Air Link**.
2. Make sure **Link** or **Air Link** is active so the headset is connected to your PC.
3. In Unreal, click the small VR headset icon (top‑right) if needed to enable VR.

---

## 9. Talk to Ailey in VR

Now the fun part:

1. In Unreal, click **Play** and choose **VR Preview**.
2. Put on your Quest 3.
3. Use the provided input (controller button or UI) to send a message.
4. You should:
   - See Ailey’s answer as text (subtitles).
   - Hear her reply with audio (if Chatterbox and the gateway are running).

If you don’t hear sound, check:

- Is **Chatterbox** running?
- Is the backend terminal showing errors?
- Is the Blueprint that decodes `audio_wav_base64` connected?

---

## 10. Stopping Everything

When you are done:

1. Close the Unreal editor.
2. In each terminal, press **Ctrl + C** to stop:
   - `uvicorn` (backend)
   - `chatterbox-server`
   - `ollama serve`

You can start them again any time by following **Section 5**.

---

## 11. Summary

You now have:

- A working **VR secretary** in Unreal Engine 5.
- A clear way to start and stop:
  - the **AI model** (Ollama),
  - the **voice** (Chatterbox),
  - and the **controller backend** (FastAPI gateway).

From here, you can:

- Change Ailey’s personality in the backend.
- Replace the avatar with your own model.
- Use the same backend API from other engines (like Unity) if you want.

If you want more technical details, check the main project `README.md` and the
docs in the `docs/` folder.
