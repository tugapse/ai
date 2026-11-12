"""Human-in-the-loop: non-interactive command execution, HIL_TOOLS gating and previews."""

import re
import time

import pytest

import ai.program  # noqa: F401  (startup import order, avoids a circular import)
from ai.config import ProgramConfig, ProgramSetting
from ai.agents.agent_io import AgentEventType, PERMISSION_YES, PERMISSION_NO
from ai.agents.tool_preview import describe_tool_request
import ai.tools.agent_tools as agent_tools

# Reuse the orchestrator fakes
from test_agent_chat import RecordingIO, make_orchestrator, isolate  # noqa: F401

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def plain(lines):
    return "\n".join(ANSI.sub("", line) for line in lines)


class TestNonInteractiveCommands:
    @pytest.fixture(autouse=True)
    def project_root(self, tmp_path, monkeypatch):
        monkeypatch.setattr(agent_tools, "PROJECT_ROOT", str(tmp_path))

    def test_stdin_is_closed(self, tmp_path):
        start = time.monotonic()
        result = agent_tools.execute_command(command="read answer; echo got:[$answer]", path="@ROOT")
        assert time.monotonic() - start < 5
        assert "got:[]" in result["stdout"]

    def test_no_controlling_terminal(self, tmp_path):
        start = time.monotonic()
        result = agent_tools.execute_command(command="cat /dev/tty", path="@ROOT", timeout=10)
        assert time.monotonic() - start < 5
        assert result["status"] == "FAILED"

    def test_pager_and_editor_env(self, tmp_path):
        result = agent_tools.execute_command(command="echo $GIT_PAGER $PAGER $GIT_EDITOR $GIT_TERMINAL_PROMPT", path="@ROOT")
        assert result["stdout"].split() == ["cat", "cat", "true", "0"]

    def test_timeout_kills_whole_process_group(self, tmp_path):
        marker = tmp_path / "survived"
        start = time.monotonic()
        result = agent_tools.execute_command(
            command=f"(sleep 3; touch {marker}) & sleep 30", path="@ROOT", timeout=1
        )
        assert time.monotonic() - start < 6
        assert result["status"] == "FAILED" and "timed out" in result["error"]
        time.sleep(3.5)
        assert not marker.exists(), "background child outlived the timeout"

    def test_success_and_failure(self, tmp_path):
        ok = agent_tools.execute_command(command="echo hi", path="@ROOT")
        assert ok["status"] == "SUCCESS" and ok["stdout"].strip() == "hi"
        bad = agent_tools.execute_command(command="exit 3", path="@ROOT")
        assert bad["status"] == "FAILED" and bad["returncode"] == 3


@pytest.fixture
def hil_tools():
    config = ProgramConfig.get_current()
    original = config.get(ProgramSetting.HIL_TOOLS)

    def set_tools(tools):
        config.set(ProgramSetting.HIL_TOOLS, tools)

    yield set_tools
    config.set(ProgramSetting.HIL_TOOLS, original)


PIPELINE = {
    "entry_point": "MASTER",
    "max_iterations": 10,
    "agents": {"MASTER": {
        "role": "management",
        "tools": ["write_file", "execute_command", "read_file"],
        "allowed_targets": ["MASTER", "USER", "STOP"],
        "prompt_file_path": "m.md",
    }},
}


class TestHilToolsSetting:
    def test_gating_follows_config(self, hil_tools):
        hil_tools(["write_file"])
        io = RecordingIO(permission=PERMISSION_YES)
        orch, _, reg = make_orchestrator([
            {"action": {"tool_name": "execute_command", "tool_parameters": {"command": "ls"}}},
            {"action": {"tool_name": "write_file", "tool_parameters": {"path": "a.txt", "content": "x"}}},
            {"action": {"agent_target": "STOP"}},
        ], io=io, pipeline=PIPELINE)
        orch.run_loop("go", "s-hil")
        assert [t for t, _ in io.permission_requests] == ["write_file"]
        assert [name for name, _ in reg.executed] == ["execute_command", "write_file"]

    def test_denied_write_is_not_executed(self, hil_tools):
        hil_tools(["execute_command", "write_file", "patch_file", "delete_file"])
        io = RecordingIO(permission=PERMISSION_NO)
        orch, _, reg = make_orchestrator([
            {"action": {"tool_name": "write_file", "tool_parameters": {"path": "a.txt", "content": "x"}}},
            {"action": {"agent_target": "STOP"}},
        ], io=io, pipeline=PIPELINE)
        orch.run_loop("go", "s-hil2")
        assert reg.executed == []

    def test_missing_setting_falls_back_to_execute_command(self, hil_tools):
        hil_tools(None)
        io = RecordingIO(permission=PERMISSION_YES)
        orch, _, _ = make_orchestrator([
            {"action": {"tool_name": "write_file", "tool_parameters": {"path": "a", "content": "x"}}},
            {"action": {"tool_name": "execute_command", "tool_parameters": {"command": "ls"}}},
            {"action": {"agent_target": "STOP"}},
        ], io=io, pipeline=PIPELINE)
        orch.run_loop("go", "s-hil3")
        assert [t for t, _ in io.permission_requests] == ["execute_command"]


class TestUserHandBack:
    def test_hand_back_without_question_does_not_print_generic_prompt(self):
        io = RecordingIO()
        orch, _, _ = make_orchestrator([
            {"response_to_user": "Output: hello", "action": {"agent_target": "USER"}},
        ], io=io)
        result = orch.run_loop("go", "s-hand")
        assert result.reason == "awaiting_user"
        assert result.message == "Output: hello"
        assert AgentEventType.QUESTION not in io.types()

    def test_explicit_question_is_shown(self):
        io = RecordingIO()
        orch, _, _ = make_orchestrator([
            {"response_to_user": "Found two files.", "action": {"agent_target": "USER", "message_to_target": "Which one?"}},
        ], io=io)
        orch.run_loop("go", "s-q2")
        questions = [e.text for e in io.events if e.type == AgentEventType.QUESTION]
        assert questions == ["Which one?"]


