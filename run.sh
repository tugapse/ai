#!/bin/bash
set -e

FOLDER=$(dirname -- $(realpath -- "$0"))
AI_DIR="${AI_ASSISTANT_DIRECTORY:-$HOME/Ai}"
CURRENT_DIR="$(pwd)"

USE_DOCKER=false
FORWARD_ARGS=()

# Parse CLI arguments to detect the Docker flag
while [[ $# -gt 0 ]]; do
  case "$1" in
    --docker)
      USE_DOCKER=true
      shift
      ;;
    *)
      FORWARD_ARGS+=("$1")
      shift
      ;;
  esac
done

if [ "$USE_DOCKER" = true ]; then
  exec docker run --rm -it \
    --network jarvis-network \
    --user "$(id -u):$(id -g)" \
    -v "$AI_DIR":"$AI_DIR" \
    -v "$CURRENT_DIR":/workspace \
    -w /workspace \
    -e CURRENT_DIR=/workspace \
    -e AI_ASSISTANT_DIRECTORY="$AI_DIR" \
    -e TQDM_DISABLE=1 \
    -e PYTHONUNBUFFERED=1 \
    jarvis-ai:latest "${FORWARD_ARGS[@]}"
fi

# Default host execution
source "$FOLDER/.venv/bin/activate"
export TQDM_DISABLE=1
export PYTHONPATH="$FOLDER/src"
export AI_ASSISTANT_DIRECTORY="$AI_DIR"
export CURRENT_DIR="$CURRENT_DIR"

python3 -X faulthandler "$FOLDER/src/ai/main.py" "${FORWARD_ARGS[@]}"
deactivate