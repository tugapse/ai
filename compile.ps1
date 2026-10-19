$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
if (-not $ProjectRoot) {
    $ProjectRoot = (Get-Location).Path
}

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $VenvPython) {
    $Python = $VenvPython
} else {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCommand) {
        Write-Error "Python was not found. Install Python or create the project .venv first."
        exit 1
    }
    $Python = $PythonCommand.Source
}

Push-Location $ProjectRoot
try {
    & $Python -m PyInstaller --version *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing PyInstaller..."
        & $Python -m pip install pyinstaller
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Could not install PyInstaller."
            exit 1
        }
    }

    $EntryPoint = Join-Path $ProjectRoot "launcher.py"
    $RunScript = Join-Path $ProjectRoot "run.ps1"
    $SourcePath = Join-Path $ProjectRoot "src"
    $AssetsPath = Join-Path $ProjectRoot "assets"
    $ScriptsPath = Join-Path $ProjectRoot "scripts"
    $ProjectFile = Join-Path $ProjectRoot "pyproject.toml"
    $EngineStatusPath = Join-Path $ProjectRoot "installed_engines.json"

    $PyInstallerArgs = @(
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--console",
        "--python-option", "X utf8",
        "--name", "ai",
        "--specpath", (Join-Path $ProjectRoot "build"),
        "--add-data", "$RunScript;.",
        "--add-data", "$SourcePath;src",
        "--add-data", "$AssetsPath;assets",
        "--add-data", "$ScriptsPath;scripts",
        "--add-data", "$ProjectFile;.",
        "--add-data", "$EngineStatusPath;.",
        $EntryPoint
    )

    & $Python @PyInstallerArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "PyInstaller failed to build the executable."
        exit 1
    }

    Write-Host "Build complete: $(Join-Path $ProjectRoot 'dist\ai.exe')"
} finally {
    Pop-Location
}
