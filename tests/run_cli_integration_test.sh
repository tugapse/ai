#!/bin/bash
# CLI Integration Test Skeleton
# Based on plan.md

set -e

VERBOSE=0
for arg in "$@"; do
    if [ "$arg" == "-V" ] || [ "$arg" == "--verbose" ]; then
        VERBOSE=1
    fi
done

export VERBOSE

# Set the AI_ASSISTANT_DIRECTORY environment variable for the test environment
export AI_ASSISTANT_DIRECTORY="/tmp/ai_assistant_test_dir"

# Create a temporary file for the model configuration
TEST_MODEL_CONFIG=$(mktemp --suffix=.json)
cat << 'EOF' > "$TEST_MODEL_CONFIG"
{
  "model_name": "gemma4",
  "model_type": "gguf",
  "model_properties": {
    "gguf_filename": "gemma-4-E2B-it-Q4_K_M.gguf",
    "model_repo_id": "unsloth/gemma-4-E2B-it-GGUF",
    "n_gpu_layers": -1,
    "n_ctx": 2048,
    "verbose": false,
    "max_new_tokens": 512,
    "temperature": 0.1,
    "top_p": 0.5,
    "top_k": 50,
    "presence_penalty": 1,
    "frequency_penalty": 1
  }
}
EOF

# Ensure cleanup on exit
trap "rm -f \"$TEST_MODEL_CONFIG\"" EXIT

export MODEL_TO_USE="$TEST_MODEL_CONFIG"
# Execution command
export AI_CMD="./run.sh -dc -md $MODEL_TO_USE"

SCRIPT_DIR=$(dirname -- "$(realpath -- "$0")")
source "$SCRIPT_DIR/e2e/test_utils.sh"
source "$SCRIPT_DIR/e2e/test_category_1_info.sh"
source "$SCRIPT_DIR/e2e/test_category_2_single_turn.sh"
source "$SCRIPT_DIR/e2e/test_category_3_fs_modifiers.sh"
source "$SCRIPT_DIR/e2e/test_category_4_config_state.sh"
source "$SCRIPT_DIR/e2e/test_category_5_blocking.sh"

# --- Execution ---
echo "========================================"
echo "Starting CLI Integration Tests"
echo "========================================"

run_category_1
run_category_2
run_category_3

# ==============================================================================
# TODO: Pending Implementations
# ==============================================================================
# Test: --image
# Test: --pipeline
# Test: --create-tool
# Test: --generate-config

run_category_4

# TODO: Implement remaining tests: -D, -e, -q, -pl, -pdb, -nta

run_category_5

# Test: Interactive mode
# Test: --install
# Test: --overwrite-config

print_summary
