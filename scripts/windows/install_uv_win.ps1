# install_uv_win.ps1 - Install uv on Windows (ASCII-only output)

# Ensure TLS 1.2 for downloads on older .NET
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

Write-Host ""
Write-Host "[INFO] Checking for 'uv'..."

# Check if 'uv' is already available
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue

if ($uvCmd) {
    Write-Host "[OK] 'uv' already installed:"
    try {
        uv --version
    } catch {
        Write-Host "[WARN] Could not run 'uv --version': $($_.Exception.Message)"
    }
    exit 0
}

Write-Host "[INFO] 'uv' not found. Starting installation..."

# Installer script URL and temp path
$installScriptUrl  = "https://astral.sh/uv/install.ps1"
$installScriptPath = Join-Path $env:TEMP "uv-install.ps1"

# Download installer script
Write-Host "[INFO] Downloading uv installer script..."
try {
    Invoke-WebRequest -UseBasicParsing -Uri $installScriptUrl -OutFile $installScriptPath
} catch {
    Write-Host "[ERROR] Failed to download uv installer script: $($_.Exception.Message)"
    exit 1
}

# Run installer script
try {
    if (-not (Test-Path $installScriptPath)) {
        Write-Host "[ERROR] uv installer script not found after download."
        exit 1
    }

    Write-Host "[INFO] Running uv installer script..."
    powershell.exe -ExecutionPolicy Bypass -File $installScriptPath
} catch {
    Write-Host "[ERROR] Running uv installer script failed: $($_.Exception.Message)"
    exit 1
} finally {
    # Clean up installer script
    try { Remove-Item $installScriptPath -ErrorAction SilentlyContinue } catch {}
}

# Verify installation
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvCmd) {
    Write-Host "[ERROR] 'uv' did not install correctly."
    Write-Host "[HINT] Install manually from https://astral.sh/uv/ and ensure it is on PATH."
    exit 1
}

Write-Host ""
Write-Host "[DONE] 'uv' installed successfully!"
try {
    uv --version
} catch {
    Write-Host "[WARN] 'uv' installed but 'uv --version' failed: $($_.Exception.Message)"
}

exit 0
