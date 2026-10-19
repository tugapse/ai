$ErrorActionPreference = "Stop"

$PROJECT_ROOT = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$AI_ASSISTANT_DIRECTORY = $env:AI_ASSISTANT_DIRECTORY

if ($AI_ASSISTANT_DIRECTORY -and $AI_ASSISTANT_DIRECTORY.StartsWith("/")) {
    $CYGPATH = Get-Command cygpath.exe -ErrorAction SilentlyContinue
    if (-not $CYGPATH) {
        Write-Error "cygpath.exe is required to translate Git Bash paths."
        exit 1
    }

    $AI_ASSISTANT_DIRECTORY = & $CYGPATH.Source -w $AI_ASSISTANT_DIRECTORY
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    $env:AI_ASSISTANT_DIRECTORY = $AI_ASSISTANT_DIRECTORY
}

$RUN_SCRIPT = Join-Path $PROJECT_ROOT "run.ps1"
& $RUN_SCRIPT @args
exit $LASTEXITCODE
