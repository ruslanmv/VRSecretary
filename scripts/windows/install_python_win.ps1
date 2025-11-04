# install_python_win.ps1 - Install Python 3.11 on Windows (ASCII-only output)

# Ensure TLS 1.2 for downloads on older .NET
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

Write-Host ""
Write-Host "[INFO] Checking for Python 3.11..."

# Check if python3.11 is available
$pythonInstalled = Get-Command python3.11 -ErrorAction SilentlyContinue

if ($pythonInstalled) {
    Write-Host "[OK] Python 3.11 already installed:"
    python3.11 --version
    exit 0
}

Write-Host "[INFO] Python 3.11 not found. Starting installation..."

# Installer URL and temp path
$installerUrl  = "https://www.python.org/ftp/python/3.11.4/python-3.11.4-amd64.exe"
$installerPath = Join-Path $env:TEMP "python311-installer.exe"

# Download installer
Write-Host "[INFO] Downloading Python 3.11 from python.org ..."
try {
    Invoke-WebRequest -UseBasicParsing -Uri $installerUrl -OutFile $installerPath
} catch {
    Write-Host "[ERROR] Failed to download Python installer: $($_.Exception.Message)"
    exit 1
}

# Silent install: for all users, add to PATH, include pip and launcher
$arguments = '/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1 Include_launcher=1'
try {
    Write-Host "[INFO] Running installer (silent). This may take a minute..."
    $p = Start-Process -FilePath $installerPath -ArgumentList $arguments -PassThru -Wait
    if ($p.ExitCode -ne 0) {
        Write-Host "[ERROR] Installer returned exit code $($p.ExitCode)."
        exit 1
    }
} catch {
    Write-Host "[ERROR] Failed to run installer: $($_.Exception.Message)"
    exit 1
} finally {
    # Clean up installer
    try { Remove-Item $installerPath -ErrorAction SilentlyContinue } catch {}
}

# Verify installation
$pythonInstalled = Get-Command python3.11 -ErrorAction SilentlyContinue
if (-not $pythonInstalled) {
    Write-Host "[ERROR] Python 3.11 did not install correctly."
    exit 1
}

# Upgrade pip and common build tools
Write-Host "[INFO] Upgrading pip, setuptools, and wheel..."
try {
    python3.11 -m pip install --upgrade pip setuptools wheel
} catch {
    Write-Host "[WARN] Failed to upgrade pip tooling: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "[DONE] Python 3.11 installed successfully!"
python3.11 --version

