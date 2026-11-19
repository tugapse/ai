#!/bin/bash
# CLI integration tests.
#
# They test the CLI's parameters and commands, not a model: the model is replaced by a stub
# Brain Server (tests/e2e/stub_server.py) that records what the CLI sends and always answers
# STUB_OK. No GPU and no model are needed, and a run takes a few minutes.
#
# Every run gets its own AI_ASSISTANT_DIRECTORY and free ports, so it never touches ~/Ai or a
# Brain Server running on this machine.
#
#   tests/run_cli_integration_test.sh [all|1|2|3|4|5]
#     1  informational flags and listings
#     2  what each parameter sends to the model
#     3  errors and exit codes
#     4  server and relay
#     5  agent mode (scripted agent turns)
#
# Known bugs are marked with known_issue: they count as skipped until fixed
# (STRICT_KNOWN_ISSUES=1 makes them fail).

set -e

SELECTED_CATEGORY="${1:-all}"

SCRIPT_DIR=$(dirname -- "$(realpath -- "$0")")
cd "$SCRIPT_DIR/.."   # the CLI is started as ./run.sh from the repository root

source "$SCRIPT_DIR/e2e/test_utils.sh"
source "$SCRIPT_DIR/e2e/stub_utils.sh"
source "$SCRIPT_DIR/e2e/test_category_1_info.sh"
source "$SCRIPT_DIR/e2e/test_category_2_params.sh"
source "$SCRIPT_DIR/e2e/test_category_3_errors.sh"
source "$SCRIPT_DIR/e2e/test_category_4_server.sh"
source "$SCRIPT_DIR/e2e/test_category_5_agent.sh"

run_selected_categories() {
    case "$SELECTED_CATEGORY" in
        all|ALL|"")
            run_category_1
            run_category_2
            run_category_3
            run_category_4
            run_category_5
            ;;
        1) run_category_1 ;;
        2) run_category_2 ;;
        3) run_category_3 ;;
        4) run_category_4 ;;
        5) run_category_5 ;;
        *)
            echo "Error: Unknown CLI integration category: $SELECTED_CATEGORY"
            echo "Valid values: 1, 2, 3, 4, 5, or all"
            exit 1
            ;;
    esac
}

if ! stub_start; then
    echo -e "${RED}The stub Brain Server could not start; no test ran.${NC}"
    exit 1
fi
trap stub_stop EXIT

run_selected_categories

print_summary

# ==============================================================================
# Not covered yet
# ==============================================================================
# - ai agent --knowledge, tools that ask for permission (write/execute)
# - Interactive chat mode
# - ai models generate, ai tools create, ai setup install/config
