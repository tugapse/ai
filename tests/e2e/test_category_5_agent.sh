#!/bin/bash
# Category 5: agent mode (ai agent). The stub answers with scripted turns in the agent's XML
# format, so a test drives the agent loop (tool call -> tool result -> final answer) and checks
# what the CLI sent at each step. Runs happen in their own work folder.

# agent_turn_final TEXT : an agent turn that answers the user and ends the run.
function agent_turn_final() {
    cat <<EOF
<response>
  <thought><![CDATA[Answer the user.]]></thought>
  <manifest><phase>Done</phase><current_priority>Answer</current_priority></manifest>
  <notes><![CDATA[NOTES_MARKER]]></notes>
  <action>
    <tool_name>null</tool_name>
    <tool_parameters></tool_parameters>
    <agent_target>USER</agent_target>
  </action>
  <response_to_user><![CDATA[$1]]></response_to_user>
</response>
EOF
}

# agent_turn_tool TOOL PARAMETERS_XML : an agent turn that calls one tool.
function agent_turn_tool() {
    cat <<EOF
<response>
  <thought><![CDATA[Call $1.]]></thought>
  <manifest><phase>Discovery</phase><current_priority>Use $1</current_priority></manifest>
  <notes><![CDATA[calling $1]]></notes>
  <action>
    <tool_name>$1</tool_name>
    <tool_parameters>$2</tool_parameters>
    <agent_target>SELF</agent_target>
  </action>
  <response_to_user><![CDATA[Using $1]]></response_to_user>
</response>
EOF
}

# agent_cli TERMINAL_FILE ARGS... : runs "ai agent ARGS" in the work folder.
function agent_cli() {
    local term_out="$1"; shift
    local repo
    repo=$(pwd)
    mkdir -p "$AGENT_WORK"
    echo -e "   ${YELLOW}[EXEC]${NC} (cd work) ai agent $*"
    set +e
    (cd "$AGENT_WORK" && AI_ASSISTANT_DIRECTORY="$STUB_HOME" timeout 180 "$repo/run.sh" -dc -md "$STUB_MODEL" agent "$@") > "$term_out" 2>&1
    local code=$?
    set -e
    return $code
}

# The agent's input is one user message holding "<context>{...}</context>".
AGENT_INPUT="next(m['content'] for m in reversed(r['messages']) if m['role'] == 'user')"

function test_agent_answers() {
    stub_reset
    stub_reply_always "$(agent_turn_final AGENT_DONE_MARKER)"
    local term="$STUB_ROOT/term.txt" code=0
    agent_cli "$term" -m "AGENT_OBJECTIVE_1" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect "one model turn for a direct answer" "len(reqs) == 1" || return 1
    expect "the objective reaches the agent" "\"'objective': 'AGENT_OBJECTIVE_1'\" in $AGENT_INPUT" || return 1
    expect "the agent gets its system prompt" "len(r.get('system_prompt_content') or '') > 100" || return 1
    expect_text "$term" "AGENT_DONE_MARKER" "the answer is printed" || return 1
}

function test_agent_tool_call() {
    stub_reset
    local term="$STUB_ROOT/term.txt" code=0
    mkdir -p "$AGENT_WORK"
    printf 'WORK_FILE_MARKER\n' > "$AGENT_WORK/notes.txt"
    stub_reply_next "$(agent_turn_tool read_file '<path>@ROOT/notes.txt</path>')"
    stub_reply_always "$(agent_turn_final AGENT_DONE_MARKER)"
    agent_cli "$term" -m "read the notes" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect "two model turns: the tool call, then the answer" "len(reqs) == 2" || return 1
    expect "the 1st turn has not seen the file" "'WORK_FILE_MARKER' not in json.dumps(reqs[0])" || return 1
    expect "the tool result reaches the 2nd turn" "'WORK_FILE_MARKER' in $AGENT_INPUT" || return 1
    expect "the tool result is a success" "\"'status': 'SUCCESS'\" in $AGENT_INPUT" || return 1
    expect "the notes of the 1st turn are carried over" "\"'agent_notes': 'calling read_file'\" in $AGENT_INPUT" || return 1
    expect_text "$term" "AGENT_DONE_MARKER" "the final answer is printed" || return 1
}

