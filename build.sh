#!/bin/bash
FOLDER=$(dirname -- $(realpath -- "$0"))
source "$FOLDER/.venv/bin/activate"
python dependency_installer.py
deactivate 