class TestPreview:
    def test_execute_command(self):
        text = plain(describe_tool_request("execute_command", {"command": "rm -rf build", "path": "src"}))
        assert "rm -rf build" in text and "src" in text

    def test_write_file_preview_and_truncation(self, tmp_path):
        content = "\n".join(f"line {i}" for i in range(20))
        text = plain(describe_tool_request("write_file", {"path": str(tmp_path / "new.py"), "content": content}))
        assert "new file · 20 lines" in text and "+ line 0" in text and "more lines" in text
        existing = tmp_path / "old.py"
        existing.write_text("x")
        assert "overwrite" in plain(describe_tool_request("write_file", {"path": str(existing), "content": "y"}))

    def test_patch_file_diff(self):
        text = plain(describe_tool_request("patch_file", {"path": "a.py", "search": "old()", "replace": "new()"}))
        assert "- old()" in text and "+ new()" in text

    def test_generic_tool(self):
        text = plain(describe_tool_request("my_mcp", {"command": "list", "limit": 5}))
        assert "my_mcp" in text and "list" in text and "5" in text


class OrderIO(RecordingIO):
    """Records permission requests in the same timeline as events."""

    def request_permission(self, tool, params):
        self.events.append(SimpleEvent("PERMISSION", tool))
        return PERMISSION_YES


class SimpleEvent:
    def __init__(self, type_, text):
        self.type, self.text, self.data = type_, text, {}


def timeline(io):
    return [(e.type if isinstance(e.type, str) else e.type.value, e.text) for e in io.events
            if (e.type == "PERMISSION") or e.type in (AgentEventType.MESSAGE, AgentEventType.QUESTION)
            or (e.type == AgentEventType.STATUS and e.data.get("fresh"))]


class TestStatusComesFirst:
    def test_status_and_message_before_permission(self, hil_tools):
        hil_tools(["execute_command"])
        io = OrderIO()
        orch, _, _ = make_orchestrator([
            {"manifest": {"phase": "exec", "current_priority": "Run the build"},
             "response_to_user": "Running the build now.",
             "action": {"tool_name": "execute_command", "tool_parameters": {"command": "make"}}},
            {"action": {"agent_target": "STOP"}},
        ], io=io, pipeline=PIPELINE)
        orch.run_loop("build it", "s-order")
        assert timeline(io)[:3] == [("status", "Run the build"), ("message", "Running the build now."), ("PERMISSION", "execute_command")]

    def test_status_before_user_question(self):
        io = RecordingIO()
        orch, _, _ = make_orchestrator([
            {"manifest": {"current_priority": "Need a decision"},
             "response_to_user": "Two options found.",
             "action": {"agent_target": "USER", "message_to_target": "A or B?"}},
        ], io=io)
        orch.run_loop("go", "s-order2")
        assert timeline(io) == [("status", "Need a decision"), ("message", "Two options found."), ("question", "A or B?")]

    def test_unchanged_status_not_repeated(self):
        io = RecordingIO()
        same = {"manifest": {"current_priority": "Reading files"}, "action": {"tool_name": "read_file", "tool_parameters": {"path": "a"}}}
        orch, _, _ = make_orchestrator([dict(same), dict(same), {"action": {"agent_target": "STOP"}}], io=io)
        orch.run_loop("go", "s-order3")
        fresh = [e.text for e in io.events if e.type == AgentEventType.STATUS and e.data.get("fresh")]
        assert fresh == ["Reading files"]

    def test_console_prints_fresh_status_only(self, monkeypatch):
        from ai.agents.agent_io import AgentEvent, ConsoleIO
        printed = []
        monkeypatch.setattr("ai.agents.agent_io.TerminalUI.status", lambda agent, text: printed.append(text))
        io = ConsoleIO()
        io.emit(AgentEvent(AgentEventType.STATUS, "M", "first step task", {"fresh": False, "iteration": 1}))
        io.emit(AgentEvent(AgentEventType.STATUS, "M", "stale", {"fresh": False, "iteration": 2}))
        io.emit(AgentEvent(AgentEventType.STATUS, "M", "Run the build", {"fresh": True}))
        assert printed == ["first step task", "Run the build"]

    def test_chat_commits_fresh_status_line(self):
        from ai.agents.agent_io import AgentEvent
        from ai.agents.chat_ui.bridge import ChatIO
        from ai.agents.chat_ui.renderer import LiveState
        out = []
        io = ChatIO(LiveState(), out.append, lambda: None)
        io.emit(AgentEvent(AgentEventType.STATUS, "M", "progress", {"fresh": False}))
        io.emit(AgentEvent(AgentEventType.STATUS, "M", "Run the build", {"fresh": True, "phase": "exec"}))
        assert len(out) == 1 and "Run the build" in out[0] and "exec" in out[0]


def test_tool_with_user_target_still_runs():
    """Regression: patch_file + agent_target USER skipped the tool but the agent claimed success."""
    io = RecordingIO(permission=PERMISSION_YES)
    orch, _, reg = make_orchestrator([
        {"response_to_user": "Renamed it.", "action": {"tool_name": "read_file", "tool_parameters": {"path": "a"}, "agent_target": "USER"}},
    ], io=io, pipeline=PIPELINE)
    result = orch.run_loop("go", "s-user-tool")
    assert result.reason == "awaiting_user"
    assert reg.executed == [("read_file", {"path": "a"})]
