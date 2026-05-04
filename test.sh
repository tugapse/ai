#!/bin/bash
# Exit immediately if a command exits with a non-zero status.
set -e

# Define the path to the virtual environment directory
VENV_DIR=".venv"

# Check if the virtual environment directory exists
if [ ! -d "$VENV_DIR" ]; then
  echo "Error: Virtual environment not found at '$VENV_DIR'."
  echo "Please run the build script first to set up the environment."
  exit 1
fi

# Activate the virtual environment, install dependencies, and run pytest
echo "Running tests..."
source "$VENV_DIR/bin/activate"

echo "Executing pytest..."
PYTHONPATH=src pytest
echo "Tests finished."