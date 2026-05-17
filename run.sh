#!/bin/bash
FOLDER=$(dirname -- $(realpath -- "$0"))
source "$FOLDER/.venv/bin/activate"
export TQDM_DISABLE=1
export PYTHONPATH="$FOLDER/src"
python3 -X faulthandler "$FOLDER/src/ai/main.py" "$@"
deactivate 