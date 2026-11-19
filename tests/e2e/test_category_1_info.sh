#!/bin/bash
# Category 1: informational flags and listing commands. None of them should reach the model.

function test_help_flag() {
    stub_reset
    local term="$STUB_ROOT/term.txt" code=0
    stub_cli "$term" -h || code=$?
    expect_code 0 "$code" "$term" "-h exits cleanly" || return 1
    expect_text "$term" "usage: .*ai" "-h prints the usage line" || return 1
    expect_text "$term" "JUST A REASONING VIRTUAL INTELLIGENT SENTINEL AGENTIC INTERFACE" "-h prints the banner" || return 1
    expect_text "$term" "--msg" "-h lists --msg" || return 1
    expect_no_request "-h sends nothing to the model" || return 1
}

function test_command_help() {
    local term="$STUB_ROOT/term.txt" code
    for command in agent server models sessions knowledge; do
        code=0
        stub_cli "$term" "$command" --help || code=$?
        expect_code 0 "$code" "$term" "ai $command --help" || return 1
        expect_text "$term" "usage: .*$command" "ai $command --help prints its usage" || return 1
    done
}

function test_version_flag() {
    stub_reset
    local term="$STUB_ROOT/term.txt" code=0 version
    version=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1)
    stub_cli "$term" -v || code=$?
    expect_code 0 "$code" "$term" "-v exits cleanly" || return 1
    expect_text "$term" "Version" "-v prints a version line" || return 1
    expect_text "$term" "${version//./\\.}" "-v prints the pyproject version ($version)" || return 1
    expect_no_request "-v sends nothing to the model" || return 1
}

function test_show_logo() {
    local term="$STUB_ROOT/term.txt" code=0
    stub_cli "$term" --show-logo -v || code=$?
    expect_code 0 "$code" "$term" "--show-logo exits cleanly" || return 1
    expect_text "$term" "JARVIS|█" "--show-logo prints the logo" || return 1
}

function test_listings() {
    stub_reset
    local term="$STUB_ROOT/term.txt" code
    for command in "models list" "sessions list" "mcp list" "knowledge list" "server frontend list"; do
        code=0
        # shellcheck disable=SC2086
        stub_cli "$term" $command || code=$?
        expect_code 0 "$code" "$term" "ai $command" || return 1
        expect_text "$term" "Traceback" "ai $command prints no traceback" absent || return 1
    done
    expect_no_request "listings send nothing to the model" || return 1
}

function test_models_list_shows_configs() {
    local term="$STUB_ROOT/term.txt" code=0
    mkdir -p "$STUB_HOME/system/models/cli-tests"
    cp "$STUB_MODEL" "$STUB_HOME/system/models/cli-tests/stub-listed.json"
    stub_cli "$term" models list || code=$?
    expect_code 0 "$code" "$term" "ai models list" || return 1
    expect_text "$term" "cli-tests/stub-listed" "a config added to the models folder is listed" || return 1
    expect_text "$term" "jarvis" "its model type is shown" || return 1
    rm -rf "$STUB_HOME/system/models/cli-tests"
}

function test_legacy_flags() {
    local term="$STUB_ROOT/term.txt" code
    for flag in "-l" "-ls"; do
        code=0
        stub_cli "$term" "$flag" || code=$?
        expect_code 0 "$code" "$term" "legacy $flag still works" || return 1
        expect_text "$term" "Old flags still work but will go away" "legacy $flag warns it will go away" || return 1
    done
}

function run_category_1() {
    echo -e "\n${GREEN}### Category 1: Informational flags and listings ###${NC}"
    run_test "Help (-h)" "-h exits 0, prints the usage and sends nothing." test_help_flag
    run_test "Command Help (COMMAND --help)" "Each command prints its own usage." test_command_help
    run_test "Version (-v)" "-v prints the version from pyproject.toml." test_version_flag
    run_test "Show Logo (--show-logo)" "--show-logo prints the logo." test_show_logo
    run_test "Listings" "models/sessions/mcp/knowledge/frontend list exit 0 without a traceback." test_listings
    run_test "Models List" "A config in the models folder is listed with its type." test_models_list_shows_configs
    run_test "Legacy Flags (-l, -ls)" "Old flags still work and warn that they will go away." test_legacy_flags
}
