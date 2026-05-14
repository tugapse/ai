#!/bin/bash

# ==============================================================================
# Script: setup-dependencies.sh
# Description: Self-Bootstrapping Python Virtual Environment Loader
# Features: Silent Execution, Auto-Venv Creation, UI-Consistent Status
# ==============================================================================

set -e

# --- ANSI COLORS ---
BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' 

# --- PATH CONFIGURATION ---
FOLDER=$(dirname -- "$(realpath -- "$0")")
VENV_PATH="$FOLDER/.venv"

# --- MAIN EXECUTION ---

# 1. Virtual Environment Bootstrap
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${CYAN}○${NC} Initializing new virtual environment..."
    python3 -m venv "$VENV_PATH" > /dev/null 2>&1
fi

# 2. Activation & Quiet Execution
source "$VENV_PATH/bin/activate"

echo -e "${CYAN}○${NC} Synchronizing dependencies..."

# Suppressing logs for the installer and the python execution
# We redirect both stdout and stderr to /dev/null
if python3 -m pip install --upgrade pip > /dev/null 2>&1 && \
   python3 "$FOLDER/dependency_installer.py" > /dev/null 2>&1; then
    echo -e "${GREEN}✔${NC} System dependencies synchronized."
else
    echo -e "${BOLD}${CYAN}✖${NC} Synchronization failed. Check logic manually."
    deactivate
    exit 1
fi

deactivate