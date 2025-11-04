# install_cuda_win.ps1 - Install CUDA-enabled PyTorch stack (Windows, ASCII-only output)
#
# Usage (from project root, with your venv activated):
#   .\scripts\windows\install_cuda_win.ps1
#
# This will:
#   - Check if torch already has CUDA support; if yes, do nothing.
#   - Upgrade pip/setuptools/wheel from the *normal* PyPI index.
#   - Uninstall any existing torch/torchvision/torchaudio.
#   - Install pinned CUDA wheels for cu121:
#       torch==2.5.1+cu121
#       torchvision==0.20.1+cu121
#       torchaudio==2.5.1+cu121

$ErrorActionPreference = "Stop"

# ----------------- Pinned versions that EXIST on cu121 -----------------

# These are the latest torch 2.5.x CUDA 12.1 wheels as of now.
# If PyTorch changes their CUDA support, you might have to update them.
$TORCH_VERSION       = "2.5.1+cu121"
$TORCHVISION_VERSION = "0.20.1+cu121"
$TORCHAUDIO_VERSION  = "2.5.1+cu121"

# CUDA wheels index for PyTorch cu121
$CUDA_INDEX_URL = "https://download.pytorch.org/whl/cu121"

# Ensure TLS 1.2 for downloads on older .NET
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

Write-Host ""
Write-Host "[INFO] Checking for Python on PATH..."

# Check that Python is available (use the one from your venv if active)
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python is not available on PATH."
    Write-Host "[HINT] Activate your virtual environment or install Python first."
    exit 1
}

Write-Host "[OK] Python found at: $($pythonCmd.Source)"
try {
    & python --version
} catch {
    Write-Host "[WARN] Could not read Python version: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "[INFO] Checking if PyTorch with CUDA is already available..."

$hasCudaTorch = $false
try {
    # Try to import torch and print CUDA version if present
    $torchOutput = & python -c "import torch, sys; v = getattr(torch, 'version', None); cuda = getattr(v, 'cuda', None); print(cuda or '')" 2>$null
    if ($LASTEXITCODE -eq 0 -and $torchOutput.Trim() -ne "") {
        $hasCudaTorch = $true
        Write-Host "[OK] Existing torch installation has CUDA support (CUDA version: $($torchOutput.Trim()))."
    } else {
        Write-Host "[INFO] Torch is missing or has no CUDA support; proceeding with CUDA install."
    }
} catch {
    Write-Host "[INFO] Torch not installed or import failed; proceeding with CUDA install."
}

if ($hasCudaTorch) {
    Write-Host ""
    Write-Host "[INFO] Skipping CUDA install because CUDA-enabled torch is already present."
    Write-Host "[DONE] Nothing to do."
    exit 0
}

# ----------------- Find project root (folder containing pyproject.toml) -----------------

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = $scriptDir

while ($true) {
    $pyproject = Join-Path $projectRoot "pyproject.toml"
    if (Test-Path $pyproject) {
        break
    }

    $parent = Split-Path -Parent $projectRoot
    if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $projectRoot) {
        Write-Host "[WARN] pyproject.toml not found above $scriptDir."
        Write-Host "[WARN] Using script directory as project root: $scriptDir"
        $projectRoot = $scriptDir
        break
    }

    $projectRoot = $parent
}

Write-Host ""
Write-Host "[INFO] Preparing to install CUDA-enabled PyTorch stack..."
Write-Host "[INFO] Project root (for reference): $projectRoot"
Write-Host "[INFO] CUDA wheels index: $CUDA_INDEX_URL"

Set-Location $projectRoot

# ----------------- Upgrade build tooling from *normal* PyPI -----------------

Write-Host ""
Write-Host "[INFO] Upgrading pip, setuptools, and wheel from the default PyPI index..."
try {
    & python -m pip install --upgrade pip setuptools wheel
} catch {
    Write-Host "[WARN] Failed to upgrade pip tooling: $($_.Exception.Message)"
}

# ----------------- Remove any existing torch stack -----------------

Write-Host ""
Write-Host "[INFO] Uninstalling any existing torch / torchvision / torchaudio..."
try {
    & python -m pip uninstall -y torch torchvision torchaudio 2>$null | Out-Null
} catch {
    Write-Host "[WARN] Uninstall may have partially failed (some packages missing), continuing..."
}

# ----------------- Install pinned CUDA wheels directly -----------------

Write-Host ""
Write-Host "[INFO] Installing pinned CUDA wheels from index:"
Write-Host "       torch==$TORCH_VERSION"
Write-Host "       torchvision==$TORCHVISION_VERSION"
Write-Host "       torchaudio==$TORCHAUDIO_VERSION"
Write-Host ""
Write-Host "[INFO] Running:"
Write-Host "       python -m pip install `"
Write-Host "           torch==$TORCH_VERSION `"
Write-Host "           torchvision==$TORCHVISION_VERSION `"
Write-Host "           torchaudio==$TORCHAUDIO_VERSION `"
Write-Host "           --index-url $CUDA_INDEX_URL"
Write-Host ""

& python -m pip install `
    "torch==$TORCH_VERSION" `
    "torchvision==$TORCHVISION_VERSION" `
    "torchaudio==$TORCHAUDIO_VERSION" `
    --index-url $CUDA_INDEX_URL

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] pip install of pinned CUDA wheels failed with exit code $LASTEXITCODE."
    Write-Host "[HINT] This may mean the index $CUDA_INDEX_URL does not have these versions anymore."
    Write-Host "[HINT] Check PyTorch 'Get Started' page and adjust:"
    Write-Host "       - $CUDA_INDEX_URL"
    Write-Host "       - the pinned versions at the top of this script."
    exit 1
}

Write-Host ""
Write-Host "[DONE] CUDA-enabled torch/torchvision/torchaudio installed from $CUDA_INDEX_URL."

# ----------------- Final verification -----------------

Write-Host ""
Write-Host "[INFO] Verifying torch and CUDA availability..."
try {
    $torchCheck = & python -c "import torch; print('torch', torch.__version__); print('cuda_available', torch.cuda.is_available());"
    Write-Host $torchCheck
} catch {
    Write-Host "[WARN] Torch verification failed: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "[DONE] CUDA installation script completed."
