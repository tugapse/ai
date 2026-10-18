#!/bin/bash
# Exit immediately if a command exits with a non-zero status.
set -e

# Define the path to the virtual environment directory
# resolve from current file dir

SCRIPT_DIR=$(dirname -- "$(realpath -- "$0")")
VENV_DIR="$SCRIPT_DIR/../.venv"

# Activate virtual environment if present, otherwise rely on system/container environment
if [ -d "$VENV_DIR" ]; then
  echo "Activating virtual environment at $VENV_DIR..."
  source "$VENV_DIR/bin/activate"
elif command -v pytest >/dev/null 2>&1; then
  echo "Virtual environment not present; using environment pytest..."
else
  echo "Error: Virtual environment not found at '$VENV_DIR' and pytest is not installed."
  echo "Please run the build script first to set up the environment."
  exit 1
fi

echo "Running tests..."

echo "Executing pytest..."
export PYTHONPATH=$PYTHONPATH:./src
pytest
echo "Tests finished."