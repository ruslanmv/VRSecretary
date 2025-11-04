#!/usr/bin/env pwsh
<#
 demo/install_windows.ps1

 Friendly Windows installer for the VRSecretary demo.

 - If `make` is available, it will call:
     make install
     make patch-plugin

 - If `make` is NOT available, it performs a simplified manual setup:
     * Create .venv (using py -3.11 or python)
     * Install backend/gateway into the venv
     * Copy backend/docker/env.example to backend/gateway/.env (if missing)
     * Try to run the Unreal plugin patch script (if present)

 Run from PowerShell:

   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # (once, if needed)
   .\demo\install_windows.ps1
#>

param(
    [switch]$SkipMakeFallback  # if set, fail instead of manual install when make is missing
)

$ErrorActionPreference = "Stop"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " VRSecretary Demo - Windows Setup              " -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# --------------------------------------------------------------------------
# Locate repo root (parent of the demo folder)
# --------------------------------------------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root      = Split-Path -Parent $ScriptDir

Write-Host " Script location : $ScriptDir"
Write-Host " Repo root       : $Root"
Write-Host ""

Set-Location $Root

if (-not (Test-Path "Makefile")) {
    Write-Host "❌ Makefile not found in repo root: $Root" -ForegroundColor Red
    Write-Host "   Make sure you're running this inside the VRSecretary repository."
    exit 1
}

# --------------------------------------------------------------------------
# Try to use `make` (best experience)
# --------------------------------------------------------------------------
$makeCmd = $null
try {
    $makeCmd = Get-Command make -ErrorAction SilentlyContinue
} catch {
    $makeCmd = $null
}

