# ==============================================================================
# Script: setup-dependencies.ps1
# Description: Self-Bootstrapping Python Virtual Environment Loader (PowerShell)
# Features: Silent Execution, Auto-Venv Creation, UI-Consistent Status
# Author: Fábio Almeida
# ==============================================================================

$ErrorActionPreference = "Stop"

# --- ANSI COLORS & SYMBOLS ---
$ESC    = [char]27
$BOLD   = "$ESC[1m"
$GREEN  = "$ESC[0;32m"
$CYAN   = "$ESC[0;36m"
$NC     = "$ESC[0m"

$CHECK  = [char]0x2714
$CROSS  = [char]0x2716
$CIRCLE = [char]0x25CB

# --- PATH CONFIGURATION ---
$FOLDER = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$VENV_PATH = Join-Path -Path $FOLDER -ChildPath ".venv"
$VENV_PYTHON = Join-Path -Path $VENV_PATH -ChildPath "Scripts\python.exe"

# --- 1. VIRTUAL ENVIRONMENT BOOTSTRAP ---
if (-not (Test-Path -LiteralPath $VENV_PATH)) {
    Write-Host "${CYAN}${CIRCLE}${NC} Initializing new virtual environment..."
    
    # '*> $null' is the PowerShell equivalent of '> /dev/null 2>&1'
    & python -m venv $VENV_PATH *> $null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "${BOLD}${CYAN}${CROSS}${NC} Failed to create virtual environment."
        exit 1
    }
}

Write-Host "${CYAN}${CIRCLE}${NC} Synchronizing dependencies..."

# --- 2. SILENT PIP UPGRADE ---
& $VENV_PYTHON -m pip install --upgrade pip *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "${BOLD}${CYAN}${CROSS}${NC} Pip upgrade failed."
    exit 1
}

# --- 3. EXECUTE DEPENDENCY INSTALLER ---
$INSTALLER_SCRIPT = Join-Path -Path $FOLDER -ChildPath "scripts/dependency_installer.py"
& $VENV_PYTHON $INSTALLER_SCRIPT

if ($LASTEXITCODE -ne 0) {
    Write-Host "${BOLD}${CYAN}${CROSS}${NC} Synchronization failed. Check logic manually."
    exit 1
}

Write-Host "${GREEN}${CHECK}${NC} System dependencies synchronized."