#!/bin/bash
# stub_utils.sh: the stub Brain Server and the helpers every CLI test category uses.
#
# The model is replaced by tests/e2e/stub_server.py through a "jarvis" model config. The stub
# records every request and always answers STUB_OK, so a test checks what the CLI sent (system
# prompt, files, task, images) or did with the answer (-o, -q) — never what a model decided to
# reply. No GPU and no model are needed.
#
# The runner starts one stub for the whole run (stub_start) and stops it on exit (stub_stop).
# Every run uses its own AI_ASSISTANT_DIRECTORY and free ports, so it never touches ~/Ai or a
# Brain Server running on this machine (port 9999).

STUB_REPLY="STUB_OK"

# --- stub lifecycle ---------------------------------------------------------------------

function stub_start() {
    STUB_ROOT=$(mktemp -d)
    STUB_STATE="$STUB_ROOT/stub"
    STUB_HOME="$STUB_ROOT/home"
    mkdir -p "$STUB_HOME"
    python3 -I "$SCRIPT_DIR/e2e/stub_server.py" "$STUB_STATE" &
    STUB_PID=$!
    for _ in $(seq 1 100); do
        [ -f "$STUB_STATE/port" ] && break
        sleep 0.1
    done
    if [ ! -f "$STUB_STATE/port" ]; then
        echo -e "   ${RED}❌ The stub server did not start${NC}"
        return 1
    fi
    STUB_PORT=$(cat "$STUB_STATE/port")
    STUB_MODEL="$STUB_ROOT/stub-model.json"
    cat > "$STUB_MODEL" <<EOF
{
  "model_name": "stub",
  "model_type": "jarvis",
  "model_properties": {
    "base_url": "http://127.0.0.1:$STUB_PORT",
    "server_model": "stub",
    "n_ctx": 4096,
    "max_new_tokens": 64,
    "timeout": 15
  }
}
EOF
    if [ "${AI_WINDOWS_CLI:-0}" -eq 1 ]; then
        STUB_CMD="./tests/e2e/run-windows-cli.sh -dc -md $STUB_MODEL"
    else
        STUB_CMD="./run.sh -dc -md $STUB_MODEL"
    fi
    log_verbose "Stub server on port $STUB_PORT, home $STUB_HOME"
    # Bootstrap the isolated home (creates its config.json) before tests edit its settings.
    AI_ASSISTANT_DIRECTORY="$STUB_HOME" $STUB_CMD models list > "$STUB_ROOT/bootstrap.txt" 2>&1 || true
}

function stub_stop() {
    stop_server /dev/null > /dev/null 2>&1 || true
    if [ -n "${STUB_PID:-}" ]; then
        kill -TERM "$STUB_PID" 2>/dev/null || true
        wait "$STUB_PID" 2>/dev/null || true
        STUB_PID=""
    fi
    if [ -n "${STUB_ROOT:-}" ]; then
        cleanup_files -r "$STUB_ROOT"
        STUB_ROOT=""
    fi
}

# Forget the requests of the previous test.
function stub_reset() {
    rm -rf "$STUB_STATE/requests" "$STUB_STATE/last.json"
}

# --- helpers ----------------------------------------------------------------------------

# stub_cli OUT_TERMINAL ARGS... : runs the CLI on the stub with an isolated home.
# Returns the CLI exit code; the terminal output goes to OUT_TERMINAL.
function stub_cli() {
    local term_out="$1"; shift
    echo -e "   ${YELLOW}[EXEC]${NC} ai $*"
    set +e
    AI_ASSISTANT_DIRECTORY="$STUB_HOME" $STUB_CMD "$@" > "$term_out" 2>&1
    local code=$?
    set -e
    return $code
}

# stub_query PYTHON_EXPR : evaluates an expression on the last request (variable "r") and on
# the list of all requests ("reqs"); prints the result.
function stub_query() {
    python3 -I - "$STUB_STATE" "$1" <<'EOF'
import glob, json, os, sys
state, expr = sys.argv[1], sys.argv[2]
reqs = [json.load(open(p, encoding="utf-8")) for p in sorted(glob.glob(os.path.join(state, "requests", "*.json")))]
r = reqs[-1] if reqs else {}
users = [m.get("content", "") for m in r.get("messages", []) if m.get("role") == "user"]
print(eval(expr))
EOF
}

# expect DESCRIPTION PYTHON_CONDITION : the condition must be True on the recorded request(s).
function expect() {
    local description="$1" condition="$2" result
    result=$(stub_query "$condition" 2>&1) || true
    if [ "$result" = "True" ]; then
        echo -e "      -> ${GREEN}Verified: $description${NC}"
        TEST_CASES=$((TEST_CASES + 1))
        return 0
    fi
    echo -e "      -> ${RED}❌ FAILED: $description${NC}"
    echo "         condition: $condition"
    echo "         result:    $result"
    echo "         last request:"
    sed 's/^/           /' "$STUB_STATE/last.json" 2>/dev/null || echo "           (no request recorded)"
    return 1
}

