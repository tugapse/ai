$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV_DIR = Join-Path $SCRIPT_DIR "..\.venv"

if (-not (Test-Path $VENV_DIR)) {
    Write-Host "Error: Virtual environment not found at '$VENV_DIR'."
    Write-Host "Please run the build script first to set up the environment."
    exit 1
}

Write-Host "Running tests..."
& "$VENV_DIR\Scripts\Activate.ps1"

Write-Host "Executing pytest..."
$env:PYTHONPATH = "$env:PYTHONPATH;./src"
pytest
Write-Host "Tests finished."