# Makefile - VRSecretary full environment helper
# Cross-platform (Windows PowerShell / CMD / Git Bash / Linux / macOS).
#
# Capabilities:
#   - Create & sync a Python 3.11 virtualenv
#   - Install root "simple-environment" (Jupyter + Ollama Python client) via pyproject.toml
#   - Install VRSecretary backend (backend/gateway) into the same venv
#   - Register a Jupyter kernel
#   - Install/start Ollama on the host (best-effort)
#   - Run the FastAPI gateway (uvicorn)
#   - Build & run a Docker image with Ollama + Jupyter + this project
#   - Control backend docker-compose dev stack
#   - Apply Unreal plugin patch (if script exists)

# =============================================================================
#  Configuration & Cross-Platform Setup
# =============================================================================

.DEFAULT_GOAL := uv-install

# --- User-Configurable Variables ---
PYTHON ?= python3.11
VENV   ?= .venv

# VRSecretary backend (FastAPI) location
BACKEND_DIR    ?= backend/gateway
BACKEND_APP    ?= vrsecretary_gateway.main:app
BACKEND_HOST   ?= 0.0.0.0
BACKEND_PORT   ?= 8000

# --- OS Detection for Paths and Commands ---
ifeq ($(OS),Windows_NT)
# Use the Python launcher on Windows
PYTHON         := py -3.11
# Windows settings (PowerShell-safe)
PY_SUFFIX      := .exe
BIN_DIR        := Scripts
ACTIVATE       := $(VENV)\$(BIN_DIR)\activate
# Use $$null for PowerShell redirection
NULL_DEVICE    := $$null
RM             := Remove-Item -Force -ErrorAction SilentlyContinue
RMDIR          := Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
SHELL          := powershell.exe
.SHELLFLAGS    := -NoProfile -ExecutionPolicy Bypass -Command
# Reference to environment variables for PowerShell
ENVREF         := $$env:
# Docker volume source for PS (use the .Path of $PWD)
MOUNT_SRC      := "$$PWD.Path"
else
# Unix/Linux/macOS settings
PY_SUFFIX      :=
BIN_DIR        := bin
ACTIVATE       := . $(VENV)/$(BIN_DIR)/activate
NULL_DEVICE    := /dev/null
RM             := rm -f
RMDIR          := rm -rf
SHELL          := /bin/bash
.ONESHELL:
.SHELLFLAGS    := -eu -o pipefail -c
# Reference to environment variables for POSIX sh/bash
ENVREF         := $$
# Docker volume source for POSIX shells
MOUNT_SRC      := "$$(pwd)"
endif

# --- Derived Variables ---
PY_EXE  := $(VENV)/$(BIN_DIR)/python$(PY_SUFFIX)
PIP_EXE := $(VENV)/$(BIN_DIR)/pip$(PY_SUFFIX)

# Docker Config (optional Jupyter+Ollama dev container)
DOCKER_IMAGE ?= simple-env:latest
DOCKER_NAME  ?= simple-env
DOCKER_PORT  ?= 8888
DOCKER_PORT_OLLAMA ?= 11434

.PHONY: \
  help \
  venv \
  install \
  pip-install \
  dev \
  uv-install \
  update \
  test \
  lint \
  fmt \
  check \
  shell \
  clean \
  distclean \
  clean-venv \
  build-container \
  run-container \
  stop-container \
  remove-container \
  logs \
  check-python \
  check-pyproject \
  check-uv \
  python-version \
  install-ollama \
  check-ollama \
  notebook \
  pull-model \
  ollama-test \
  ensure-ollama-running \
  backend-install \
  backend-dev \
  run-gateway \
  gateway-test \
  docker-dev-up \
  docker-dev-down \
  docker-dev-logs \
  start-stack \
  patch-plugin

# =============================================================================
#  Helper Scripts (exported env vars; expanded by the shell)
# =============================================================================