# expect_exit_ok CODE TERMINAL_FILE
function expect_exit_ok() {
    if [ "$1" -ne 0 ]; then
        echo -e "      -> ${RED}❌ FAILED: exit code $1${NC}"
        tail -20 "$2"
        return 1
    fi
    echo -e "      -> ${GREEN}Verified: exit code 0${NC}"
    TEST_CASES=$((TEST_CASES + 1))
}

# expect_file_is FILE TEXT : the file holds exactly TEXT (trailing newline ignored).
function expect_file_is() {
    local content
    content=$(cat "$1" 2>/dev/null) || content="(missing)"
    if [ "$content" = "$2" ]; then
        echo -e "      -> ${GREEN}Verified: $(basename "$1") contains exactly '$2'${NC}"
        TEST_CASES=$((TEST_CASES + 1))
        return 0
    fi
    echo -e "      -> ${RED}❌ FAILED: $(basename "$1") should contain exactly '$2', has: $content${NC}"
    return 1
}

function free_port() {
    python3 -I -c "import socket; s=socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1]); s.close()"
}

# expect_code EXPECTED ACTUAL TERMINAL_FILE DESCRIPTION
# EXPECTED is a number, or "nonzero".
function expect_code() {
    local expected="$1" actual="$2" term="$3" description="$4"
    if { [ "$expected" = "nonzero" ] && [ "$actual" -ne 0 ]; } || [ "$expected" = "$actual" ]; then
        echo -e "      -> ${GREEN}Verified: $description (exit $actual)${NC}"
        TEST_CASES=$((TEST_CASES + 1))
        return 0
    fi
    echo -e "      -> ${RED}❌ FAILED: $description — expected exit $expected, got $actual${NC}"
    tail -15 "$term"
    return 1
}

# expect_text FILE PATTERN DESCRIPTION [absent]
function expect_text() {
    local file="$1" pattern="$2" description="$3" mode="${4:-present}"
    if grep -aqiE -- "$pattern" "$file"; then
        [ "$mode" = "present" ] && { echo -e "      -> ${GREEN}Verified: $description${NC}"; TEST_CASES=$((TEST_CASES + 1)); return 0; }
    else
        [ "$mode" = "absent" ] && { echo -e "      -> ${GREEN}Verified: $description${NC}"; TEST_CASES=$((TEST_CASES + 1)); return 0; }
    fi
    echo -e "      -> ${RED}❌ FAILED: $description (pattern '$pattern' $mode expected)${NC}"
    tail -15 "$file"
    return 1
}

function expect_no_request() {
    if [ -f "$STUB_STATE/last.json" ]; then
        echo -e "      -> ${RED}❌ FAILED: $1 — a request reached the model${NC}"
        return 1
    fi
    echo -e "      -> ${GREEN}Verified: $1${NC}"
    TEST_CASES=$((TEST_CASES + 1))
}

# set_home_setting KEY JSON_VALUE : writes a setting into the isolated home's config.json.
function set_home_setting() {
    python3 -I - "$STUB_HOME/config.json" "$1" "$2" <<'EOF'
import json, sys
path, key, value = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
try:
    data = json.load(open(path, encoding="utf-8"))
except FileNotFoundError:
    data = {}
data[key] = value
json.dump(data, open(path, "w", encoding="utf-8"), indent=2)
EOF
}

# wait_health PORT SECONDS : prints /api/health once it answers; fails after SECONDS.
function wait_health() {
    local port="$1" seconds="$2" body
    for _ in $(seq 1 $((seconds * 2))); do
        body=$(python3 -I -c "import urllib.request,sys; print(urllib.request.urlopen('http://127.0.0.1:$port/api/health', timeout=2).read().decode())" 2>/dev/null) && { echo "$body"; return 0; }
        sleep 0.5
    done
    return 1
}

# start_server LOG ARGS... : starts the CLI server in the background (SERVER_PID).
function start_server() {
    local log="$1"; shift
    echo -e "   ${YELLOW}[EXEC]${NC} ai $* &"
    AI_ASSISTANT_DIRECTORY="$STUB_HOME" ./run.sh -dc "$@" > "$log" 2>&1 < /dev/null &
    SERVER_PID=$!
}

# stop_server LOG : SIGINT to the server's process group; waits up to 30 s for it to exit.
function stop_server() {
    local log="$1"
    [ -z "${SERVER_PID:-}" ] && return 0
    pkill -INT -P "$SERVER_PID" 2>/dev/null || true
    kill -INT "$SERVER_PID" 2>/dev/null || true
    for _ in $(seq 1 60); do
        kill -0 "$SERVER_PID" 2>/dev/null || break
        sleep 0.5
    done
    if kill -0 "$SERVER_PID" 2>/dev/null; then
        echo -e "      -> ${RED}❌ FAILED: the server did not stop within 30 s of SIGINT${NC}"
        pkill -KILL -P "$SERVER_PID" 2>/dev/null || true
        kill -KILL "$SERVER_PID" 2>/dev/null || true
        SERVER_PID=""
        return 1
    fi
    wait "$SERVER_PID" 2>/dev/null || true
    SERVER_PID=""
    echo -e "      -> ${GREEN}Verified: the server stopped on SIGINT${NC}"
    TEST_CASES=$((TEST_CASES + 1))
}
