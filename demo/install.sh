#!/usr/bin/env bash
#
# demo/install.sh
#
# Friendly helper script for the VRSecretary demo.
#
# This script uses the top-level Makefile to do most of the work for you:
#
#   - Creates a Python virtual environment
#   - Installs all Python dependencies (root + VRSecretary backend)
#   - Installs & checks Ollama (best effort)
#   - Registers a Jupyter kernel (optional, for notebooks)
#
# It is meant for **non-technical** users. Just run it from:
#   - macOS / Linux: any bash-capable terminal
#   - Windows: Git Bash (installed with Git for Windows)
#
# Requirements (installed once):
#   - Git (for Git Bash on Windows)
#   - Python 3.11 (or compatible, as configured in the Makefile)
#   - The VRSecretary repo checked out
#
# This script does NOT:
#   - Install Unreal Engine (you do that via Epic Games Launcher)
#   - Install Chatterbox (see the main README for that)
#   - Start the servers automatically every time (see the end of the script for next steps)
#

set -euo pipefail

# ---------------------------------------------------------------------------
# Locate the repo root (folder that contains the Makefile)
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "==============================================="
echo " VRSecretary Demo - One-Time Setup (Makefile) "
echo "==============================================="
echo
echo " Script location : ${SCRIPT_DIR}"
echo " Repo root       : ${ROOT}"
echo

cd "${ROOT}"

# ---------------------------------------------------------------------------
# Check that the Makefile exists and that 'make' is available
# ---------------------------------------------------------------------------

if [[ ! -f "Makefile" ]]; then
  echo "❌ I could not find a Makefile in: ${ROOT}"
  echo "   Please make sure you are inside the VRSecretary repository."
  exit 1
fi

if ! command -v make >/dev/null 2>&1; then
  echo "❌ The 'make' command is not available on this system."
  echo
  echo "On Windows:"
  echo "  - Make sure you installed Git for Windows."
  echo "  - Use the Git Bash terminal to run this script."
  echo "  - If 'make' is still missing, install it via your package manager"
  echo "    (for example: MSYS2, Chocolatey, or similar)."
  echo
  echo "On macOS / Linux:"
  echo "  - Install build tools, e.g. 'xcode-select --install' on macOS,"
  echo "    or 'sudo apt install build-essential' on Ubuntu."
  echo
  echo "After that, run this script again:"
  echo "  bash demo/install.sh"
  exit 1
fi

# ---------------------------------------------------------------------------
# Run the main Makefile targets
# ---------------------------------------------------------------------------

echo "▶️  Step 1/2: Creating the Python environment and installing backend..."
echo "    (This uses 'make install' from the repo root.)"
echo

# 'make install' will:
#   - Create a virtualenv (.venv) if needed
#   - Sync dependencies via uv (or pip fallback)
#   - Install the VRSecretary backend
#   - Register a Jupyter kernel
#   - Try to install & start Ollama (best effort)
make install

echo
echo "✅ Step 1 done! The Python environment and backend are installed."
echo

echo "▶️  Step 2/2: Applying the Unreal VRSecretary plugin patch (if available)..."
echo "    (This uses 'make patch-plugin'. If the patch script is missing, it's ok.)"
echo

make patch-plugin || echo "ℹ️ Plugin patch step skipped (no patch script found or patch failed)."

echo
echo "==============================================="
echo "  VRSecretary Demo - Setup Finished            "
echo "==============================================="
cat <<'EOF'

What was done for you:

  - A Python virtual environment (.venv) was created in the repo.
  - The VRSecretary backend (FastAPI gateway) was installed into that venv.
  - A Jupyter kernel "Python 3.11 (VRSecretary)" was registered (optional use).
  - Ollama was checked/installed (best effort) and tested, if possible.
  - The VRSecretary Unreal plugin was patched to the latest structure.

You are now ready to start the demo.

NEXT STEPS (every time you want to use Ailey):

  1) Start the AI model (Ollama)
     -----------------------------
     Open a terminal and run:

       ollama serve

     Leave that window open.

  2) Start Chatterbox (voice)
     ------------------------
     Open a second terminal and run (adjust path/command if needed):

       chatterbox-server --port 4123

     Again, leave that window open.

  3) Start the VRSecretary backend (FastAPI)
     ---------------------------------------
     From the root of the repo, you now have two options:

     a) EASY MODE – using make (recommended)
        ------------------------------------
        From the repo root (where the Makefile is), run:

          make run-gateway

        This will start the FastAPI gateway on:
          http://0.0.0.0:8000

     b) MANUAL MODE – using Python directly
        -----------------------------------
        If you prefer, you can activate the virtualenv and run uvicorn yourself:

          # On macOS / Linux / Git Bash:
          source .venv/bin/activate

          # On Windows PowerShell:
          #   .venv\Scripts\Activate.ps1

          cd backend/gateway
          uvicorn vrsecretary_gateway.main:app --host 0.0.0.0 --port 8000

  4) Open the Unreal demo project
     ----------------------------
       - In File Explorer:
           VRSecretary/samples/unreal-vr-secretary-demo/
       - Right-click VRSecretaryDemo.uproject:
           "Generate Visual Studio project files" (first time only)
       - Double-click VRSecretaryDemo.uproject to open in Unreal.
       - In Unreal:
           * Edit → Plugins → find "VRSecretary" and enable it if needed.
           * Edit → Project Settings → Plugins → VRSecretary:
               - Gateway URL:  http://localhost:8000
               - Backend Mode: Gateway (Ollama)
               - HTTP Timeout: 60.0 (default)

  5) Put on your VR headset (Quest 3)
     --------------------------------
       - Connect via USB or Air Link.
       - In Unreal, click "VR Preview".
       - Use the provided controls in the demo to talk to Ailey.

If something does not work, check:

  - That ollama, chatterbox, and the FastAPI backend are all running.
  - That the Gateway URL is correct in Unreal settings.
  - The terminal windows for error messages.

You can re-run this install script at any time if you change machines or
delete the .venv folder.

Enjoy building with Ailey, your VR secretary! 🤖🎧

EOF
