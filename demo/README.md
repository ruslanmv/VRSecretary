# VRSecretary – Simple End‑to‑End Demo (Oculus Quest 3)

This folder contains a step‑by‑step demo that shows you how to talk with
your VR secretary (Ailey) in Unreal Engine 5 using an Oculus Quest 3.

The goal is to make this as simple as possible, even if you are not an IT
expert. Just follow the steps in order.

---

## 1. What You Will Get

When you finish this guide you will be able to:

* Put on your Quest 3.
* Start the Unreal demo project.
* Talk to Ailey, your VR secretary.
* Hear her answer with a natural‑sounding voice.

Behind the scenes, a few programs will be running on your PC, but the
Makefile and this guide will set them up for you.

---

## 2. What You Need

### 2.1 Hardware

* A Windows 10 or 11 PC, or a Linux/macOS machine (most testing has been on Windows).
* An NVIDIA GPU is recommended (for faster AI and voice), but not strictly required.
* An Oculus Quest 3 with a USB‑C cable or Air Link enabled.

### 2.2 Software (install once)

Please install these before you continue:

1. **Unreal Engine 5.3 or newer**

   * Install from the Epic Games Launcher.
   * When installing, enable the C++ game development option.
   Unreal and a C++ toolchain are required to open and run the demo project.

   **Install the Epic Games Launcher**

   * Go to the official Unreal download page:  
     <https://www.unrealengine.com/en-US/download>
   * Download and run the **Epic Games Launcher** installer for your platform.
   * When prompted, sign in or create a free Epic Games account.

   **Install Unreal Engine 5.3+ from the Launcher**

   * Open the **Epic Games Launcher**.
   * In the left sidebar, click **Unreal Engine → Library**.
   * Under **Engine Versions**, click the small `+` button to add a new version.
   * Choose **5.3** or any newer 5.x version (5.3, 5.4, 5.5, 5.6, etc.).
   * Click **Install**, choose an install location, and wait for the download to finish.

   **Install C++ build tools for Unreal (Windows only)**

   Unreal C++ projects (like this demo) need Visual Studio or similar C++ tools.

   * Download **Visual Studio Community 2022** (free) from:  
     <https://visualstudio.microsoft.com/vs/community/>
   * Run the installer and, in the **Workloads** tab, enable:
     * **Game development with C++**
   * Make sure the default optional components stay checked (Windows 10/11 SDK, C++ tools,
     and Visual Studio tools for Unreal Engine).
   * Finish the installation and reboot if requested.

   If you are new to Unreal, the official “Install Unreal Engine” and “Getting Started” docs
   are useful:

   * Install guide: <https://dev.epicgames.com/documentation/en-us/unreal-engine/install-unreal-engine>  
   * Getting started: <https://dev.epicgames.com/documentation/en-us/unreal-engine/get-started>

