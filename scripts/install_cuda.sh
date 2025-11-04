#!/usr/bin/env bash
# scripts/install_cuda.sh
#
# Install PyTorch CUDA wheels for this project.
# - On Linux/macOS: installs directly with pip.
# - On Windows: prints the PowerShell commands you should run.

set -euo pipefail

CUDA_INDEX_URL="https://download.pytorch.org/whl/cu121"

# Resolve project root as the parent of the "scripts" directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

os="$(uname -s)"

case "$os" in
  Linux|Darwin)
    echo "Detected OS: $os"
    echo "Using CUDA wheels index: $CUDA_INDEX_URL"
    echo "Installing project with [cuda] extra from: $PROJECT_ROOT"
    cd "$PROJECT_ROOT"

    # Set the index URL for this pip invocation only
    export PIP_INDEX_URL="$CUDA_INDEX_URL"

    # You can swap 'pip' for 'pip3' or 'python -m pip' if needed
    pip install ".[cuda]"

    echo "✅ CUDA-enabled torch/torchvision/torchaudio installed."
    ;;

  MINGW*|MSYS*|CYGWIN*)
    echo "Detected Windows / Git Bash environment."
    echo
    echo "Bash cannot set PowerShell environment variables directly."
    echo "Please open a *PowerShell* window in the project root and run:"
    echo
    echo '  $env:PIP_INDEX_URL = "https://download.pytorch.org/whl/cu121"'
    echo '  pip install ".[cuda]"'
    echo
    echo "This will install the CUDA builds of torch/torchvision/torchaudio for your GPU."
    ;;

  *)
    echo "❌ Unknown or unsupported OS: $os"
    echo "You can still manually run one of these:"
    echo
    echo "Linux/macOS:"
    echo "  export PIP_INDEX_URL=\"$CUDA_INDEX_URL\""
    echo '  pip install ".[cuda]"'
    echo
    echo "Windows PowerShell:"
    echo '  $env:PIP_INDEX_URL = "https://download.pytorch.org/whl/cu121"'
    echo '  pip install ".[cuda]"'
    exit 1
    ;;
esac
