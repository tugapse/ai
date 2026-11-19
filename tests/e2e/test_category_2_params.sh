#!/bin/bash
# Category 2: what each parameter sends to the model (checked on the stub's recorded request).

function test_stub_message_and_output() {
    stub_reset
    local term="$STUB_ROOT/term.txt" out="$STUB_ROOT/out.txt" code=0
    stub_cli "$term" -m "PING_MESSAGE_1" -o "$out" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect "exactly one request reached the model" "len(reqs) == 1" || return 1
    expect "-m is the last user message" "users[-1] == 'PING_MESSAGE_1'" || return 1
    expect_file_is "$out" "$STUB_REPLY" || return 1
    if grep -q "$STUB_REPLY" "$term"; then
        echo -e "      -> ${GREEN}Verified: the answer is printed to the terminal${NC}"
        TEST_CASES=$((TEST_CASES + 1))
    else
        echo -e "      -> ${RED}❌ FAILED: the answer is not printed to the terminal${NC}"
        return 1
    fi
}

function test_stub_quiet() {
    stub_reset
    local term="$STUB_ROOT/term.txt" out="$STUB_ROOT/out.txt" code=0
    stub_cli "$term" -q -m "PING_QUIET" -o "$out" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect_file_is "$out" "$STUB_REPLY" || return 1
    if grep -q "$STUB_REPLY" "$term"; then
        echo -e "      -> ${RED}❌ FAILED: -q still printed the answer to the terminal${NC}"
        return 1
    fi
    echo -e "      -> ${GREEN}Verified: -q prints nothing of the answer${NC}"
    TEST_CASES=$((TEST_CASES + 1))
}

function test_stub_system_file() {
    stub_reset
    local term="$STUB_ROOT/term.txt" sys="$STUB_ROOT/sys.md" code=0
    printf 'SYSTEM_FILE_MARKER line one\nline two\n' > "$sys"
    stub_cli "$term" -sf "$sys" -m "hi" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect "-sf is sent as system_prompt_content" \
        "r.get('system_prompt_content') == 'SYSTEM_FILE_MARKER line one\nline two\n'" || return 1
    expect "-sf is the first (system) message" \
        "r['messages'][0] == {'role': 'system', 'content': 'SYSTEM_FILE_MARKER line one\nline two\n'}" || return 1
}

function test_stub_system_name() {
    stub_reset
    local term="$STUB_ROOT/term.txt" code=0
    mkdir -p "$STUB_HOME/system/system-prompt"
    printf 'SYSTEM_NAME_MARKER\n' > "$STUB_HOME/system/system-prompt/stub_guard.md"
    stub_cli "$term" -s "stub_guard" -m "hi" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect "-s NAME loads system-prompt/NAME.md" "'SYSTEM_NAME_MARKER' in (r.get('system_prompt_content') or '')" || return 1
}

function test_stub_file() {
    stub_reset
    local term="$STUB_ROOT/term.txt" file="$STUB_ROOT/context.txt" code=0
    printf 'FILE_MARKER_4285\n' > "$file"
    stub_cli "$term" -f "$file" -m "what is in the file?" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect "-f content is sent in a user message" "any('FILE_MARKER_4285' in u for u in users)" || return 1
    expect "-f names the file" "any('context.txt' in u for u in users)" || return 1
    expect "-m still comes last" "users[-1] == 'what is in the file?'" || return 1
}

function test_stub_task() {
    stub_reset
    local term="$STUB_ROOT/term.txt" code=0
    mkdir -p "$STUB_HOME/user/task"
    printf 'TASK_NAME_MARKER_7777\n' > "$STUB_HOME/user/task/stub_task.md"
    stub_cli "$term" -t "stub_task" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect "-t NAME sends the task text" "any('TASK_NAME_MARKER_7777' in u for u in users)" || return 1
}

function test_stub_task_file() {
    stub_reset
    local term="$STUB_ROOT/term.txt" task="$STUB_ROOT/my_task.md" code=0
    printf 'TASK_FILE_MARKER_8888\n' > "$task"
    stub_cli "$term" -tf "$task" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect "-tf sends the task file text" "any('TASK_FILE_MARKER_8888' in u for u in users)" || return 1
}

function test_stub_image() {
    stub_reset
    local term="$STUB_ROOT/term.txt" img="$STUB_ROOT/pixel.png" code=0
    # A valid 1x1 PNG.
    python3 -I -c "import base64,sys; open(sys.argv[1],'wb').write(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGD4DwABBAEAwS2OUAAAAABJRU5ErkJggg=='))" "$img"
    stub_cli "$term" -i "$img" -m "describe" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect "-i attaches one image to the last user message" \
        "len([m for m in r['messages'] if m.get('role') == 'user'][-1].get('images', [])) == 1" || return 1
    expect "the image is a PNG data URL" \
        "[m for m in r['messages'] if m.get('role') == 'user'][-1]['images'][0].startswith('data:image/png;base64,')" || return 1
}

function test_stub_folder_and_ext() {
    stub_reset
    local term="$STUB_ROOT/term.txt" dir="$STUB_ROOT/project" code=0
    mkdir -p "$dir/sub"
    printf 'PY_MARKER_A\n' > "$dir/a.py"
    printf 'PY_MARKER_B\n' > "$dir/sub/b.py"
    printf 'TXT_MARKER_C\n' > "$dir/c.txt"
    stub_cli "$term" -D "$dir" -e py -m "summarise" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect "-D sends a.py" "any('PY_MARKER_A' in u for u in users)" || return 1
    expect "-D includes sub-folders" "any('PY_MARKER_B' in u for u in users)" || return 1
    expect "-e py leaves c.txt out" "not any('TXT_MARKER_C' in u for u in users)" || return 1
}

