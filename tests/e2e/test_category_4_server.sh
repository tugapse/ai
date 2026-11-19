#!/bin/bash
# Category 4: the Brain Server and relay mode, on free ports (never 9999), against the stub.

function test_server_starts_empty() {
    local log="$STUB_ROOT/server.log" port health
    port=$(free_port)
    set_home_setting SERVER_PORT "$port"
    set_home_setting SERVER_HOST '"127.0.0.1"'
    start_server "$log" server
    if ! health=$(wait_health "$port" 90); then
        echo -e "      -> ${RED}❌ FAILED: /api/health did not answer on port $port within 90 s${NC}"
        tail -20 "$log"; stop_server "$log"; return 1
    fi
    echo -e "      -> ${GREEN}Verified: ai server answers /api/health on port $port${NC}"
    TEST_CASES=$((TEST_CASES + 1))
    if python3 -I -c "import json,sys; d=json.loads(sys.argv[1]); sys.exit(0 if d['status']=='online' and d['loaded'] is False else 1)" "$health"; then
        echo -e "      -> ${GREEN}Verified: without --model it starts with no model loaded${NC}"
        TEST_CASES=$((TEST_CASES + 1))
    else
        echo -e "      -> ${RED}❌ FAILED: unexpected health: $health${NC}"; stop_server "$log"; return 1
    fi
    stop_server "$log" || return 1
    expect_text "$log" "graceful shutdown" "the server logs a graceful shutdown" || return 1
}

function test_relay() {
    stub_reset
    local log="$STUB_ROOT/relay.log" port health code
    port=$(free_port)
    set_home_setting SERVER_PORT "$port"
    set_home_setting SERVER_HOST '"127.0.0.1"'
    start_server "$log" server --relay "http://127.0.0.1:$STUB_PORT"
    if ! health=$(wait_health "$port" 90); then
        echo -e "      -> ${RED}❌ FAILED: the relay did not answer on port $port within 90 s${NC}"
        tail -20 "$log"; stop_server "$log"; return 1
    fi
    if python3 -I -c "import json,sys; d=json.loads(sys.argv[1]); sys.exit(0 if (d.get('relay') or '').startswith('http://127.0.0.1:$STUB_PORT') else 1)" "$health"; then
        echo -e "      -> ${GREEN}Verified: health reports the relay target${NC}"
        TEST_CASES=$((TEST_CASES + 1))
    else
        echo -e "      -> ${RED}❌ FAILED: health does not report the relay: $health${NC}"; stop_server "$log"; return 1
    fi
    code=0
    python3 -I -c "
import json, sys, urllib.request
req = urllib.request.Request('http://127.0.0.1:$port/api/v1/chat/completions', method='POST',
    data=json.dumps({'model': 'stub', 'messages': [{'role': 'user', 'content': 'RELAY_MARKER'}]}).encode(),
    headers={'Content-Type': 'application/json', 'X-Jarvis-Client': 'cli-tests'})
body = json.loads(urllib.request.urlopen(req, timeout=60).read())
sys.exit(0 if body['choices'][0]['message']['content'] == 'STUB_OK' else 1)
" || code=$?
    if [ "$code" -ne 0 ]; then
        echo -e "      -> ${RED}❌ FAILED: a chat sent to the relay did not come back with the stub answer${NC}"
        tail -20 "$log"; stop_server "$log"; return 1
    fi
    echo -e "      -> ${GREEN}Verified: a chat sent to the relay gets the Brain's answer${NC}"
    TEST_CASES=$((TEST_CASES + 1))
    expect "the relay forwarded the message to the Brain" "users[-1] == 'RELAY_MARKER'" || { stop_server "$log"; return 1; }
    stop_server "$log" || return 1
}

function test_legacy_server_flag() {
    local log="$STUB_ROOT/legacy-server.log" port
    port=$(free_port)
    set_home_setting SERVER_PORT "$port"
    set_home_setting SERVER_HOST '"127.0.0.1"'
    start_server "$log" --server
    if ! wait_health "$port" 90 > /dev/null; then
        echo -e "      -> ${RED}❌ FAILED: legacy --server did not answer within 90 s${NC}"
        tail -20 "$log"; stop_server "$log"; return 1
    fi
    echo -e "      -> ${GREEN}Verified: legacy --server still starts the server${NC}"
    TEST_CASES=$((TEST_CASES + 1))
    stop_server "$log" || return 1
    expect_text "$log" "Old flags still work but will go away" "legacy --server warns it will go away" || return 1
}

function run_category_4() {
    echo -e "\n${GREEN}### Category 4: Server and relay ###${NC}"
    if [ "${AI_WINDOWS_CLI:-0}" -eq 1 ]; then
        echo -e "   -> ${YELLOW}SKIPPED: server tests need POSIX signal forwarding.${NC}"
        TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
        return
    fi
    run_test "Server (ai server)" "Starts on a free port with no model, answers health, stops on SIGINT." test_server_starts_empty
    run_test "Relay (ai server --relay)" "A relay forwards chats to the Brain (the stub)." test_relay
    run_test "Legacy Server Flag (--server)" "The old --server flag still starts the server and warns." test_legacy_server_flag
}
