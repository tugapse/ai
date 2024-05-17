#!/bin/bash
FOLDER=$(dirname -- $(realpath -- "$0"))/../..
export PYTHONPATH=$FOLDER
python3 $(realpath -- "$FOLDER/ai/init.py") "$@"