function test_stub_all_together() {
    stub_reset
    local term="$STUB_ROOT/term.txt" out="$STUB_ROOT/out.txt" code=0
    printf 'COMBO_SYSTEM\n' > "$STUB_ROOT/combo-sys.md"
    printf 'COMBO_FILE\n' > "$STUB_ROOT/combo.txt"
    mkdir -p "$STUB_HOME/user/task"
    printf 'COMBO_TASK\n' > "$STUB_HOME/user/task/combo_task.md"
    stub_cli "$term" -sf "$STUB_ROOT/combo-sys.md" -f "$STUB_ROOT/combo.txt" -t combo_task -m "COMBO_MESSAGE" -o "$out" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect "one request carries everything" "len(reqs) == 1" || return 1
    expect "the system prompt is -sf" "r.get('system_prompt_content') == 'COMBO_SYSTEM\n'" || return 1
    expect "the file is sent" "any('COMBO_FILE' in u for u in users)" || return 1
    expect "the task is sent" "any('COMBO_TASK' in u for u in users)" || return 1
    expect "the message is sent" "any('COMBO_MESSAGE' in u for u in users)" || return 1
    expect "the file comes before the message" \
        "min(i for i, u in enumerate(users) if 'COMBO_FILE' in u) < max(i for i, u in enumerate(users) if 'COMBO_MESSAGE' in u)" || return 1
    expect_file_is "$out" "$STUB_REPLY" || return 1
}

function test_stub_system_file_is_sent_verbatim() {
    local term="$STUB_ROOT/term.txt" code sys
    # JSON, quotes, accents, markdown and a large file must reach the model unchanged.
    sys="$STUB_ROOT/json-sys.md"
    printf '{"role": "bot", "instruction": "Reply with \\"OK\\"", "lang": "português"}\n' > "$sys"
    stub_reset; code=0
    stub_cli "$term" -sf "$sys" -m "hi" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect "a JSON system prompt is sent verbatim" \
        "r.get('system_prompt_content') == open('$sys', encoding='utf-8').read()" || return 1
    sys="$STUB_ROOT/large-sys.md"
    : > "$sys"
    for i in $(seq 1 500); do echo "Line $i: Lorem ipsum dolor sit amet, consectetur adipiscing elit." >> "$sys"; done
    echo "LARGE_END_MARKER" >> "$sys"
    stub_reset; code=0
    stub_cli "$term" -sf "$sys" -m "hi" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect "a 500-line system prompt is sent whole" \
        "r.get('system_prompt_content') == open('$sys', encoding='utf-8').read()" || return 1
}

function test_stub_empty_system_file() {
    stub_reset
    local term="$STUB_ROOT/term.txt" sys="$STUB_ROOT/empty-sys.md" code=0
    : > "$sys"
    stub_cli "$term" -sf "$sys" -m "EMPTY_SYS_MESSAGE" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect "an empty -sf still sends the message" "users[-1] == 'EMPTY_SYS_MESSAGE'" || return 1
    expect "an empty -sf sends an empty system prompt" "not (r.get('system_prompt_content') or '').strip()" || return 1
}

function test_stub_sf_wins_over_s() {
    stub_reset
    local term="$STUB_ROOT/term.txt" code=0
    mkdir -p "$STUB_HOME/system/system-prompt"
    printf 'NAMED_PROMPT\n' > "$STUB_HOME/system/system-prompt/named.md"
    printf 'FILE_PROMPT\n' > "$STUB_ROOT/file-prompt.md"
    stub_cli "$term" -s named -sf "$STUB_ROOT/file-prompt.md" -m "hi" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect "-sf wins when both -s and -sf are given" "r.get('system_prompt_content') == 'FILE_PROMPT\n'" || return 1
}

function run_category_2() {
    echo -e "\n${GREEN}### Category 2: Parameters sent to the model ###${NC}"
    run_test "Message + Output (-m, -o)" "-m is sent as the last user message; -o gets exactly the answer." test_stub_message_and_output
    run_test "Quiet (-q)" "-q prints nothing of the answer while -o still gets it." test_stub_quiet
    run_test "System File (-sf)" "-sf content is sent verbatim as the system prompt." test_stub_system_file
    run_test "System Name (-s)" "-s NAME loads system/system-prompt/NAME.md." test_stub_system_name
    run_test "System File Content" "JSON, accents and a 500-line file are sent unchanged." test_stub_system_file_is_sent_verbatim
    run_test "Empty System File" "An empty -sf sends an empty system prompt and the message." test_stub_empty_system_file
    run_test "-s and -sf Together" "-sf wins over -s." test_stub_sf_wins_over_s
    run_test "File (-f)" "-f content and name are sent with the message." test_stub_file
    run_test "Task (-t)" "-t NAME sends the task template text." test_stub_task
    run_test "Task File (-tf)" "-tf sends the task file text." test_stub_task_file
    run_test "Folder + Extensions (-D, -e)" "-D loads the folder recursively; -e filters by extension." test_stub_folder_and_ext
    run_test "All Together (-sf -f -t -m -o)" "Every part reaches the model in one request." test_stub_all_together
    known_issue "Image (-i)" "-i should attach the image as a data URL; with a jarvis model it crashes (no load_images)." test_stub_image
}
