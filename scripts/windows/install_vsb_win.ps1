# install_vsb_win.ps1 - Install Microsoft Visual C++ Build Tools (VS 2022)
# Requires Administrator privileges to run successfully.

# Ensure TLS 1.2 for downloads on older .NET / PowerShell
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

Write-Host ""
Write-Host "[INFO] Checking for Visual C++ Build Tools (VS 2022)..."

# -----------------------------------------------------------------------------
# 1. Fast path: detect existing Build Tools / C++ compiler and skip install
# -----------------------------------------------------------------------------

$hasVCTools = $false

# Try vswhere (installed with Visual Studio / Build Tools)
$vswherePath = Join-Path "${env:ProgramFiles(x86)}" "Microsoft Visual Studio\Installer\vswhere.exe"

if (Test-Path $vswherePath) {
    try {
        $vsInstallPath = & $vswherePath `
            -products * `
            -requires Microsoft.VisualStudio.Workload.VCTools `
            -requiresAny `
            -version "[17.0,18.0)" `
            -property installationPath `
            -latest 2>$null

        if ($vsInstallPath) {
            Write-Host "[OK] Visual C++ Build Tools already installed at: $vsInstallPath"
            $hasVCTools = $true
        }
    } catch {
        Write-Host "[WARN] vswhere.exe check failed: $($_.Exception.Message)"
    }
}

# Fallback: look for cl.exe on PATH (any reasonably recent MSVC is fine)
if (-not $hasVCTools) {
    $clCmd = Get-Command cl.exe -ErrorAction SilentlyContinue
    if ($clCmd) {
        Write-Host "[OK] Found C/C++ compiler 'cl.exe' at: $($clCmd.Path)"
        Write-Host "[INFO] Assuming suitable C++ build tools are already installed. Skipping VS Build Tools installation."
        $hasVCTools = $true
    }
}

if ($hasVCTools) {
    # Nothing to do, exit quickly
    exit 0
}

Write-Host "[INFO] Visual C++ Build Tools not found. Proceeding with installation..."

# -----------------------------------------------------------------------------
# 2. Download VS Build Tools bootstrapper (if not already cached)
# -----------------------------------------------------------------------------

# URI for the Visual Studio Build Tools 2022 bootstrapper
$vsBootstrapperUrl = "https://aka.ms/vs/17/release/vs_BuildTools.exe"

# Local path for the downloaded installer
$tempDir = Join-Path $env:TEMP "VSBuildTools"
$exePath = Join-Path $tempDir "vs_BuildTools.exe"

# Create the temporary directory if it does not exist
if (-not (Test-Path $tempDir)) {
    Write-Host "[INFO] Creating temporary directory: $tempDir"
    try {
        New-Item -Path $tempDir -ItemType Directory | Out-Null
    } catch {
        Write-Host "[ERROR] Failed to create temporary directory: $($_.Exception.Message)"
        exit 1
    }
}

# Download only if we do not already have the bootstrapper
if (-not (Test-Path $exePath)) {
    Write-Host "[INFO] Downloading Visual Studio Build Tools installer..."
    try {
        Invoke-WebRequest -Uri $vsBootstrapperUrl -OutFile $exePath -UseBasicParsing
    } catch {
        Write-Host "[ERROR] Failed to download VS Build Tools: $($_.Exception.Message)"
        Write-Host "[HINT] Check your internet connection and try again."
        exit 1
    }
} else {
    Write-Host "[INFO] Reusing cached VS Build Tools installer: $exePath"
}

if (-not (Test-Path $exePath)) {
    Write-Host "[ERROR] Downloaded installer not found at: $exePath"
    exit 1
}

# -----------------------------------------------------------------------------
# 3. Run the installer silently
# -----------------------------------------------------------------------------

# Installer arguments:
#   --quiet              : Runs installation silently (no GUI)
#   --norestart          : Prevents automatic system restart
#   --add VCTools        : Installs the core C++ build tools workload
#   --includeRecommended : Installs recommended components (incl. Windows SDK)
$arguments = @(
    "--quiet",
    "--norestart",
    "--add", "Microsoft.VisualStudio.Workload.VCTools",
    "--includeRecommended"
)

Write-Host "[INFO] Starting silent installation of Microsoft Visual C++ Build Tools..."
Write-Host "[INFO] This may take several minutes and will not show a progress bar."

try {
    $process = Start-Process -FilePath $exePath -ArgumentList $arguments -Wait -PassThru
    $exitCode = $process.ExitCode
} catch {
    Write-Host "[ERROR] Failed to start VS Build Tools installer: $($_.Exception.Message)"
    exit 1
}

if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "[SUCCESS] Microsoft Visual C++ Build Tools installed successfully."
    Write-Host "[NOTE] It is recommended to restart your system before building packages that need a compiler."
    # Optional cleanup:
    # try { Remove-Item $exePath -Force -ErrorAction SilentlyContinue } catch {}
    exit 0
} else {
    Write-Host ""
    Write-Host "[ERROR] VS Build Tools installer returned exit code: $exitCode"
    Write-Host "[HINT] You may need to run the installer manually to see detailed error messages."
    exit $exitCode
}
