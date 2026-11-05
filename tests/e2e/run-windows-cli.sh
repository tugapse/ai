#!/bin/bash

SCRIPT_DIR=$(dirname -- "$(realpath -- "$0")")
WINDOWS_RUNNER=$(cygpath -w "$SCRIPT_DIR/run-windows-cli.ps1")
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$WINDOWS_RUNNER" "$@"
exit $?
