#!/bin/bash
# test_utils.sh

# Colors for output
export GREEN='\033[0;32m'
export RED='\033[0;31m'
export NC='\033[0m' # No Color
export YELLOW='\033[0;33m'

export TESTS_TOTAL=0
export TESTS_PASSED=0
export TESTS_FAILED=0

export VERBOSE="${VERBOSE:-0}"

function log_verbose() {
    if [ "${VERBOSE:-0}" -eq 1 ]; then
        echo -e "${YELLOW}   [DEBUG] $1${NC}"
    fi
}

function cleanup_files() {
    if [ "${VERBOSE:-0}" -eq 0 ]; then
        rm -f "$@"
    else
        log_verbose "Keeping temp file(s) for debugging: $@"
    fi
}

function run_test() {
    local test_name="$1"
    local description="$2"
    local func_name="$3"

    echo -e "\n${YELLOW}======================================================================${NC}"
    echo -e "${YELLOW}▶ TEST: ${test_name}${NC}"
    echo -e "  ${description}"
    echo -e "${YELLOW}----------------------------------------------------------------------${NC}"

    TESTS_TOTAL=$((TESTS_TOTAL + 1))

    set +e
    
    if [ "${VERBOSE:-0}" -eq 1 ]; then
        ( $func_name )
        local exit_code=$?
    else
        local temp_out=$(mktemp)
        ( $func_name ) > "$temp_out" 2>&1
        local exit_code=$? 
        
        if [ "$exit_code" -ne 0 ]; then
            cat "$temp_out"
        else
            grep -aE '(\[EXEC\]|->)' "$temp_out" || true
        fi
        rm -f "$temp_out"
    fi
    set -e

    if [ "$exit_code" -eq 0 ]; then
        echo -e "   -> ${GREEN}✅ TEST PASSED: ${test_name}${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "   -> ${RED}❌ TEST FAILED: ${test_name}${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

function run_and_verify() {
    local expected="$1"
    local out_file="$2"
    local cmd="$3"
    
    echo -e "   ${YELLOW}[EXEC]${NC} $cmd"
    set +e
    eval "$cmd"
    local exit_code=$?
    set -e
    
    if [ "$exit_code" -ne 0 ]; then
         echo -e "      -> ${RED}❌ FAILED: Command failed with exit code $exit_code${NC}"
         return 1
    fi
    
    if [ "$expected" != "NO_CHECK" ]; then
        if grep -iq "$expected" "$out_file"; then
            echo -e "      -> ${GREEN}Verified: '$expected' found in output.${NC}"
        else
            echo -e "      -> ${RED}❌ FAILED: '$expected' not found in $out_file${NC}"
            cat "$out_file" 2>/dev/null || echo "(file not found)"
            return 1
        fi
    else
        echo -e "      -> ${GREEN}Verified: Command completed successfully.${NC}"
    fi
}

function print_summary() {
    echo -e "\n======================================================================"
    echo -e "🏆 INTEGRATION TEST SUMMARY"
    echo -e "======================================================================"
    echo -e "Total Tests Run : $TESTS_TOTAL"
    echo -e "Tests Passed    : ${GREEN}$TESTS_PASSED${NC}"
    if [ "$TESTS_FAILED" -gt 0 ]; then
        echo -e "Tests Failed    : ${RED}$TESTS_FAILED${NC}"
        exit 1
    else
        echo -e "Tests Failed    : 0"
    fi
    echo -e "======================================================================\n"
}