function test_agent_session() {
    stub_reset
    stub_reply_always "$(agent_turn_final FIRST_ANSWER_MARKER)"
    local term="$STUB_ROOT/term.txt" code=0 session="cli-tests-$$"
    agent_cli "$term" --session-id "$session" -m "FIRST_OBJECTIVE" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    stub_reset
    stub_reply_always "$(agent_turn_final SECOND_ANSWER_MARKER)"
    agent_cli "$term" --session-id "$session" -m "SECOND_OBJECTIVE" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect "the 2nd run carries the 1st objective" "'FIRST_OBJECTIVE' in $AGENT_INPUT" || return 1
    expect "the 2nd run carries the 1st answer" "'FIRST_ANSWER_MARKER' in $AGENT_INPUT" || return 1
    expect "the 2nd run's objective is the new one" "\"'objective': 'SECOND_OBJECTIVE'\" in $AGENT_INPUT" || return 1
    stub_reset
    stub_reply_always "$(agent_turn_final THIRD_ANSWER_MARKER)"
    agent_cli "$term" --resume "$session" -m "THIRD_OBJECTIVE" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect "--resume continues the same session" "'SECOND_ANSWER_MARKER' in $AGENT_INPUT" || return 1
    stub_reset
    stub_reply_always "$(agent_turn_final OTHER_ANSWER)"
    agent_cli "$term" --session-id "other-$session" -m "OTHER_OBJECTIVE" || code=$?
    expect_exit_ok "$code" "$term" || return 1
    # Long-term memory (episodes) is shared on purpose; the conversation itself is not.
    expect "another session id starts with no conversation history" "\"'conversation_history': []\" in $AGENT_INPUT" || return 1
}

function test_agent_permission_denied_without_terminal() {
    stub_reset
    local term="$STUB_ROOT/term.txt" code=0
    mkdir -p "$AGENT_WORK"
    rm -f "$AGENT_WORK/should_not_exist"
    stub_reply_next "$(agent_turn_tool execute_command '<command>touch @ROOT/should_not_exist</command>')"
    stub_reply_always "$(agent_turn_final AGENT_DONE_MARKER)"
    agent_cli "$term" -m "run a command" < /dev/null || code=$?
    expect_exit_ok "$code" "$term" || return 1
    expect_text "$term" "denied: no terminal to ask for permission" "a gated tool is denied when no one can approve it" || return 1
    if [ -e "$AGENT_WORK/should_not_exist" ]; then
        echo -e "      -> ${RED}❌ FAILED: the denied command ran anyway${NC}"
        return 1
    fi
    echo -e "      -> ${GREEN}Verified: the denied command did not run${NC}"
    TEST_CASES=$((TEST_CASES + 1))
    expect "the agent is told access was denied" "len(reqs) == 2 and 'Access Denied' in $AGENT_INPUT" || return 1
}

function test_agent_errors() {
    local term="$STUB_ROOT/term.txt" code
    stub_reset; code=0
    agent_cli "$term" --resume "no-such-session-$$" -m "hi" || code=$?
    expect_code nonzero "$code" "$term" "--resume with an unknown id fails" || return 1
    expect_text "$term" "No agent session matching" "the error names the missing session" || return 1
    expect_no_request "--resume: nothing is sent to the model" || return 1
    stub_reset; code=0
    agent_cli "$term" --pipeline "no_such_pipeline" -m "hi" || code=$?
    expect_code nonzero "$code" "$term" "--pipeline with an unknown name fails" || return 1
    expect_text "$term" "Pipeline config 'no_such_pipeline.json' not found" "the error names the missing pipeline" || return 1
    expect_no_request "--pipeline: nothing is sent to the model" || return 1
}

function test_agent_failure_exit_code() {
    stub_reset
    stub_reply_always "NOT AN AGENT ANSWER"
    local term="$STUB_ROOT/term.txt" code=0
    agent_cli "$term" -m "hi" || code=$?
    expect_code nonzero "$code" "$term" "an agent that never produces valid output fails the command" || return 1
}

function run_category_5() {
    echo -e "\n${GREEN}### Category 5: Agent mode (ai agent) ###${NC}"
    AGENT_WORK="$STUB_ROOT/work"
    run_test "Agent Answer" "A direct answer: one turn, the objective sent, the answer printed." test_agent_answers
    run_test "Agent Tool Call" "A tool call runs and its result reaches the next turn." test_agent_tool_call
    run_test "Agent Session (--session-id, --resume)" "A session carries history; --resume continues it; another id starts empty." test_agent_session
    run_test "Agent Permission (no terminal)" "A gated tool (execute_command) is denied without a terminal and does not run." test_agent_permission_denied_without_terminal
    run_test "Agent Errors (--resume, --pipeline)" "Unknown session or pipeline fails and sends nothing." test_agent_errors
    known_issue "Agent Failure Exit Code" "A run that ends in an error should exit non-zero; today it exits 0." test_agent_failure_exit_code
}
