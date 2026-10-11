$ErrorActionPreference = "Stop"

$FOLDER = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }

# Ensure absolute module imports (e.g., 'import src.ai') resolve correctly
$env:PYTHONPATH = $FOLDER
$env:PYTHONUNBUFFERED = "1"

$VENV_PATH = Join-Path -Path $FOLDER -ChildPath ".venv"
$VENV_PYTHON = Join-Path -Path $VENV_PATH -ChildPath "Scripts\python.exe"
$MAIN_SCRIPT = Join-Path -Path $FOLDER -ChildPath "src\ai\main.py"

# Enforce virtual environment usage to prevent missing dependency errors
if (-not (Test-Path -LiteralPath $VENV_PYTHON)) {
    Write-Host "[!] Virtual environment not found. Please run .\build.ps1 first." -ForegroundColor Red
    exit 1
}

# Set VIRTUAL_ENV variable just in case any underlying Python scripts check for it
$env:VIRTUAL_ENV = $VENV_PATH

# Execute main.py using the isolated Python environment
& $VENV_PYTHON $MAIN_SCRIPT @args

exit $LASTEXITCODE