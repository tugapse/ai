#!/bin/bash

function test_server_flag() {
    local TEMP_OUT=$(mktemp)
    local REMOTE_TEMP_OUT=$(mktemp)
    local REMOTE_TASK_OUT=$(mktemp)
    local TEMP_TASK_FILE=$(mktemp)
    local REMOTE_SYS_OUT=$(mktemp)
    local TEMP_SYS_FILE=$(mktemp)
    local REMOTE_FILE_OUT=$(mktemp)
    local TEMP_FILE=$(mktemp)
    local TEMP_MODEL_JSON=$(mktemp --suffix=.json)
    
    cat <<EOF > "$TEMP_MODEL_JSON"
{
    "model_name": "$TEST_MODEL_CONFIG",
    "model_type": "jarvis",
    "model_properties": {
    "base_url": "http://0.0.0.0:9999",
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

    echo "   [EXEC] $AI_CMD --server > \"$TEMP_OUT\" 2>&1 &"
    
    set +e
    $AI_CMD --server > "$TEMP_OUT" 2>&1 &
    local SERVER_PID=$!
    
    # Wait 5 seconds for the server to initialize
    echo "   [EXEC] Waiting 20 seconds for server to initialize..."
    sleep 20
    
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo -e "      -> ${RED}❌ FAILED: Server failed to start or crashed prematurely${NC}"
        cat "$TEMP_OUT" 2>/dev/null
        cleanup_files "$TEMP_OUT" "$REMOTE_TEMP_OUT" "$REMOTE_TASK_OUT" "$TEMP_TASK_FILE" "$REMOTE_SYS_OUT" "$TEMP_SYS_FILE" "$REMOTE_FILE_OUT" "$TEMP_FILE" "$TEMP_MODEL_JSON"
        return 1
    fi
    
    # Test Remote Connection
    echo "   [EXEC] Testing remote connection: $AI_CMD -md \"$TEMP_MODEL_JSON\" -m \"Reply exactly with REMOTE_SUCCESS\" -o \"$REMOTE_TEMP_OUT\""
    $AI_CMD -md "$TEMP_MODEL_JSON" -m "Reply exactly with REMOTE_SUCCESS" -o "$REMOTE_TEMP_OUT"
    
    if grep -q "REMOTE_SUCCESS" "$REMOTE_TEMP_OUT" 2>/dev/null; then
         echo -e "      -> ${GREEN}Remote connection responded successfully${NC}"
        TEST_CASES=$((TEST_CASES + 1))
    else
         echo -e "      -> ${RED}❌ FAILED: Remote connection failed to respond correctly${NC}"
         echo -e "      -> Content of remote output file ($REMOTE_TEMP_OUT):"
         cat "$REMOTE_TEMP_OUT" 2>/dev/null || echo "(file not found)"
         kill -TERM $SERVER_PID
         wait $SERVER_PID 2>/dev/null || true
         cleanup_files "$TEMP_OUT" "$REMOTE_TEMP_OUT" "$REMOTE_TASK_OUT" "$TEMP_TASK_FILE" "$REMOTE_SYS_OUT" "$TEMP_SYS_FILE" "$REMOTE_FILE_OUT" "$TEMP_FILE" "$TEMP_MODEL_JSON"
         return 1
    fi
    
    # Test Remote Connection with Task File
    echo "Reply exactly with REMOTE_TASK_SUCCESS" > "$TEMP_TASK_FILE"
    echo "   [EXEC] Testing remote connection with task file: $AI_CMD -md \"$TEMP_MODEL_JSON\" -tf \"$TEMP_TASK_FILE\" -o \"$REMOTE_TASK_OUT\""
    $AI_CMD -md "$TEMP_MODEL_JSON" -tf "$TEMP_TASK_FILE" -o "$REMOTE_TASK_OUT"
    
    if grep -q "REMOTE_TASK_SUCCESS" "$REMOTE_TASK_OUT" 2>/dev/null; then
         echo -e "      -> ${GREEN}Remote connection with task file responded successfully${NC}"
        TEST_CASES=$((TEST_CASES + 1))
    else
         echo -e "      -> ${RED}❌ FAILED: Remote connection with task file failed to respond correctly${NC}"
         echo -e "      -> Content of remote output file ($REMOTE_TASK_OUT):"
         cat "$REMOTE_TASK_OUT" 2>/dev/null || echo "(file not found)"
         kill -TERM $SERVER_PID
         wait $SERVER_PID 2>/dev/null || true
         cleanup_files "$TEMP_OUT" "$REMOTE_TEMP_OUT" "$REMOTE_TASK_OUT" "$TEMP_TASK_FILE" "$REMOTE_SYS_OUT" "$TEMP_SYS_FILE" "$REMOTE_FILE_OUT" "$TEMP_FILE" "$TEMP_MODEL_JSON"
         return 1
    fi
    
    # Test Remote Connection with System File
    echo "You are a robot. Always reply exactly with REMOTE_SYS_SUCCESS." > "$TEMP_SYS_FILE"
    echo "   [EXEC] Testing remote connection with system file: $AI_CMD -md \"$TEMP_MODEL_JSON\" -sf \"$TEMP_SYS_FILE\" -m \"Who are you?\" -o \"$REMOTE_SYS_OUT\""
    $AI_CMD -md "$TEMP_MODEL_JSON" -sf "$TEMP_SYS_FILE" -m "Who are you?" -o "$REMOTE_SYS_OUT"
    
    if grep -q "REMOTE_SYS_SUCCESS" "$REMOTE_SYS_OUT" 2>/dev/null; then
         echo -e "      -> ${GREEN}Remote connection with system file responded successfully${NC}"
        TEST_CASES=$((TEST_CASES + 1))
    else
         echo -e "      -> ${RED}❌ FAILED: Remote connection with system file failed to respond correctly${NC}"
         echo -e "      -> Content of remote output file ($REMOTE_SYS_OUT):"
         cat "$REMOTE_SYS_OUT" 2>/dev/null || echo "(file not found)"
         kill -TERM $SERVER_PID
         wait $SERVER_PID 2>/dev/null || true
         cleanup_files "$TEMP_OUT" "$REMOTE_TEMP_OUT" "$REMOTE_TASK_OUT" "$TEMP_TASK_FILE" "$REMOTE_SYS_OUT" "$TEMP_SYS_FILE" "$REMOTE_FILE_OUT" "$TEMP_FILE" "$TEMP_MODEL_JSON"
         return 1
    fi

    # Test Remote Connection with Context File
    echo "SECRET_CODE_9999" > "$TEMP_FILE"
    echo "   [EXEC] Testing remote connection with file: $AI_CMD -md \"$TEMP_MODEL_JSON\" -f \"$TEMP_FILE\" -m \"What is the secret code in the file? Output only the code.\" -o \"$REMOTE_FILE_OUT\""
    $AI_CMD -md "$TEMP_MODEL_JSON" -f "$TEMP_FILE" -m "What is the secret code in the file? Output only the code." -o "$REMOTE_FILE_OUT"
    
    if grep -q "SECRET_CODE_9999" "$REMOTE_FILE_OUT" 2>/dev/null; then
         echo -e "      -> ${GREEN}Remote connection with file responded successfully${NC}"
        TEST_CASES=$((TEST_CASES + 1))
    else
         echo -e "      -> ${RED}❌ FAILED: Remote connection with file failed to respond correctly${NC}"
         echo -e "      -> Content of remote output file ($REMOTE_FILE_OUT):"
         cat "$REMOTE_FILE_OUT" 2>/dev/null || echo "(file not found)"
         kill -TERM $SERVER_PID
         wait $SERVER_PID 2>/dev/null || true
         cleanup_files "$TEMP_OUT" "$REMOTE_TEMP_OUT" "$REMOTE_TASK_OUT" "$TEMP_TASK_FILE" "$REMOTE_SYS_OUT" "$TEMP_SYS_FILE" "$REMOTE_FILE_OUT" "$TEMP_FILE" "$TEMP_MODEL_JSON"
         return 1
    fi

    # Send SIGTERM to the process and its children (the actual python process)
    echo "   [EXEC] Sending SIGTERM to process $SERVER_PID and its children"
    pkill -TERM -P $SERVER_PID 2>/dev/null || true
    kill -TERM $SERVER_PID 2>/dev/null || true
    
    # Wait up to 5 seconds for the process to exit and logs to flush
    for i in {1..5}; do
        if grep -iq "graceful shutdown" "$TEMP_OUT"; then
            break
        fi
        sleep 1
    done
    wait $SERVER_PID 2>/dev/null || true
    set -e
    
    if grep -iq "graceful shutdown" "$TEMP_OUT"; then
        echo -e "      -> ${GREEN}Server Flag successfully verified (Started and Stopped cleanly)${NC}"
        cleanup_files "$TEMP_OUT" "$REMOTE_TEMP_OUT" "$REMOTE_TASK_OUT" "$TEMP_TASK_FILE" "$REMOTE_SYS_OUT" "$TEMP_SYS_FILE" "$REMOTE_FILE_OUT" "$TEMP_FILE" "$TEMP_MODEL_JSON"
        TEST_CASES=$((TEST_CASES + 1))
         return 0
    else
        echo -e "      -> ${RED}❌ FAILED: Server did not log graceful shutdown${NC}"
        echo -e "      -> Content of output file ($TEMP_OUT):"
        cat "$TEMP_OUT" 2>/dev/null || echo "(file not found)"
        cleanup_files "$TEMP_OUT" "$REMOTE_TEMP_OUT" "$REMOTE_TASK_OUT" "$TEMP_TASK_FILE" "$REMOTE_SYS_OUT" "$TEMP_SYS_FILE" "$REMOTE_FILE_OUT" "$TEMP_FILE" "$TEMP_MODEL_JSON"
        return 1
    fi
}

function run_category_5() {
    echo -e "\n${GREEN}### Category 5: Blocking / Long-Running Processes ###${NC}"
    run_test "Server Flag (--server)" "Verifies the AI server starts in the background and shuts down gracefully upon SIGTERM." test_server_flag
}