2. **Git**

   * Download from [https://git-scm.com/downloads](https://git-scm.com/downloads)
   * On Windows, this gives you Git Bash, which is useful but not required if you use PowerShell.

3. **Python 3.11**

   The Makefile assumes Python 3.11:

   * On Windows, install Python 3.11 from [https://www.python.org/downloads/](https://www.python.org/downloads/)
     and make sure the `py -3.11` launcher works.
   * On Linux/macOS, install Python 3.11 with your package manager or from python.org,
     and make sure `python3.11` is available.

4. **Ollama**

   Ollama runs the LLM that Ailey uses.

   * Download from [https://ollama.com/download](https://ollama.com/download)
   * After installation, open a terminal and run once:

     ```bash
     ollama pull llama3
     ```

   The Makefile will try to start Ollama for you, but it is still a good
   idea to confirm it runs once manually.

5. **Chatterbox (TTS – Text‑To‑Speech)**

   This provides the voice for Ailey.

   * Go to: [https://github.com/rsxdalv/chatterbox](https://github.com/rsxdalv/chatterbox)
   * Follow the "Getting started" instructions to install it.
   * You only need the basic `chatterbox-server` command working.

6. **Make** (recommended but optional)

   The easiest way to set up and run the demo is with the provided Makefile.

   * On Linux/macOS, `make` is usually already installed.
   * On Windows you can get `make` via:

     * Chocolatey: `choco install make`, or
     * MSYS2 / Git for Windows SDK, or
     * Your favorite package manager.

   If you really cannot install `make`, you can still use the legacy
   script `demo/install.sh` from Git Bash (see below).

---

## 3. Get the Project

Open a terminal:

* On Windows: PowerShell or Git Bash
* On Linux/macOS: your usual shell

Then run:

```bash
git clone https://github.com/ruslanmv/VRSecretary.git
cd VRSecretary
```

If you already have the repo, just go to its folder:

```bash
cd path/to/VRSecretary
```

---

## 4. One‑Time Backend Setup (easy mode)

You only need to do this once on each machine.

### 4.1 Option A: Use `make install` (recommended)

From the `VRSecretary` root folder, run:

```bash
make install
```

This will:

* Create a Python virtual environment in `.venv`.
* Sync dependencies from `pyproject.toml` into `.venv` using `uv`.
* Install the VRSecretary backend (`backend/gateway`) into the same venv.
* Register a Jupyter kernel named `Python 3.11 (VRSecretary)`.
* Try to install and/or start Ollama on the host (best effort).

The command is the same on all platforms:

* Windows (PowerShell):

  ```powershell
  cd C:\path\to\VRSecretary
  make install
  ```

* Linux/macOS:

  ```bash
  cd /path/to/VRSecretary
  make install
  ```

If the automatic Ollama installation fails, just install Ollama
manually from [https://ollama.com/download](https://ollama.com/download) and rerun `make install`.

### 4.2 Option B: Legacy script (if you cannot use `make`)

If you cannot install `make`, you can still run the old helper script
from Git Bash or any POSIX shell:

```bash
bash demo/install.sh
```

This script will:

* Create a Python virtual environment for the backend.
* Install the FastAPI gateway and its dependencies.
* Create a default configuration file (`.env`) for the gateway.
* Apply the Unreal plugin patch so the VRSecretary plugin is up to date.

You do not need to run both `make install` and `demo/install.sh`. Pick one.

---

## 5. Start the AI Services (every time you want to use Ailey)

Each time you want to use the demo, you will typically have three
processes running:

* Ollama (the model / brain)
* Chatterbox (the TTS voice)
* VRSecretary backend (the controller / HTTP API)

You can use PowerShell, CMD, or Git Bash on Windows, and your usual
shell on Linux/macOS.

### 5.1 Start Ollama

If `make install` completed successfully, Ollama may already be running.
If not, open a terminal and run:

```bash
ollama serve
```

Leave this window open.

To confirm it is working, you can test:

```bash
curl http://127.0.0.1:11434/api/tags
```

### 5.2 Start Chatterbox

Open a second terminal and run:

```bash
chatterbox-server --port 4123
```

Leave this window open too.

### 5.3 Start the VRSecretary backend

You can start the backend either with `make` or manually.

#### Option A: Use `make run-gateway` (recommended)

From the `VRSecretary` root folder:

```bash
make run-gateway
```

This will:

* Ensure the virtual environment exists.
* Ensure the backend is installed into `.venv`.
* Start `uvicorn` with the VRSecretary gateway application on port 8000.

You should see log messages like:

```text
Uvicorn running on http://0.0.0.0:8000
```

#### Option B: Start the backend manually

If you want to run the commands yourself:

```bash
cd path/to/VRSecretary

# Activate the virtual environment
# On Windows PowerShell:
#   .venv\Scripts\Activate.ps1
# On Linux/macOS or Git Bash:
#   source .venv/bin/activate

# Start the FastAPI gateway
uvicorn vrsecretary_gateway.main:app --host 0.0.0.0 --port 8000
```

To test that it works, open a browser and go to:

* [http://localhost:8000/docs](http://localhost:8000/docs) – you should see the API docs.

---

## 6. Open the Unreal Demo Project

1. Make sure Unreal Engine 5.3 or newer is installed.

2. In your file explorer, go to:

   ```text
   VRSecretary/samples/unreal-vr-secretary-demo/
   ```

3. Right‑click `VRSecretaryDemo.uproject` and choose:

   "Generate Visual Studio project files" (first time only).

4. Double‑click `VRSecretaryDemo.uproject` to open the project in Unreal.

5. Let Unreal compile the C++ modules if it asks you.

---

## 7. Check the VRSecretary Plugin Settings

In Unreal:

1. Go to `Edit -> Plugins`.
2. Search for `VRSecretary` and make sure it is enabled.
3. Then go to:

   `Edit -> Project Settings -> Plugins -> VRSecretary`

   Set:

   * `Gateway URL`: `http://localhost:8000`
   * `Backend Mode`: `Gateway (Ollama)`
   * `HTTP Timeout`: `60.0` (default is fine)

These settings tell the game how to reach the backend you started earlier.

---

## 8. Connect Your Oculus Quest 3

1. Plug in your Quest 3 with a USB‑C cable or use Air Link.
2. Make sure Link or Air Link is active so the headset is connected to your PC.
3. In Unreal, click the small VR headset icon (top‑right) if needed to enable VR.

---

## 9. Talk to Ailey in VR

Now the fun part:

1. In Unreal, click `Play` and choose `VR Preview`.
2. Put on your Quest 3.
3. Use the provided input (controller button or UI) to send a message.
4. You should:

   * See Ailey’s answer as text (subtitles).
   * Hear her reply with audio (if Chatterbox and the gateway are running).

If you do not hear sound, check:

* Is `chatterbox-server` running?
* Is the backend terminal showing errors?
* Is the Blueprint that decodes `audio_wav_base64` connected?

---

## 10. Stopping Everything

When you are done:

1. Close the Unreal editor.
2. In each terminal, press `Ctrl + C` to stop:

   * `uvicorn` (backend)
   * `chatterbox-server`
   * `ollama serve`

You can start them again any time by following Section 5.

---

## 11. Makefile Quick Reference

Some useful Make targets from the project root:

* `make install`

  * One‑time setup: create `.venv`, install dependencies, backend, and Jupyter kernel, and try to install/start Ollama.

* `make run-gateway`

  * Start the VRSecretary FastAPI gateway using the virtual environment.

* `make pull-model`

  * Pull a small model (example) for quick tests via Ollama.

* `make notebook`

  * Ensure Jupyter is installed in the venv and register the `VRSecretary` kernel.

* `make test`

  * Run Python tests.

* `make clean`

  * Remove Python caches and the virtual environment.

You do not need all of these for the basic demo, but they are useful if
you want to develop further.

---

## 12. Summary

You now have:

* A working VR secretary in Unreal Engine 5.
* A clear way to start and stop:

  * the AI model (Ollama),
  * the voice (Chatterbox),
  * and the controller backend (FastAPI gateway).

From here, you can:

* Change Ailey’s personality in the backend.
* Replace the avatar with your own model.
* Use the same backend API from other engines (like Unity) if you want.

For more technical details, check the main project `README.md` and the
docs in the `docs/` folder.
