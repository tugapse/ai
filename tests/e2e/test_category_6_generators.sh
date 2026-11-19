#!/bin/bash
# Category 6: commands that write files into the AI folder (models generate, tools create,
# config reset). Checked on the isolated AI_ASSISTANT_DIRECTORY, never on ~/Ai.

# generate_types TYPES... : models generate writes a valid config for each type.
function generate_types() {
    local term="$STUB_ROOT/term.txt" code type file
    for type in "$@"; do
        code=0
        file="$STUB_HOME/user/models/cli_gen_$type.json"
        rm -f "$file"
        stub_cli "$term" models generate "cli_gen_$type" --type "$type" || code=$?
        expect_code 0 "$code" "$term" "models generate --type $type" || return 1
        if python3 -I -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d['model_type']==sys.argv[2] and d['model_name']==sys.argv[3] and isinstance(d.get('model_properties'), dict) else 1)" "$file" "$type" "cli_gen_$type"; then
            echo -e "      -> ${GREEN}Verified: user/models/cli_gen_$type.json is valid JSON of type $type${NC}"
            TEST_CASES=$((TEST_CASES + 1))
        else
            echo -e "      -> ${RED}❌ FAILED: user/models/cli_gen_$type.json is missing or wrong${NC}"
            cat "$file" 2>/dev/null
            return 1
        fi
    done
}

function test_models_generate() {
    stub_reset
    local term="$STUB_ROOT/term.txt" code=0
    generate_types gguf ollama causal_lm || return 1
    stub_cli "$term" models list || code=$?
    expect_text "$term" "cli_gen_ollama" "generated configs show up in models list" || return 1
    expect_no_request "nothing is sent to the model" || return 1
    rm -f "$STUB_HOME"/user/models/cli_gen_*.json
}

function test_models_generate_other_types() {
    # seq2seq_lm, gemini, openai and jarvis have no template: today they write "{}" with exit 0.
    generate_types seq2seq_lm gemini openai jarvis || return 1
    rm -f "$STUB_HOME"/user/models/cli_gen_*.json
}

function test_models_generate_bad_type() {
    local term="$STUB_ROOT/term.txt" code=0
    stub_cli "$term" models generate cli_gen_bad --type no_such_type || code=$?
    expect_code 2 "$code" "$term" "an unknown --type is refused" || return 1
    expect_text "$term" "invalid choice: 'no_such_type'" "the error names the bad type" || return 1
    if [ -e "$STUB_HOME/user/models/cli_gen_bad.json" ]; then
        echo -e "      -> ${RED}❌ FAILED: a config was written for a bad type${NC}"
        return 1
    fi
    echo -e "      -> ${GREEN}Verified: no config is written${NC}"
    TEST_CASES=$((TEST_CASES + 1))
}

function test_tools_create() {
    stub_reset
    local term="$STUB_ROOT/term.txt" code=0 file="$STUB_HOME/user/tools/cli_tool.py"
    rm -f "$file"
    stub_cli "$term" tools create cli_tool || code=$?
    expect_code 0 "$code" "$term" "tools create" || return 1
    if [ -f "$file" ] && grep -q "def cli_tool" "$file"; then
        echo -e "      -> ${GREEN}Verified: user/tools/cli_tool.py defines cli_tool${NC}"
        TEST_CASES=$((TEST_CASES + 1))
    else
        echo -e "      -> ${RED}❌ FAILED: the tool skeleton is missing${NC}"
        return 1
    fi
    if .venv/bin/python -I -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$file"; then
        echo -e "      -> ${GREEN}Verified: the skeleton is valid Python${NC}"
        TEST_CASES=$((TEST_CASES + 1))
    else
        echo -e "      -> ${RED}❌ FAILED: the skeleton is not valid Python${NC}"
        return 1
    fi
    printf '\n# EDITED_BY_TEST\n' >> "$file"
    code=0
    stub_cli "$term" tools create cli_tool || code=$?
    expect_code nonzero "$code" "$term" "creating the same tool again fails" || return 1
    expect_text "$term" "already exists" "the error says the tool exists" || return 1
    if grep -q "EDITED_BY_TEST" "$file"; then
        echo -e "      -> ${GREEN}Verified: the existing tool is not overwritten${NC}"
        TEST_CASES=$((TEST_CASES + 1))
    else
        echo -e "      -> ${RED}❌ FAILED: the existing tool was overwritten${NC}"
        return 1
    fi
    expect_no_request "nothing is sent to the model" || return 1
    rm -f "$file"
}

function test_models_generate_keeps_existing() {
    local term="$STUB_ROOT/term.txt" code=0 file="$STUB_HOME/user/models/cli_keep.json"
    stub_cli "$term" models generate cli_keep --type gguf || code=$?
    python3 -I -c "import json,sys; p=sys.argv[1]; d=json.load(open(p)); d['EDITED_BY_TEST']=True; json.dump(d, open(p,'w'))" "$file"
    code=0
    stub_cli "$term" models generate cli_keep --type gguf || code=$?
    local kept
    kept=$(python3 -I -c "import json,sys; print(json.load(open(sys.argv[1])).get('EDITED_BY_TEST', False))" "$file")
    rm -f "$file"
    if [ "$kept" = "True" ] || [ "$code" -ne 0 ]; then
        echo -e "      -> ${GREEN}Verified: an existing model config is not overwritten silently${NC}"
        TEST_CASES=$((TEST_CASES + 1))
        return 0
    fi
    echo -e "      -> ${RED}❌ FAILED: models generate overwrote an existing config without asking (exit 0)${NC}"
    return 1
}

function test_config_reset() {
    local term="$STUB_ROOT/term.txt" code=0 config="$STUB_HOME/config.json" backup="$STUB_ROOT/config.backup.json"
    cp "$config" "$backup"
    set_home_setting CLI_TESTS_MARKER '"keep-me?"'
    stub_cli "$term" config reset < /dev/null || code=$?
    expect_code 0 "$code" "$term" "config reset" || { cp "$backup" "$config"; return 1; }
    if python3 -I -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if 'CLI_TESTS_MARKER' not in d and 'ROOT_DIRECTORY' in d else 1)" "$config"; then
        echo -e "      -> ${GREEN}Verified: config.json is back to the defaults${NC}"
        TEST_CASES=$((TEST_CASES + 1))
    else
        echo -e "      -> ${RED}❌ FAILED: config.json was not reset${NC}"
        cp "$backup" "$config"; return 1
    fi
    cp "$backup" "$config"
}

function run_category_6() {
    echo -e "\n${GREEN}### Category 6: Commands that write files (models generate, tools create, config reset) ###${NC}"
    run_test "Models Generate" "models generate writes a valid gguf/ollama/causal_lm config, listed afterwards." test_models_generate
    known_issue "Models Generate (other types)" "seq2seq_lm, gemini, openai and jarvis should get a config (or be refused); today they write {} with exit 0." test_models_generate_other_types
    run_test "Models Generate (bad type)" "An unknown --type exits 2 and writes nothing." test_models_generate_bad_type
    run_test "Tools Create" "tools create writes a valid skeleton and never overwrites an existing tool." test_tools_create
    run_test "Config Reset" "config reset puts config.json back to the defaults." test_config_reset
    known_issue "Models Generate Overwrite" "models generate should not overwrite an existing config silently (tools create refuses)." test_models_generate_keeps_existing
}