export HELP_SCRIPT
define HELP_SCRIPT
import re, sys, io
print('Usage: make <target> [OPTIONS...]\n')
print('Available targets:\n')
mf = '$(firstword $(MAKEFILE_LIST))'
with io.open(mf, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        m = re.match(r'^([a-zA-Z0-9_.-]+):.*?## (.*)$$', line)
        if m:
            target, help_text = m.groups()
            print('  {0:<22} {1}'.format(target, help_text))
endef

export CLEAN_SCRIPT
define CLEAN_SCRIPT
import glob, os, shutil, sys
patterns = ['*.pyc', '*.pyo', '*~', '*.egg-info', '__pycache__', 'build', 'dist', '.mypy_cache', '.pytest_cache', '.ruff_cache']
to_remove = set()
for p in patterns:
    to_remove.update(glob.glob('**/' + p, recursive=True))
for path in sorted(to_remove, key=len, reverse=True):
    try:
        if os.path.isfile(path) or os.path.islink(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
    except OSError as e:
        print('Error removing {0}: {1}'.format(path, e), file=sys.stderr)
endef

# =============================================================================
#  Core Targets
# =============================================================================

help: ## Show this help message
ifeq ($(OS),Windows_NT)
	@& $(PYTHON) -X utf8 -c "$(ENVREF)HELP_SCRIPT"
else
	@$(PYTHON) -X utf8 -c "$(ENVREF)HELP_SCRIPT"
endif

# --- Local Python Environment (root pyproject: simple-environment) ---

# Create the venv only if it doesn't exist (do NOT wipe after uv sync)
ifeq ($(OS),Windows_NT)
$(VENV):
	@if (-not (Test-Path '$(VENV)')) { \
		Write-Host "Creating virtual environment at $(VENV)..."; \
		& $(PYTHON) -m venv '$(VENV)'; \
		& '$(VENV)\Scripts\python.exe' -m pip install -U pip; \
		& '$(VENV)\Scripts\python.exe' -V | %% { "✅ Created $(VENV) with $$_" }; \
	} else { Write-Host "ℹ️ Virtual environment exists: $(VENV)"; }
else
$(VENV):
	@echo "Ensuring virtual environment exists at $(VENV)..."
	@[ -d "$(VENV)" ] || { $(PYTHON) -m venv "$(VENV)"; "$(VENV)/bin/python" -m pip install -U pip; echo "✅ Created $(VENV)"; }
endif

venv: $(VENV) ## Ensure the virtual environment exists

# --- Unified install: root pyproject + backend + Jupyter + Ollama ---
install: venv uv-install backend-install notebook install-ollama ensure-ollama-running ## Install root deps, VRSecretary backend, Jupyter kernel, and host Ollama

dev: uv-install backend-dev ## Install project in dev mode using uv + VRSecretary backend (dev extras)

pip-install: venv check-pyproject ## [pip] Install root project (simple-environment) in non-editable mode
	@$(PIP_EXE) install .
	@echo "✅ Installed root project into $(VENV) using pip"

uv-install: check-pyproject venv check-uv ## [uv] Create/sync deps INTO .venv from root pyproject.toml
ifeq ($(OS),Windows_NT)
	@echo "Syncing environment with uv into $(VENV)..."
	@$$uvCmd = (Get-Command uv -ErrorAction SilentlyContinue); if (-not $$uvCmd) { $$uvCmd = Join-Path $$env:USERPROFILE '.local\bin\uv.exe' }; if (-not (Test-Path $$uvCmd)) { Write-Host 'Error: uv not found. Run `make check-uv` to install it.'; exit 1 }
	@$$env:UV_PROJECT_ENVIRONMENT = '$(VENV)'; & $$uvCmd sync
	@echo "✅ Done! To activate the environment, run:`n   .\\$(VENV)\\Scripts\\Activate.ps1"
else
	@echo "Syncing environment with uv into $(VENV)..."
	@UV_PROJECT_ENVIRONMENT=$(VENV) uv sync
	@echo -e "✅ Done! To activate the environment, run:\n   source $(VENV)/bin/activate"
endif

update: check-pyproject ## Upgrade/sync dependencies (prefers uv if available), plus dev extras for backend
ifeq ($(OS),Windows_NT)
	@$$uvCmd = (Get-Command uv -ErrorAction SilentlyContinue); if (-not $$uvCmd) { $$uvCmd = Join-Path $$env:USERPROFILE '.local\bin\uv.exe' }; if (Test-Path $$uvCmd) { \
		Write-Host 'Syncing root pyproject with uv...'; $$env:UV_PROJECT_ENVIRONMENT = '$(VENV)'; & $$uvCmd sync; \
	} else { \
		Write-Host 'uv not found, falling back to pip...'; if (-not (Test-Path '$(VENV)\Scripts\python.exe')) { & $(PYTHON) -m venv '$(VENV)'; & '$(VENV)\Scripts\python.exe' -m pip install -U pip }; \
		& '$(VENV)\Scripts\python.exe' -m pip install -U -e ".[dev]"; \
		Write-Host '✅ Root project and dev dependencies upgraded (pip fallback)'; \
	} ; \
	if (Test-Path '$(BACKEND_DIR)') { \
		Write-Host 'Updating backend/gateway (dev + watsonx extras)...'; \
		& '$(VENV)\Scripts\python.exe' -m pip install -U -e "$(BACKEND_DIR)[dev,watsonx]" ; \
	}
else
	@if command -v uv >$(NULL_DEVICE) 2>&1; then \
		echo "Syncing root pyproject with uv..."; UV_PROJECT_ENVIRONMENT=$(VENV) uv sync; \
	else \
		echo "uv not found, falling back to pip..."; \
		[ -x "$(VENV)/bin/python" ] || $(PYTHON) -m venv "$(VENV)"; \
		"$(VENV)/bin/python" -m pip install -U pip; \
		"$(VENV)/bin/pip" install -U -e ".[dev]"; \
		echo "✅ Root project and dev dependencies upgraded (pip fallback)"; \
	fi ; \
	if [ -d "$(BACKEND_DIR)" ]; then \
		echo "Updating backend/gateway (dev + watsonx extras)..."; \
		"$(VENV)/bin/pip" install -U -e "$(BACKEND_DIR)[dev,watsonx]"; \
	fi
endif

# --- Install VRSecretary backend into the venv ---

backend-install: venv ## Install VRSecretary backend (backend/gateway) into the venv
	@if [ -d "$(BACKEND_DIR)" ]; then \
		echo "📦 Installing VRSecretary backend from $(BACKEND_DIR)..."; \
		"$(PY_EXE)" -m pip install -e "$(BACKEND_DIR)"; \
		echo "✅ Installed VRSecretary backend."; \
	else \
		echo "⚠️ backend/gateway directory not found. Skipping backend-install."; \
	fi

backend-dev: venv ## Install VRSecretary backend with dev + watsonx extras
	@if [ -d "$(BACKEND_DIR)" ]; then \
		echo "📦 Installing VRSecretary backend (dev + watsonx extras)..."; \
		"$(PY_EXE)" -m pip install -e "$(BACKEND_DIR)[dev,watsonx]"; \
		echo "✅ Installed VRSecretary backend with dev extras."; \
	else \
		echo "⚠️ backend/gateway directory not found. Skipping backend-dev."; \
	fi

# --- Jupyter kernel registration (root env) ---
notebook: venv ## Ensure Jupyter + ipykernel are available and register 'vrsecretary-env' kernel
	@echo "📚 Ensuring Jupyter Notebook & kernel are installed..."
	@$(PY_EXE) -m pip install --upgrade notebook ipykernel >$(NULL_DEVICE)
	@$(PY_EXE) -m ipykernel install --user --name "vrsecretary-env" --display-name "Python 3.11 (VRSecretary)" >/dev/null 2>&1 || true
	@echo "✅ Jupyter kernel registered: Python 3.11 (VRSecretary)"

# --- Ollama installation on the HOST (best-effort) ---
check-ollama: ## Check whether 'ollama' is available
	@echo "🔎 Checking for Ollama on host..."
ifeq ($(OS),Windows_NT)
	@if (Get-Command ollama -ErrorAction SilentlyContinue) { echo '✅ Ollama is installed.' } else { echo 'ℹ️ Ollama not found.'; exit 1 }
else
	@command -v ollama >/dev/null 2>&1 && echo "✅ Ollama is installed." || (echo "ℹ️ Ollama not found." && exit 1)
endif

install-ollama: ## Install Ollama on the host (Win/macOS/Linux) if missing
ifeq ($(OS),Windows_NT)
	@if (Get-Command ollama -ErrorAction SilentlyContinue) { \
		echo '✅ Ollama already installed.' \
	} else { \
		echo '⬇️ Installing Ollama via winget (requires Windows 10/11)...'; \
		winget install -e --id Ollama.Ollama || echo '⚠️ winget install failed; try the GUI installer from https://ollama.com/download'; \
	}
else
	@if command -v ollama >/dev/null 2>&1; then \
		echo "✅ Ollama already installed."; \
	elif [ "$$(uname -s)" = "Darwin" ]; then \
		echo "⬇️ Installing Ollama via Homebrew..."; \
		(brew update && brew install --cask ollama) || echo "⚠️ brew install failed; download from https://ollama.com/download"; \
	else \
		echo "⬇️ Installing Ollama via official script..."; \
		curl -fsSL https://ollama.com/install.sh | sh || echo "⚠️ install.sh failed; see https://ollama.com/download"; \
	fi
endif

# Try to start the server and wait until it responds on 127.0.0.1:11434
ensure-ollama-running: ## Start Ollama server (best-effort) and verify API is reachable
ifeq ($(OS),Windows_NT)
	@if (Get-Command ollama -ErrorAction SilentlyContinue) { \
		Write-Host '▶️  Starting Ollama server (background)...'; \
		Start-Process -FilePath ollama -ArgumentList 'serve' -WindowStyle Hidden; \
		$ok=$false; for($i=0; $i -lt 60; $i++){ try { iwr http://127.0.0.1:11434/api/tags -UseBasicParsing | Out-Null; $ok=$true; break } catch { Start-Sleep -Milliseconds 500 } }; \
		if($ok){ echo '✅ Ollama server is up: http://127.0.0.1:11434'; } else { echo '⚠️ Could not reach Ollama on 11434. Start it manually or check firewall.'; } \
	} else { echo '⚠️ Ollama not installed'; exit 1 }
else
	@command -v ollama >/dev/null 2>&1 || { echo "⚠️ Ollama not installed"; exit 1; }
	@echo "▶️  Starting Ollama server (background, best-effort)..."
	@pkill -f "ollama serve" >/dev/null 2>&1 || true
	@nohup ollama serve >/tmp/ollama.log 2>&1 &
	@ok=0; for i in $$(seq 1 60); do curl -fsS http://127.0.0.1:11434/api/tags >/dev/null && ok=1 && break || sleep 0.5; done; \
	if [ "$$ok" = "1" ]; then echo "✅ Ollama server is up: http://127.0.0.1:11434"; else echo "⚠️ Could not reach Ollama on 11434. Start it manually or check firewall."; fi
endif

# --- Quick pull + test against local Ollama ---
pull-model: ## Pull a tiny model for quick tests (host Ollama)
	@echo "📥 Pulling qwen2.5:0.5b-instruct..."
	@ollama pull qwen2.5:0.5b-instruct || echo "⚠️ Could not pull model. Is Ollama running?"

ollama-test: venv ## Run a tiny Python chat against local Ollama (root env)
	@echo "💬 Running a quick chat against http://localhost:11434 ..."
	@$(PY_EXE) - <<'PY'
	import sys
	try:
		import ollama
	except Exception as e:
		print('Missing python client: pip install ollama'); sys.exit(1)
	try:
		r = ollama.chat(model='qwen2.5:0.5b-instruct',
						messages=[{'role':'user','content':"Say only 'Ciao!' in Italian."}])
		print(r['message']['content'])
	except Exception as e:
		print('⚠️ Chat failed:', e)
	PY

# --- Run VRSecretary backend locally ---
run-gateway: venv backend-install ## Run FastAPI VRSecretary gateway with uvicorn
	@echo "🚀 Starting VRSecretary gateway on http://$(BACKEND_HOST):$(BACKEND_PORT)..."
	@$(PY_EXE) -m uvicorn $(BACKEND_APP) --host $(BACKEND_HOST) --port $(BACKEND_PORT)

gateway-test: ## Test gateway /health endpoint
ifeq ($(OS),Windows_NT)
	@echo "🔎 Testing gateway health at http://localhost:$(BACKEND_PORT)/health ..."
	@try { \
		$resp = iwr ("http://localhost:$(BACKEND_PORT)/health") -UseBasicParsing; \
		Write-Host $resp.Content; \
	} catch { \
		Write-Host "⚠️ Gateway health check failed."; \
		exit 1; \
	}
else
	@echo "🔎 Testing gateway health at http://localhost:$(BACKEND_PORT)/health ..."
	@curl -fsS "http://localhost:$(BACKEND_PORT)/health" || { echo "⚠️ Gateway health check failed."; exit 1; }
endif

start-stack: install run-gateway ## Setup everything (env + Ollama + backend) and run gateway (foreground)

# --- Docker (Jupyter + Ollama + simple-environment) ---

build-container: check-pyproject ## Build the Jupyter+Ollama dev image with this repo
	@echo "🐳 Building image '$(DOCKER_IMAGE)' using Dockerfile..."
	@docker build -t $(DOCKER_IMAGE) .

ifeq ($(OS),Windows_NT)
run-container: ## Run or restart the dev container (Jupyter:8888, Ollama:11434)
	@docker run -d --name $(DOCKER_NAME) -p $(DOCKER_PORT):8888 -p $(DOCKER_PORT_OLLAMA):11434 -v $(MOUNT_SRC):/workspace $(DOCKER_IMAGE) > $(NULL_DEVICE) 2> $(NULL_DEVICE); if ($$LASTEXITCODE -ne 0) { docker start $(DOCKER_NAME) > $(NULL_DEVICE) 2> $(NULL_DEVICE) }
	@echo "Container is up:"
	@echo "  Jupyter:  http://localhost:$(DOCKER_PORT)"
	@echo "  Ollama:   http://localhost:$(DOCKER_PORT_OLLAMA)"

stop-container: ## Stop the dev container
	@docker stop $(DOCKER_NAME) > $(NULL_DEVICE) 2> $(NULL_DEVICE); if ($$LASTEXITCODE -ne 0) { echo "Info: container was not running." }

remove-container: stop-container ## Stop and remove the dev container
	@docker rm $(DOCKER_NAME) > $(NULL_DEVICE) 2> $(NULL_DEVICE); if ($$LASTEXITCODE -ne 0) { echo "Info: container did not exist." }
else
run-container: ## Run or restart the dev container (Jupyter:8888, Ollama:11434)
	@docker run -d --name $(DOCKER_NAME) -p $(DOCKER_PORT):8888 -p $(DOCKER_PORT_OLLAMA):11434 -v $(MOUNT_SRC):/workspace $(DOCKER_IMAGE) > $(NULL_DEVICE) || docker start $(DOCKER_NAME)
	@echo "Container is up:"
	@echo "  Jupyter:  http://localhost:$(DOCKER_PORT)"
	@echo "  Ollama:   http://localhost:$(DOCKER_PORT_OLLAMA)"

stop-container: ## Stop the dev container
	@docker stop $(DOCKER_NAME) >$(NULL_DEVICE) 2>&1 || echo "Info: container was not running."

remove-container: stop-container ## Stop and remove the dev container
	@docker rm $(DOCKER_NAME) >$(NULL_DEVICE) 2>&1 || echo "Info: container did not exist."
endif

logs: ## View the dev container logs (Ctrl-C to exit)
	@docker logs -f $(DOCKER_NAME)

# --- Backend docker-compose dev stack (gateway + Ollama) ---

docker-dev-up: ## Start backend dev stack (docker-compose.dev.yml)
	@echo "🐳 Starting backend dev stack (gateway + Ollama)..."
	@docker compose -f backend/docker/docker-compose.dev.yml up -d

docker-dev-down: ## Stop backend dev stack
	@echo "🐳 Stopping backend dev stack..."
	@docker compose -f backend/docker/docker-compose.dev.yml down

docker-dev-logs: ## Tail logs from backend dev stack
	@docker compose -f backend/docker/docker-compose.dev.yml logs -f

# --- Unreal plugin patch helper (optional) ---

patch-plugin: ## Apply VRSecretary Unreal plugin patch (if tools/scripts/apply_vrsecretary_patch.sh exists)
	@if [ -x "tools/scripts/apply_vrsecretary_patch.sh" ]; then \
		echo "🔧 Applying VRSecretary plugin patch..."; \
		bash tools/scripts/apply_vrsecretary_patch.sh "$(PWD)"; \
	else \
		echo "⚠️ tools/scripts/apply_vrsecretary_patch.sh not found or not executable. Skipping."; \
	fi

# --- Development & QA (Python) ---

test: venv ## Run Python tests with pytest (root env; backend tests if installed)
	@echo "🧪 Running tests..."
	@$(PY_EXE) -m pytest

lint: venv ## Check code style with ruff
	@echo "🔍 Linting with ruff..."
	@$(PY_EXE) -m ruff check . || true

fmt: venv ## Format code with ruff
	@echo "🎨 Formatting with ruff..."
	@$(PY_EXE) -m ruff format . || true

check: lint test ## Run all checks (linting and testing)

# --- Utility ---

python-version: check-python ## Show resolved Python interpreter and version
ifeq ($(OS),Windows_NT)
	@echo "Using: $(PYTHON)"
	@& $(PYTHON) -V
else
	@echo "Using: $(PYTHON)"
	@$(PYTHON) -V
endif

shell: venv ## Show how to activate the virtual environment shell
	@echo "Virtual environment is ready."
	@echo "To activate it, run:"
	@echo "  On Windows (CMD/PowerShell): .\\$(VENV)\\Scripts\\Activate.ps1"
	@echo "  On Unix (Linux/macOS/Git Bash): source $(VENV)/bin/activate"

clean-venv: ## Force-remove the venv (kills python.exe on Windows)
ifeq ($(OS),Windows_NT)
	@& $$env:ComSpec /c "taskkill /F /IM python.exe >NUL 2>&1 || exit 0"
	@Start-Sleep -Milliseconds 300
	@if (Test-Path '$(VENV)'){ Remove-Item -Recurse -Force '$(VENV)' }
else
	@rm -rf "$(VENV)"
endif

clean: ## Remove Python artifacts, caches, and the virtualenv
	@echo "Cleaning project..."
	-$(RMDIR) $(VENV)
	-$(RMDIR) .pytest_cache
	-$(RMDIR) .ruff_cache
ifeq ($(OS),Windows_NT)
	@& $(PYTHON) -c "$(ENVREF)CLEAN_SCRIPT"
else
	@$(PYTHON) -c "$(ENVREF)CLEAN_SCRIPT"
endif
	@echo "Clean complete."

distclean: clean ## Alias for clean

# =============================================================================
#  Internal Helper Targets
# =============================================================================

ifeq ($(OS),Windows_NT)
check-python:
	@echo "Checking for a Python 3.11 interpreter..."
	@& $(PYTHON) -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,11) else 1)" 2>$(NULL_DEVICE); if ($$LASTEXITCODE -ne 0) { echo "Error: '$(PYTHON)' is not Python 3.11."; echo "Please install Python 3.11 and add it to your PATH,"; echo "or specify via: make install PYTHON='py -3.11'"; exit 1; }
	@echo "Found Python 3.11:"
	@& $(PYTHON) -V

check-pyproject:
	@if (Test-Path -LiteralPath 'pyproject.toml') { echo 'Found pyproject.toml at repo root' } else { echo ('Error: pyproject.toml not found in ' + (Get-Location)); exit 1 }

check-uv: ## Check for uv and install it if missing
	@echo "Checking for uv..."
	@$$cmd = Get-Command uv -ErrorAction SilentlyContinue; if (-not $$cmd) { echo 'Info: ''uv'' not found. Attempting to install it now...'; iwr https://astral.sh/uv/install.ps1 -UseBasicParsing | iex; $$localBin = Join-Path $$env:USERPROFILE '.local\bin'; if (Test-Path $$localBin) { $$env:Path = "$$localBin;$$env:Path" } }
	@$$cmd = Get-Command uv -ErrorAction SilentlyContinue; if (-not $$cmd) { $$candidate = Join-Path $$env:USERPROFILE '.local\bin\uv.exe'; if (Test-Path $$candidate) { echo ('Using ' + $$candidate); $$env:Path = (Split-Path $$candidate) + ';' + $$env:Path } else { echo 'Error: ''uv'' is still not available after installation.'; exit 1 } }
	@echo "✅ uv is available."
else
check-python:
	@echo "Checking for a Python 3.11 interpreter..."
	@$(PYTHON) -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,11) else 1)" 2>$(NULL_DEVICE) || ( \
		echo "Error: '$(PYTHON)' is not Python 3.11."; \
		echo "Please install Python 3.11 and add it to your PATH,"; \
		echo 'or specify the command via make install PYTHON=\"py -3.11\"'; \
		exit 1; \
	)
	@echo "Found Python 3.11:"
	@$(PYTHON) -V

check-pyproject:
	@[ -f pyproject.toml ] || { echo "Error: pyproject.toml not found in $$(pwd)"; exit 1; }
	@echo "Found pyproject.toml at repo root"

check-uv: ## Check for uv and install it if missing
	@echo "Checking for uv..."
	@command -v uv >$(NULL_DEVICE) 2>&1 || ( \
		echo "Info: 'uv' not found. Attempting to install it now..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	)
	@command -v uv >$(NULL_DEVICE) 2>&1 || ( \
		echo "Error: 'uv' is still not available after installation."; \
		exit 1; \
	)
	@echo "✅ uv is available."
endif
