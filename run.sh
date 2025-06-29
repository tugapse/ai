#!/bin/bash
FOLDER=$(dirname -- $(realpath -- "$0"))
source "$FOLDER/.venv/bin/activate"
python3 "$FOLDER/main.py" "$@"
deactivate 