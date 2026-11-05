SCRIPT_PATH=$(readlink -f "$0")

find "$SCRIPT_PATH" -type d -name "__pycache__" -exec rm -rf {} +