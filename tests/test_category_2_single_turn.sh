#!/bin/bash

function test_simple_message() {
    local TEMP_OUT=$(mktemp)
    echo "   [EXEC] $AI_CMD -m \"Hello\" -o \"$TEMP_OUT\""
    
    set +e
    $AI_CMD -m "Hello" -o "$TEMP_OUT"
    local exit_code=$?
    set -e
    
    if [ "$exit_code" -eq 0 ]; then
        echo -e "      -> ${GREEN}Simple Message successfully executed${NC}"
    else
        echo -e "      -> ${RED}❌ FAILED: Simple Message execution failed${NC}"
        return 1
    fi
    cleanup_files "$TEMP_OUT"
}

function test_file_flag() {
    local TEMP_FILE=$(mktemp)
    local TEMP_OUT=$(mktemp)
    echo "SECRET_CODE_4285" > "$TEMP_FILE"
    
    echo "   [EXEC] $AI_CMD -f \"$TEMP_FILE\" -m \"What is the secret code in the file? Output only the code.\" -o \"$TEMP_OUT\""
    
    set +e
    $AI_CMD -f "$TEMP_FILE" -m "What is the secret code in the file? Output only the code." -o "$TEMP_OUT"
    local exit_code=$?
    set -e
    
    if grep -q "SECRET_CODE_4285" "$TEMP_OUT" 2>/dev/null; then
        echo -e "      -> ${GREEN}File Flag successfully verified${NC}"
    else
        echo -e "      -> ${RED}❌ FAILED: File Flag verification failed${NC}"
        echo -e "      -> Content of output file ($TEMP_OUT):"
        cat "$TEMP_OUT" 2>/dev/null || echo "(file not found)"
        return 1
    fi
    cleanup_files "$TEMP_FILE" "$TEMP_OUT"
}

function test_task_flag() {
    local TEMP_TASK_OUT=$(mktemp)
    mkdir -p "$AI_ASSISTANT_DIRECTORY/tasks"
    local TASK_FILE="$AI_ASSISTANT_DIRECTORY/tasks/secret_task.md"
    echo "Reply exactly with the secret code: SECRET_CODE_7777" > "$TASK_FILE"
    
    echo "   [EXEC] $AI_CMD -t \"secret_task\" -o \"$TEMP_TASK_OUT\""
    
    set +e
    $AI_CMD -t "secret_task" -o "$TEMP_TASK_OUT"
    local exit_code=$?
    set -e
    
    if grep -q "SECRET_CODE_7777" "$TEMP_TASK_OUT" 2>/dev/null; then
        echo -e "      -> ${GREEN}Task output file successfully created and verified${NC}"
    else
        echo -e "      -> ${RED}❌ FAILED: Task output file not created or verification failed${NC}"
        echo -e "      -> Content of output file ($TEMP_TASK_OUT):"
        cat "$TEMP_TASK_OUT" 2>/dev/null || echo "(file not found)"
        return 1
    fi
    cleanup_files "$TEMP_TASK_OUT" "$TASK_FILE"
}

function test_task_file_flag() {
    local TEMP_TASK_FILE=$(mktemp)
    local TEMP_TASK_OUT=$(mktemp)
    echo "Reply exactly with the secret code: SECRET_CODE_8888" > "$TEMP_TASK_FILE"
    
    echo "   [EXEC] $AI_CMD -tf \"$TEMP_TASK_FILE\" -o \"$TEMP_TASK_OUT\""
    
    set +e
    $AI_CMD -tf "$TEMP_TASK_FILE" -o "$TEMP_TASK_OUT"
    local exit_code=$?
    set -e
    
    if grep -q "SECRET_CODE_8888" "$TEMP_TASK_OUT" 2>/dev/null; then
        echo -e "      -> ${GREEN}Task output file successfully created and verified${NC}"
    else
        echo -e "      -> ${RED}❌ FAILED: Task output file not created or verification failed${NC}"
        echo -e "      -> Task input file was: $TEMP_TASK_FILE"
        echo -e "      -> Content of output file ($TEMP_TASK_OUT):"
        cat "$TEMP_TASK_OUT" 2>/dev/null || echo "(file not found)"
        return 1
    fi
    cleanup_files "$TEMP_TASK_FILE" "$TEMP_TASK_OUT"
}

function run_category_2() {
    echo -e "\n${GREEN}### Category 2: Single-Turn Execution ###${NC}"
    run_test "Simple Message (-m)" "Validates that a direct message query processes correctly and exits cleanly." test_simple_message
    run_test "Task Flag (-t)" "Checks if a predefined task template is located and executed properly." test_task_flag
    run_test "File Flag (-f)" "Tests the ability to read context from a file and answer a query about it." test_file_flag
    run_test "Task File Flag (-tf)" "Verifies that a custom task file is loaded and used to generate correct output." test_task_file_flag
}