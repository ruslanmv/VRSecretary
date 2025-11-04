#!/usr/bin/env bash
#
# examples/install.sh
#
# Interactive helper to set up the VRSecretary backend environment.
# - Creates a .venv at the repo root (Python 3.11)
# - Installs root project (simple-environment)
# - Installs backend/gateway (with dev + watsonx extras if available)
# - Copies backend/docker/env.example to backend/gateway/.env (if missing)
#
# It does NOT start servers for you permanently; it prints next steps
# (ollama serve, chatterbox-server, uvicorn / make run-gateway).
#
# Works on:
#   - macOS / Linux (bash)
#   - Windows via Git Bash / WSL
#

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================="
echo " VRSecretary interactive installer"
echo " Repo root: $REPO_ROOT"
echo "============================================="
echo

cd "$REPO_ROOT"

# -------------------------------------------------------------
# Helper: prompt yes/no with default (Y/n or y/N)
# -------------------------------------------------------------
ask_yes_no() {
  local prompt="$1"
  local default="$2"  # "y" or "n"
  local reply

  while true; do
    if [[ "$default" == "y" ]]; then
      read -r -p "$prompt [Y/n] " reply || reply=""
      reply="${reply:-y}"
    else
      read -r -p "$prompt [y/N] " reply || reply=""
      reply="${reply:-n}"
    fi

    case "$reply" in
      [Yy]* ) return 0 ;;
      [Nn]* ) return 1 ;;
      * ) echo "Please answer y or n." ;;
    esac
  done
}

# -------------------------------------------------------------
# Detect a Python 3.11 interpreter
# -------------------------------------------------------------
detect_python() {
  local candidates=("python3.11" "python3" "py -3.11" "python")
  for cmd in "${candidates[@]}"; do
    if command -v ${cmd%% *} >/dev/null 2>&1; then
      # If it's "py -3.11", we accept as-is
      local ver
      if [[ "$cmd" == "py -3.11" ]]; then
        ver="$($cmd -V 2>&1 || true)"
      else
        ver="$($cmd -V 2>&1 || true)"
      fi
      if [[ "$ver" == *" 3.11."* ]]; then
        echo "$cmd"
        return
      fi
    fi
  done
  echo ""
}

PY_CMD="$(detect_python || true)"

if [[ -z "$PY_CMD" ]]; then
  echo "❌ Could not find a Python 3.11 interpreter automatically."
  read -r -p "Please type the command to run Python 3.11 (e.g. 'python3.11' or 'py -3.11'): " PY_CMD
fi

echo "Using Python: $PY_CMD"
echo

# -------------------------------------------------------------
# Optionally use Makefile if present
# -------------------------------------------------------------
if [[ -f "$REPO_ROOT/Makefile" ]] && command -v make >/dev/null 2>&1; then
  if ask_yes_no "Makefile detected. Use 'make install' to set up everything?" "y"; then
    echo
    echo "▶ Running: make install"
    echo
    (cd "$REPO_ROOT" && make install)
    echo
    echo "✅ Make-based installation complete."
    USE_MAKE=1
  else
    USE_MAKE=0
  fi
else
  USE_MAKE=0
fi

# -------------------------------------------------------------
# Manual install (if not using Makefile)
# -------------------------------------------------------------
if [[ "$USE_MAKE" -eq 0 ]]; then
  echo "---------------------------------------------"
  echo " Manual Python environment setup"
  echo "---------------------------------------------"
  echo

  VENV_DIR="$REPO_ROOT/.venv"

  if [[ -d "$VENV_DIR" ]]; then
    echo "ℹ️ Virtual environment already exists at .venv"
  else
    echo "Creating virtual environment at .venv with: $PY_CMD -m venv .venv"
    $PY_CMD -m venv "$VENV_DIR"
    echo "✅ Created .venv"
  fi

  # Figure out venv python path
  if [[ "$OSTYPE" == msys* || "$OSTYPE" == cygwin* ]]; then
    VENV_PY="$VENV_DIR/Scripts/python.exe"
    VENV_PIP="$VENV_DIR/Scripts/pip.exe"
  else
    VENV_PY="$VENV_DIR/bin/python"
    VENV_PIP="$VENV_DIR/bin/pip"
  fi

  echo
  echo "Upgrading pip..."
  "$VENV_PY" -m pip install --upgrade pip

  echo
  echo "Installing root project (simple-environment) into .venv..."
  "$VENV_PIP" install -e .

  if [[ -d "$REPO_ROOT/backend/gateway" ]]; then
    echo
    echo "Installing VRSecretary backend (backend/gateway) with dev + watsonx extras..."
    # If extras fail (e.g., no watsonx deps available), fall back gracefully.
    set +e
    "$VENV_PIP" install -e "backend/gateway[dev,watsonx]"
    if [[ $? -ne 0 ]]; then
      echo "⚠️ Could not install with [dev,watsonx] extras, trying without extras..."
      "$VENV_PIP" install -e "backend/gateway"
    fi
    set -e
  else
    echo "⚠️ backend/gateway not found, skipping backend install."
  fi

  echo
  echo "✅ Manual environment setup complete."
fi

# -------------------------------------------------------------
# Ensure backend .env exists
# -------------------------------------------------------------
BACKEND_DIR="$REPO_ROOT/backend/gateway"
ENV_EXAMPLE="$REPO_ROOT/backend/docker/env.example"
ENV_FILE="$BACKEND_DIR/.env"

echo
if [[ -d "$BACKEND_DIR" ]]; then
  if [[ -f "$ENV_FILE" ]]; then
    echo "ℹ️ backend/gateway/.env already exists."
  else
    if [[ -f "$ENV_EXAMPLE" ]]; then
      echo "Copying env.example to backend/gateway/.env..."
      cp "$ENV_EXAMPLE" "$ENV_FILE"
      echo "✅ Created backend/gateway/.env (please review and edit as needed)."
    else
      echo "⚠️ backend/docker/env.example not found; you will need to create backend/gateway/.env manually."
    fi
  fi
else
  echo "⚠️ backend/gateway directory not found; cannot set up .env."
fi

# -------------------------------------------------------------
# Final instructions
# -------------------------------------------------------------
cat <<'EOF'

=================================================
 ✅ VRSecretary backend environment is ready
=================================================

Next steps:

1) Start Ollama (LLM server) in a terminal:

   ollama serve
   ollama pull llama3

   Make sure the model name matches OLLAMA_MODEL in backend/gateway/.env.

2) Start Chatterbox TTS in another terminal:

   chatterbox-server --port 4123

3) Start the FastAPI gateway in a third terminal:

   # Option A (if Makefile is present):
   cd /path/to/VRSecretary
   make run-gateway

   # Option B (manual):
   cd /path/to/VRSecretary/backend/gateway
   ../../.venv/bin/python -m uvicorn vrsecretary_gateway.main:app --host 0.0.0.0 --port 8000

4) Test the gateway:

   curl http://localhost:8000/health

5) Open Unreal and load the sample project:

   - VRSecretary/samples/unreal-vr-secretary-demo/VRSecretaryDemo.uproject
   - Enable the VRSecretary plugin
   - Configure Project Settings → Plugins → VRSecretary:
       * Gateway URL: http://localhost:8000
       * Backend Mode: Gateway (Ollama)
   - Import / link the avatar as described in examples/README.md
   - Put on your Quest 3 and start "VR Preview"

You should now be able to talk with your VR Secretary (Ailey) in VR 🎧🤖

EOF
