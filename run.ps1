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

# Set environment variable 
$env:TQDM_DISABLE = "1"
$env:PYTHONPATH = "$PSScriptRoot/src"


# Construct the path to the main Python script
$mainScript = Join-Path $PSScriptRoot "src/ai/main.py"

# Run the main Python script, passing along any arguments
# The '$args' variable in PowerShell contains all arguments passed to the script.
python -X faulthandler $mainScript $args

# Deactivate the virtual environment if the function exists
if (Get-Command -Name deactivate -ErrorAction SilentlyContinue) {
    deactivate
}