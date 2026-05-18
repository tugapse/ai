#!/bin/bash

function test_help_flag() {
    local TEMP_OUT=$(mktemp)
    echo "   [EXEC] $AI_CMD -h > \"$TEMP_OUT\""
    
    set +e
    $AI_CMD -h > "$TEMP_OUT" 2>&1
    local exit_code=$?
    set -e
    
    if grep -q "JUST A REASONING VIRTUAL INTELLIGENT SENTINEL AGENTIC INTERFACE" "$TEMP_OUT" && grep -q "\[ SYSTEM READY \]" "$TEMP_OUT"; then
        echo -e "      -> ${GREEN}Help output successfully verified${NC}"
    else
        echo -e "      -> ${RED}❌ FAILED: Help output verification failed${NC}"
        echo -e "      -> Content of output file ($TEMP_OUT):"
        cat "$TEMP_OUT" 2>/dev/null || echo "(file not found)"
        return 1
    fi
    cleanup_files "$TEMP_OUT"
}

function test_version_flag() {
    local TEMP_OUT=$(mktemp)
    echo "   [EXEC] $AI_CMD -v > \"$TEMP_OUT\""
    
    set +e
    $AI_CMD -v > "$TEMP_OUT" 2>&1
    local exit_code=$?
    set -e
    
    if grep -q "Version" "$TEMP_OUT"; then
        echo -e "      -> ${GREEN}Version output successfully verified${NC}"
    else
        echo -e "      -> ${RED}❌ FAILED: Version output verification failed${NC}"
        echo -e "      -> Content of output file ($TEMP_OUT):"
        cat "$TEMP_OUT" 2>/dev/null || echo "(file not found)"
        return 1
    fi
    cleanup_files "$TEMP_OUT"
}

function test_list_models() {
    local TEMP_OUT=$(mktemp)
    echo "   [EXEC] $AI_CMD -l > \"$TEMP_OUT\""
    
    set +e
    $AI_CMD -l > "$TEMP_OUT" 2>&1
    local exit_code=$?
    set -e
    
    if [ "$exit_code" -eq 0 ]; then
        echo -e "      -> ${GREEN}List models successfully executed${NC}"
    else
        echo -e "      -> ${RED}❌ FAILED: List models execution failed with exit code $exit_code${NC}"
        echo -e "      -> Content of output file ($TEMP_OUT):"
        cat "$TEMP_OUT" 2>/dev/null || echo "(file not found)"
        return 1
    fi
    cleanup_files "$TEMP_OUT"
}

function test_show_logo() {
    local TEMP_OUT=$(mktemp)
    echo "   [EXEC] $AI_CMD --show-logo -v > \"$TEMP_OUT\""
    
    set +e
    $AI_CMD --show-logo -v > "$TEMP_OUT" 2>&1
    local exit_code=$?
    set -e
    
    if grep -q "JARVIS" "$TEMP_OUT"; then
        echo -e "      -> ${GREEN}Show Logo successfully verified${NC}"
    else
        echo -e "      -> ${RED}❌ FAILED: Show Logo verification failed${NC}"
        echo -e "      -> Content of output file ($TEMP_OUT):"
        cat "$TEMP_OUT" 2>/dev/null || echo "(file not found)"
        return 1
    fi
    cleanup_files "$TEMP_OUT"
}

function run_category_1() {
    echo -e "\n${GREEN}### Category 1: Informational & Immediate Exit ###${NC}"
    run_test "Help Flag (-h)" "Verifies that the help flag outputs the correct system diagnostic message." test_help_flag
    run_test "Version Flag (-v)" "Checks if the version flag correctly displays the JARVIS version information." test_version_flag
    run_test "List Models (-l)" "Ensures the list flag executes without errors to show available neural models." test_list_models
    run_test "Show Logo (--show-logo)" "Tests if the show logo flag successfully prints the JARVIS ASCII art." test_show_logo
}