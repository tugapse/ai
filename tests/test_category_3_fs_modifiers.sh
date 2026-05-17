#!/bin/bash

function test_output_file_flag() {
    local TEMP_OUT_FILE=$(mktemp)
    
    echo "   [EXEC] $AI_CMD -m \"Reply with the exact word BANANA\" -o \"$TEMP_OUT_FILE\""
    
    set +e
    $AI_CMD -m "Reply with the exact word BANANA" -o "$TEMP_OUT_FILE"
    local exit_code=$?
    set -e
    
    if grep -q "BANANA" "$TEMP_OUT_FILE" 2>/dev/null; then
        echo -e "      -> ${GREEN}Output file successfully created and verified${NC}"
    else
        echo -e "      -> ${RED}❌ FAILED: Output file not created or verification failed${NC}"
        echo -e "      -> Content of output file ($TEMP_OUT_FILE):"
        cat "$TEMP_OUT_FILE" 2>/dev/null || echo "(file not found)"
        return 1
    fi
    cleanup_files "$TEMP_OUT_FILE"
}

function run_category_3() {
    echo -e "\n${GREEN}### Category 3: File System Modifiers ###${NC}"
    run_test "Output File Flag (-o)" "Ensures the output flag writes the model's response to the specified file." test_output_file_flag
}