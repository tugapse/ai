$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
if (-not $ProjectRoot) {
    $ProjectRoot = (Get-Location).Path
}

$Python = $null
if ($env:AI_VENV_PATH) {
    $VenvPath = $env:AI_VENV_PATH
    if (-not [System.IO.Path]::IsPathRooted($VenvPath)) {
        $VenvPath = Join-Path $ProjectRoot $VenvPath
    }
    $VenvPython = Join-Path $VenvPath "Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
        Write-Error "AI_VENV_PATH does not contain a Windows Python environment: $VenvPath"
        exit 1
    }
    $Python = $VenvPython
} else {
    $VenvDirectories = @(
        (Join-Path $ProjectRoot ".venv"),
        (Join-Path (Split-Path $ProjectRoot -Parent) ".venv")
    )
    foreach ($VenvDirectory in $VenvDirectories) {
        $VenvPython = Join-Path $VenvDirectory "Scripts\python.exe"
        if (Test-Path -LiteralPath $VenvPython -PathType Leaf) {
            $Python = $VenvPython
            break
        }
    }

    if (-not $Python) {
        $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if (-not $PythonCommand) {
            Write-Error "Python was not found. Install Python, create a nearby .venv, or set AI_VENV_PATH."
            exit 1
        }
        $Python = $PythonCommand.Source
    }
}

# remove any existing dist and build directories
$DistPath = Join-Path $ProjectRoot "dist"
if (Test-Path -LiteralPath $DistPath -PathType Container) {
    Remove-Item -LiteralPath $DistPath -Recurse -Force
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
    $ScriptsPath = Join-Path $ProjectRoot "scripts"
    $AssetsPath = Join-Path $ProjectRoot "assets"
    $ProjectFile = Join-Path $ProjectRoot "pyproject.toml"

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
        $EntryPoint
    )

    & $Python @PyInstallerArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "PyInstaller failed to build the executable."
        exit 1
    }
    # create a .venv alongside the executable
    $DistVenvPath = Join-Path $DistPath ".venv"
    & $Python -m venv $DistVenvPath
    
    # run pip install -r requirements.txt in the .venv
    $DistVenvPython = Join-Path $DistVenvPath "Scripts\python.exe"
    $RequirementsFile = Join-Path $ProjectRoot "requirements.txt"   
    . $DistVenvPython -m pip install --upgrade pip
    . $DistVenvPython -m pip install -r $RequirementsFile

    $ExecutablePath = Join-Path $DistPath "ai.exe"
    . $ExecutablePath --help
    if ($LASTEXITCODE -ne 0) {
        Write-Error "The built executable failed to run."
        exit 1
    }
    Write-Host "Build complete: $ExecutablePath"
} finally {
    Pop-Location
}
