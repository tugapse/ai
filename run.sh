#!/bin/bash
FOLDER=$(dirname -- $(realpath -- "$0"))
source "$FOLDER/.venv/bin/activate"
export TQDM_DISABLE=1
python3 "$FOLDER/main.py" "$@"
deactivate 