if ($makeCmd -and -not $SkipMakeFallback) {
    Write-Host "✅ 'make' found at: $($makeCmd.Source)" -ForegroundColor Green
    Write-Host ""
    Write-Host "▶️  Step 1/2: Running 'make install' ..." -ForegroundColor Yellow
    & make install
    Write-Host ""
    Write-Host "✅ 'make install' completed." -ForegroundColor Green
    Write-Host ""

    Write-Host "▶️  Step 2/2: Running 'make patch-plugin' ..." -ForegroundColor Yellow
    try {
        & make patch-plugin
        Write-Host "✅ 'make patch-plugin' completed." -ForegroundColor Green
    }
    catch {
        Write-Host "ℹ️ Plugin patch step skipped or failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }

} elseif (-not $makeCmd -and $SkipMakeFallback) {
    Write-Host "❌ 'make' is not available and -SkipMakeFallback was specified." -ForegroundColor Red
    Write-Host "   Please install 'make' (e.g. via MSYS2, Chocolatey, etc.) or run without -SkipMakeFallback."
    exit 1

} else {
    # ----------------------------------------------------------------------
    # Manual fallback if `make` is missing
    # ----------------------------------------------------------------------
    Write-Host "⚠️ 'make' not found. Using manual fallback installation." -ForegroundColor Yellow
    Write-Host "   (You can install 'make' later and run 'make install' for advanced setup.)"
    Write-Host ""

    # 1) Detect Python
    $pythonCmd = $null

    try {
        $pyCmd = Get-Command py -ErrorAction SilentlyContinue
        if ($pyCmd) {
            $pythonCmd = "py -3.11"
        }
    } catch {
        $pythonCmd = $null
    }

    if (-not $pythonCmd) {
        try {
            $py3 = Get-Command python -ErrorAction SilentlyContinue
            if ($py3) {
                $pythonCmd = "python"
            }
        } catch {
            $pythonCmd = $null
        }
    }

    if (-not $pythonCmd) {
        Write-Host "❌ Could not find a Python interpreter on your PATH." -ForegroundColor Red
        Write-Host "   Please install Python 3.11+ and try again."
        exit 1
    }

    Write-Host "✅ Using Python command: $pythonCmd" -ForegroundColor Green
    Write-Host ""

    # 2) Create virtual environment at .venv
    if (-not (Test-Path ".venv")) {
        Write-Host "Creating virtual environment at .venv ..." -ForegroundColor Yellow
        & $pythonCmd -m venv ".venv"
    } else {
        Write-Host ".venv already exists; reusing it." -ForegroundColor Cyan
    }

    $venvPython = Join-Path ".venv" "Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        Write-Host "❌ Could not find $venvPython inside .venv." -ForegroundColor Red
        exit 1
    }

    # 3) Upgrade pip
    Write-Host "Upgrading pip inside .venv ..." -ForegroundColor Yellow
    & $venvPython -m pip install --upgrade pip

    # 4) Install backend/gateway
    $backendDir = Join-Path $Root "backend\gateway"
    if (-not (Test-Path $backendDir)) {
        Write-Host "❌ backend/gateway folder not found at $backendDir" -ForegroundColor Red
        exit 1
    }

    Write-Host "Installing VRSecretary backend from $backendDir ..." -ForegroundColor Yellow
    & $venvPython -m pip install -e $backendDir
    Write-Host "✅ Backend installed into .venv." -ForegroundColor Green
    Write-Host ""

    # 5) Create .env from example if needed
    $envPath      = Join-Path $backendDir ".env"
    $exampleEnv   = Join-Path $Root "backend\docker\env.example"

    if (-not (Test-Path $envPath) -and (Test-Path $exampleEnv)) {
        Write-Host "Creating backend/gateway/.env from backend/docker/env.example ..." -ForegroundColor Yellow
        Copy-Item $exampleEnv $envPath
        Write-Host "✅ .env created. You can edit it later for custom settings." -ForegroundColor Green
    } elseif (Test-Path $envPath) {
        Write-Host ".env already exists in backend/gateway; leaving it unchanged." -ForegroundColor Cyan
    } else {
        Write-Host "⚠️ Could not find backend/docker/env.example; skipping .env creation." -ForegroundColor Yellow
    }

    # 6) Try to run Unreal plugin patch (if available) via bash
    $patchScript = Join-Path $Root "tools\scripts\apply_vrsecretary_patch.sh"
    if (Test-Path $patchScript) {
        Write-Host "Attempting to run Unreal plugin patch script via bash ..." -ForegroundColor Yellow
        $bashCmd = $null
        try {
            $bashCmd = Get-Command bash -ErrorAction SilentlyContinue
        } catch {
            $bashCmd = $null
        }

        if ($bashCmd) {
            & bash "tools/scripts/apply_vrsecretary_patch.sh" "$Root"
            Write-Host "✅ Unreal plugin patch script executed." -ForegroundColor Green
        } else {
            Write-Host "ℹ️ 'bash' not found; skipping plugin patch step." -ForegroundColor Yellow
        }
    } else {
        Write-Host "ℹ️ No plugin patch script found at tools/scripts/apply_vrsecretary_patch.sh" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  VRSecretary Demo - Windows Setup Finished    " -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host @"
What was done for you:

  - A Python virtual environment (.venv) was created in the repo (or reused).
  - The VRSecretary backend (FastAPI gateway) was installed into that venv.
  - A default backend/gateway/.env file was created if needed.
  - If available, the Unreal VRSecretary plugin patch script was executed.

NEXT STEPS (every time you want to use Ailey):

  1) Start the AI model (Ollama)
     --------------------------------
     Open a terminal (PowerShell or CMD) and run:

       ollama serve

     Leave that window open.

  2) Start Chatterbox (voice)
     ------------------------
     Open a second terminal and run:

       chatterbox-server --port 4123

  3) Start the VRSecretary backend (FastAPI)
     ---------------------------------------
     From the repo root:

       # Activate the virtualenv:
       .\.venv\Scripts\Activate.ps1

       # Then start the gateway:
       cd backend\gateway
       uvicorn vrsecretary_gateway.main:app --host 0.0.0.0 --port 8000

  4) Open the Unreal demo project
     ----------------------------
       - In File Explorer:
           VRSecretary\samples\unreal-vr-secretary-demo\
       - Right-click VRSecretaryDemo.uproject:
           "Generate Visual Studio project files" (first time only)
       - Double-click VRSecretaryDemo.uproject to open in Unreal.
       - In Unreal:
           * Edit → Plugins → find "VRSecretary" and enable it if needed.
           * Edit → Project Settings → Plugins → VRSecretary:
               - Gateway URL:  http://localhost:8000
               - Backend Mode: Gateway (Ollama)
               - HTTP Timeout: 60.0 (default)

  5) Use "VR Preview" in Unreal with your Quest 3 to talk to Ailey.

You can rerun this script if you change machines or delete the .venv folder.
"@
