#!/usr/bin/env bash
#
# install_unreal_helper.sh
#
# This script DOES NOT install Unreal Engine automatically.
# Epic requires you to use their installer and accept their license.
#
# Instead, it:
#   - Detects your OS
#   - Prints simple, step-by-step instructions
#   - Tries to open the Unreal / Epic Games download page in your browser
#
# Use it from the repo root:
#   bash tools/scripts/install_unreal_helper.sh
#

set -euo pipefail

detect_os() {
  case "$(uname -s)" in
    Darwin)
      echo "macOS"
      ;;
    Linux)
      echo "Linux"
      ;;
    MINGW*|MSYS*|CYGWIN*)
      echo "Windows"
      ;;
    *)
      echo "Unknown"
      ;;
  esac
}

open_url() {
  local url="$1"
  echo
  echo "➡️  If your browser does NOT open automatically, copy/paste this URL:"
  echo "    $url"
  echo

  # Try to open the URL depending on platform
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 || true
  elif command -v open >/dev/null 2>&1; then  # macOS
    open "$url" >/dev/null 2>&1 || true
  elif command -v start >/dev/null 2>&1; then # some Git Bash / Windows
    start "" "$url" >/dev/null 2>&1 || true
  else
    : # no-op
  fi
}

OS_NAME="$(detect_os)"

echo "==============================================="
echo " Unreal Engine 5.3+ Installation Helper"
echo " Detected OS: ${OS_NAME}"
echo "==============================================="
echo

UNREAL_URL="https://www.unrealengine.com/download"

case "$OS_NAME" in
  "Windows")
    cat <<'EOF'
🪟 WINDOWS – RECOMMENDED FOR VRSECRETARY

1. Install Epic Games Launcher
   - Go to the Unreal / Epic Games download page (opening next).
   - Download the "Epic Games Launcher" for Windows.
   - Run the installer and follow the steps.

2. Sign in / create an Epic account
   - Open Epic Games Launcher.
   - Log in or create a new account (free).

3. Install Unreal Engine 5
   - In Epic Games Launcher:
       - Click "Unreal Engine" on the left.
       - Go to the "Library" tab.
       - Click the "+" button to add a new engine version.
       - Select version 5.3 or newer.
       - Click "Install".
   - Wait for the download and installation to finish (it can be large).

4. Enable C++ & VR tools (recommended)
   - When installing Visual Studio 2022, choose:
       - "Game development with C++" workload.
   - In Unreal, you can use the VR template for VRSecretary demos.

Once Unreal 5.3+ is installed, you can open:
   samples/unreal-vr-secretary-demo/VRSecretaryDemo.uproject
EOF
    open_url "$UNREAL_URL"
    ;;

  "macOS")
    cat <<'EOF'
🍎 macOS

1. Install Epic Games Launcher
   - Go to the Unreal / Epic Games download page (opening next).
   - Download the macOS installer for "Epic Games Launcher".
   - Open the .dmg and drag the launcher into Applications.

2. Sign in / create an Epic account
   - Open Epic Games Launcher.
   - Log in or create a new account (free).

3. Install Unreal Engine 5
   - In Epic Games Launcher:
       - Click "Unreal Engine" on the left.
       - Go to the "Library" tab.
       - Click the "+" button to add a new engine version.
       - Select version 5.3 or newer.
       - Click "Install".

Note: For VR with Quest, you will usually still build & run on Windows.
macOS is fine for backend development and testing, but Windows is recommended
for full VRSecretary + Quest 3 workflows.
EOF
    open_url "$UNREAL_URL"
    ;;

  "Linux")
    cat <<'EOF'
🐧 LINUX

Epic does not (yet) provide a fully supported native Linux installer like on
Windows/macOS, but you have two main options:

OPTION A – Use Epic Games Launcher via Wine/Lutris (simpler, more GUI)
  1. Install Lutris and Wine (varies by distro).
  2. Search online for "Lutris Unreal Engine Epic Games Launcher" – follow guide.
  3. Install Unreal Engine 5.3+ via the Epic Launcher (same flow as Windows).

OPTION B – Build Unreal Engine from source (advanced)
  1. Create or sign in to a GitHub account.
  2. Link your GitHub account with your Epic account (in Epic settings).
  3. Clone the UE5 repository from Epic's GitHub (you will get an invite).
  4. Follow the official Linux build instructions in the UE docs.

For VRSecretary, the most straightforward setup is:
  - Windows 10/11 for Unreal + Quest.
  - Linux for backend-only work (FastAPI, Ollama, Chatterbox), if you prefer.

This helper cannot automate these steps on Linux because they require logins
and acceptance of Epic's license.
EOF
    open_url "$UNREAL_URL"
    ;;

  *)
    cat <<'EOF'
🤷 Unknown OS

I couldn't detect a supported OS automatically.

Please open the Unreal Engine download page manually and follow the
official instructions for your platform:

  https://www.unrealengine.com/download

For VRSecretary, Windows 10/11 with Unreal Engine 5.3+ is recommended
for the full VR + Quest 3 experience.
EOF
    open_url "$UNREAL_URL"
    ;;
esac

echo "Done. Follow the printed steps to finish installing Unreal Engine."
