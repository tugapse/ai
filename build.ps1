# Get the script's directory. This is a reliable way to get the script's location.
$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition

# Construct the path to the activation script
$activationScript = Join-Path $PSScriptRoot ".venv\Scripts\Activate.ps1"

# Check if the activation script exists
if (Test-Path $activationScript) {
    # Activate the virtual environment
    & $activationScript
} else {
    Write-Error "Virtual environment activation script not found at '$activationScript'. Please ensure the .venv is set up correctly."
    exit 1
}
$instalerScript = Join-Path $PSScriptRoot "scripts\dependency_installer.py"

# Run the dependency installer
python dependency_installer.py

# Deactivate the virtual environment if the function exists
if (Get-Command -Name deactivate -ErrorAction SilentlyContinue) {
    deactivate
}