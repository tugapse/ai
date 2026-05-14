# ==============================================================================
# Script: setup-dependencies.ps1
# Description: Self-Bootstrapping Python Virtual Environment Loader (PowerShell)
# Features: Silent Execution, Auto-Venv Creation, UI-Consistent Status
# Author: Fábio Almeida
# ==============================================================================

$ErrorActionPreference = "Stop"

$BOLD = "$([char]27)[1m"
$GREEN = "$([char]27)[0;32m"
$CYAN = "$([char]27)[0;36m"
$NC = "$([char]27)[0m"

$FOLDER = $PSScriptRoot
$VENV_PATH = Join-Path $FOLDER ".venv"


if (-not (Test-Path -Path $VENV_PATH)) {
    Write-Host "$CYAN○$NC Initializing new virtual environment..." -NoNewline
    # Suppress output from venv creation
    Start-Process "python" -ArgumentList "-m venv", "`"$VENV_PATH`"" -NoNewWindow -Wait > $null 2>&1
    Write-Host " ${GREEN}Done!${NC}"
}


& "$VENV_PATH\Scripts\Activate.ps1"

Write-Host "$CYAN○$NC Synchronizing dependencies..."

try {
    python "$FOLDER\dependency_installer.py" 
    Write-Host "$GREEN✔$NC System dependencies synchronized."
}
catch {
    Write-Host "${BOLD}${CYAN}✖${NC} Synchronization failed. Check logic manually."
    Deactivate
    exit 1
}

Deactivate