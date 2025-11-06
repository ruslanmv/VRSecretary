<#
.SYNOPSIS
    Start the full VRSecretary backend stack on Windows:
    - Activate .venv
    - Start Ollama (LLM)
    - Start Chatterbox TTS server
    - Start FastAPI gateway

.DESCRIPTION
    Run this script from the repo root:

        PS C:\workspace\VRSecretary> .\start.ps1

    It will:
    * Ensure .venv exists and activate it
    * Check if an Ollama server is already running
      - If NOT running, it will start `ollama serve`
    * Open a new PowerShell window for:
      - Chatterbox TTS (tools\vr_chatterbox_server.py)
      - FastAPI gateway (uvicorn vrsecretary_gateway.main:app)
#>

param(
    # If set, do not try to start Ollama (assume it's managed elsewhere)
    [switch]$SkipOllama
)

$ErrorActionPreference = "Stop"

# -----------------------------------------------------------------------------
# Locate repo root and venv
# -----------------------------------------------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$venvActivate = Join-Path $ScriptDir ".venv\Scripts\Activate.ps1"

if (-not (Test-Path $venvActivate)) {
    Write-Error "Virtual environment not found at '.venv'. Create it first (e.g. 'make install')."
}

Write-Host "Activating virtualenv: $venvActivate"
. $venvActivate
Write-Host "[OK] Virtualenv activated."

# -----------------------------------------------------------------------------
# Helper: Check / start Ollama
# -----------------------------------------------------------------------------
function Start-Ollama {
    param(
        [string]$OllamaHost = "127.0.0.1",
        [int]$OllamaPort = 11434
    )

    Write-Host ""
    Write-Host "=== Checking Ollama server ==="

    # 1) Check if process 'ollama' is already running
    $ollamaProc = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
    if ($ollamaProc) {
        Write-Host "Ollama process already running (PID(s): $($ollamaProc.Id -join ', '))."
    }
    else {
        Write-Host "No Ollama process found. Starting 'ollama serve' in a new PowerShell window..."
        try {
            $cmd = @"
ollama serve
"@
            Start-Process -FilePath "powershell.exe" `
                -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $cmd `
                -WindowStyle Normal

            Start-Sleep -Seconds 3
        }
        catch {
            Write-Warning "Failed to start 'ollama serve'. Make sure Ollama is installed and in PATH."
            return
        }
    }

    # 2) Check the HTTP endpoint
    try {
        $url = "http://${OllamaHost}:${OllamaPort}/api/tags"
        Write-Host "Checking Ollama HTTP endpoint at $url ..."
        $resp = Invoke-WebRequest -Uri $url -Method GET -TimeoutSec 5
        if ($resp.StatusCode -eq 200) {
            Write-Host "[OK] Ollama is reachable at $url"
        }
        else {
            Write-Warning "Ollama responded with HTTP $($resp.StatusCode)."
        }
    }
    catch {
        Write-Warning "Could not reach Ollama at http://${OllamaHost}:${OllamaPort}. Is it installed and running?"
    }
}

# -----------------------------------------------------------------------------
# Helper: Start Chatterbox TTS (new PowerShell window)
# -----------------------------------------------------------------------------
function Start-ChatterboxTts {
    Write-Host ""
    Write-Host "=== Starting Chatterbox TTS server (tools\vr_chatterbox_server.py) ==="

    $cmd = @"
cd "$ScriptDir"
& "$venvActivate"
python tools\vr_chatterbox_server.py
"@

    Start-Process -FilePath "powershell.exe" `
        -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $cmd `
        -WindowStyle Normal

    Write-Host "[OK] Launched Chatterbox TTS in a new PowerShell window."
}

# -----------------------------------------------------------------------------
# Helper: Start FastAPI Gateway (new PowerShell window)
# -----------------------------------------------------------------------------
function Start-Gateway {
    Write-Host ""
    Write-Host "=== Starting FastAPI gateway (vrsecretary_gateway.main:app) ==="

    $gatewayDir = Join-Path $ScriptDir "backend\gateway"

    $cmd = @"
cd "$gatewayDir"
& "$venvActivate"
uvicorn vrsecretary_gateway.main:app --host 0.0.0.0 --port 8000 --http h11
"@

    Start-Process -FilePath "powershell.exe" `
        -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $cmd `
        -WindowStyle Normal

    Write-Host "[OK] Launched FastAPI gateway in a new PowerShell window."
    Write-Host "    Docs at: http://localhost:8000/docs"
}

# -----------------------------------------------------------------------------
# Main flow
# -----------------------------------------------------------------------------
Write-Host "=== VRSecretary backend startup ==="

if (-not $SkipOllama) {
    Start-Ollama
}
else {
    Write-Host "Skipping Ollama startup (SkipOllama switch set)."
}

Start-ChatterboxTts
Start-Gateway

Write-Host ""
Write-Host "All backend processes launched."
Write-Host "You should see three PowerShell windows:"
Write-Host "  - Ollama (ollama serve)"
Write-Host "  - Chatterbox TTS"
Write-Host "  - FastAPI gateway (http://localhost:8000)"
Write-Host ""
Write-Host "Leave them open while using the VRSecretary Unreal project."
