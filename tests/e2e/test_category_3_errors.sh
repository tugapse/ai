#!/bin/bash
# Category 3: errors and exit codes. A failing command must exit non-zero and send nothing.

function test_unknown_flag() {
    stub_reset
    local term="$STUB_ROOT/term.txt" code=0
    stub_cli "$term" --no-such-flag -m "hi" || code=$?
    expect_code 2 "$code" "$term" "an unknown flag is refused" || return 1
    expect_text "$term" "unrecognized arguments: --no-such-flag" "the error names the flag" || return 1
    expect_no_request "nothing is sent to the model" || return 1
}

function test_missing_inputs() {
    local term="$STUB_ROOT/term.txt" code
    local cases=("-f|$STUB_ROOT/nope.txt|File not found" "-tf|$STUB_ROOT/nope.md|File not found" "-D|$STUB_ROOT/nope_dir|Folder not found")
    for case in "${cases[@]}"; do
        IFS='|' read -r flag path message <<< "$case"
        stub_reset; code=0
        stub_cli "$term" "$flag" "$path" -m "hi" || code=$?
        expect_code nonzero "$code" "$term" "$flag with a missing path fails" || return 1
        expect_text "$term" "$message" "$flag says '$message'" || return 1
        expect_no_request "$flag: nothing is sent to the model" || return 1
    done
    stub_reset; code=0
    stub_cli "$term" -t "no_such_task" || code=$?
    expect_code nonzero "$code" "$term" "-t with an unknown task fails" || return 1
    expect_text "$term" "Task template 'no_such_task' not found" "-t names the missing task" || return 1
    expect_no_request "-t: nothing is sent to the model" || return 1
}

function test_missing_task_is_not_a_traceback() {
    local term="$STUB_ROOT/term.txt" code=0
    stub_cli "$term" -t "no_such_task" || code=$?
    expect_text "$term" "Traceback" "an unknown task is reported without a Python traceback" absent || return 1
}

function test_missing_system_prompt_fails() {
    local term="$STUB_ROOT/term.txt" code
    stub_reset; code=0
    stub_cli "$term" -sf "$STUB_ROOT/nope.md" -m "hi" || code=$?
    expect_code nonzero "$code" "$term" "-sf with a missing file fails" || return 1
    expect_text "$term" "System prompt file not found" "-sf names the missing file" || return 1
    expect_no_request "-sf: nothing is sent to the model" || return 1
    stub_reset; code=0
    stub_cli "$term" -s "no_such_prompt" -m "hi" || code=$?
    expect_code nonzero "$code" "$term" "-s with an unknown name fails" || return 1
    expect_text "$term" "System prompt 'no_such_prompt' not found" "-s names the missing prompt" || return 1
    expect_no_request "-s: nothing is sent to the model" || return 1
}

function test_missing_model_config() {
    local term="$STUB_ROOT/term.txt" code=0
    echo -e "   ${YELLOW}[EXEC]${NC} ai -md $STUB_ROOT/no-such-model.json -m hi"
    set +e
    AI_ASSISTANT_DIRECTORY="$STUB_HOME" ./run.sh -dc -md "$STUB_ROOT/no-such-model.json" -m "hi" > "$term" 2>&1
    code=$?
    set -e
    expect_code nonzero "$code" "$term" "-md with a missing config fails" || return 1
    expect_text "$term" "not found" "the error says the config was not found" || return 1
}

function test_brain_unreachable() {
    local term="$STUB_ROOT/term.txt" model="$STUB_ROOT/dead-model.json" port code=0
    port=$(free_port)
    sed "s/127.0.0.1:$STUB_PORT/127.0.0.1:$port/; s/\"timeout\": 15/\"timeout\": 3/" "$STUB_MODEL" > "$model"
    echo -e "   ${YELLOW}[EXEC]${NC} ai -md (nothing listening on $port) -m hi"
    set +e
    AI_ASSISTANT_DIRECTORY="$STUB_HOME" timeout 120 ./run.sh -dc -md "$model" -m "hi" -o "$STUB_ROOT/dead-out.txt" > "$term" 2>&1
    code=$?
    set -e
    expect_code nonzero "$code" "$term" "an unreachable Brain Server fails the command" || return 1
}

function run_category_3() {
    echo -e "\n${GREEN}### Category 3: Errors and exit codes ###${NC}"
    run_test "Unknown Flag" "An unknown flag exits 2, names the flag and sends nothing." test_unknown_flag
    run_test "Missing Inputs" "-f, -tf, -D and -t with a missing path or name fail and send nothing." test_missing_inputs
    run_test "Missing Model Config (-md)" "A model config that does not exist fails with a clear error." test_missing_model_config
    run_test "Unreachable Brain Server" "A chat whose server is down exits non-zero." test_brain_unreachable
    run_test "Missing System Prompt (-s, -sf)" "A missing -sf file or -s name fails and sends nothing." test_missing_system_prompt_fails
    run_test "Unknown Task Message (-t)" "An unknown task is reported without a Python traceback." test_missing_task_is_not_a_traceback
}
