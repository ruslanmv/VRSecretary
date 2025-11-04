#!/usr/bin/env bash
set -e

echo "Starting VRSecretary local stack (ollama + gateway)..."
# Example:
# 1) Start Ollama: `ollama serve` (in another terminal)
# 2) Start Chatterbox: `chatterbox-server --port 4123` (in another terminal)
# 3) Start gateway:
cd "$(dirname "$0")/../../backend/gateway"
uvicorn vrsecretary_gateway.main:app --host 0.0.0.0 --port 8000
