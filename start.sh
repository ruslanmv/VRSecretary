#!/usr/bin/env bash
#
# Start the full VRSecretary backend stack on Linux:
#   - Activate .venv
#   - Start Ollama (LLM) if not already running (can be skipped with --skip-ollama)
#   - Start Chatterbox TTS server
#   - Start FastAPI gateway
#
# Usage:
#   chmod +x start.sh
#   ./start.sh
#   ./start.sh --skip-ollama      # if Ollama is managed elsewhere

set -euo pipefail

# ------------------------------------------------------------------------------
# Parse arguments
# ------------------------------------------------------------------------------
SKIP_OLLAMA=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-ollama)
      SKIP_OLLAMA=true
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: $0 [--skip-ollama]" >&2
      exit 1
      ;;
  esac
done

# ------------------------------------------------------------------------------
# Resolve repo root (directory of this script)
# ------------------------------------------------------------------------------
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &>/dev/null && pwd )"
cd "$SCRIPT_DIR"

# ------------------------------------------------------------------------------
# Activate virtualenv
# ------------------------------------------------------------------------------
VENV_ACTIVATE="$SCRIPT_DIR/.venv/bin/activate"

if [[ ! -f "$VENV_ACTIVATE" ]]; then
  echo "ERROR: Virtualenv not found at .venv. Create it first (e.g. 'make install')." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$VENV_ACTIVATE"
echo "✓ Activated virtualenv: $VENV_ACTIVATE"

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

# ------------------------------------------------------------------------------
# Helper: Start Ollama if not running
# ------------------------------------------------------------------------------
start_ollama() {
  echo
  echo "=== Checking Ollama server ==="

  if ! command -v ollama >/dev/null 2>&1; then
    echo "WARNING: 'ollama' command not found in PATH. Skipping Ollama startup." >&2
    return
  fi

  if pgrep -x ollama >/dev/null 2>&1; then
    echo "Ollama process is already running."
  else
    echo "No Ollama process found. Starting 'ollama serve'..."
    # Runs in the background, logs to logs/ollama.log
    nohup ollama serve >"$LOG_DIR/ollama.log" 2>&1 &
    sleep 3
  fi

  # Check HTTP endpoint
  if command -v curl >/dev/null 2>&1; then
    local url="http://127.0.0.1:11434/api/tags"
    echo "Checking Ollama HTTP endpoint at $url ..."
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "✓ Ollama is reachable at $url"
    else
      echo "WARNING: Could not reach Ollama at $url" >&2
    fi
  fi
}

# ------------------------------------------------------------------------------
# Helper: Start Chatterbox TTS (background)
# ------------------------------------------------------------------------------
start_chatterbox_tts() {
  echo
  echo "=== Starting Chatterbox TTS server (tools/vr_chatterbox_server.py) ==="
  nohup python "$SCRIPT_DIR/tools/vr_chatterbox_server.py" \
    >"$LOG_DIR/tts.log" 2>&1 &
  echo "✓ Chatterbox TTS started (logs: $LOG_DIR/tts.log)"
}

# ------------------------------------------------------------------------------
# Helper: Start FastAPI Gateway (background)
# ------------------------------------------------------------------------------
start_gateway() {
  echo
  echo "=== Starting FastAPI gateway (vrsecretary_gateway.main:app) ==="
  (
    cd "$SCRIPT_DIR/backend/gateway"
    nohup uvicorn vrsecretary_gateway.main:app \
      --host 0.0.0.0 \
      --port 8000 \
      --http h11 \
      >"$LOG_DIR/gateway.log" 2>&1 &
  )
  echo "✓ Gateway started (logs: $LOG_DIR/gateway.log)"
  echo "  → Docs at: http://localhost:8000/docs"
}

# ------------------------------------------------------------------------------
# Main flow
# ------------------------------------------------------------------------------
echo "=== VRSecretary backend startup (Linux) ==="

if [[ "$SKIP_OLLAMA" == false ]]; then
  start_ollama
else
  echo "Skipping Ollama startup (--skip-ollama set)."
fi

start_chatterbox_tts
start_gateway

echo
echo "All backend services launched."
echo "  - Ollama (LLM)              → port 11434"
echo "  - Chatterbox TTS            → port 4123 (assuming default in your server)"
echo "  - VRSecretary FastAPI API   → http://localhost:8000"
echo
echo "Logs are in: $LOG_DIR"
