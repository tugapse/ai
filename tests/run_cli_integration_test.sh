#!/bin/bash
# CLI Integration Test Skeleton

set -e

# Set the AI_ASSISTANT_DIRECTORY environment variable for the test environment
export AI_ASSISTANT_DIRECTORY="/tmp/ai_assistant_test_dir"

# Create a temporary file for the model configuration
TEST_MODEL_CONFIG=$(mktemp --suffix=.json)
cat << 'EOF' > "$TEST_MODEL_CONFIG"
{
  "model_name": "Qwen/Qwen3-4B",
  "model_type": "causal_lm",
  "model_properties": {
    "max_new_tokens": 2048,
    "do_sample": true,
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 10,  
    "quantization_bits": 4,
    "device_type":"cuda"
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


run_category_1
run_category_2
run_category_3
run_category_4
run_category_5
print_summary

# ==============================================================================
# TODO: Pending Implementations
# ==============================================================================
# Test: --image
# Test: --pipeline
# Test: --create-tool
# Test: --generate-config
# Test: --overwrite-config

# TODO: Implement remaining tests: -D, -e, -q, -pl, -pdb, -nta
# Test: Interactive mode
# Test: --install

