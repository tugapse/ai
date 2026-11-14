"""Turn-ending guards: idle self-targeted turns, repeated identical tool calls, repeated answers."""

import sys
import uuid
from unittest.mock import MagicMock

import pytest

import ai.functions as ai_functions

sys.modules.setdefault("ai.core.terminal_ui", MagicMock())
sys.modules.setdefault("ai.program", MagicMock())

from ai.agents.agent_io import AgentEventType, AgentIO
from ai.agents.agent_orchestrator import AgentOrchestrator, STAGNATION_STOP


class RecordingIO(AgentIO):
    blocking_user_input = False

    def __init__(self):
        self.events = []

    def emit(self, event):
        self.events.append(event)

    def request_permission(self, tool, params):
        return "yes"

    def of(self, kind):
        return [e for e in self.events if e.type == kind]


class Connector:
    def __init__(self, responses):
        self.responses = list(responses)
        self.payloads = []
        self.llm = MagicMock()

    def send_request(self, payload, prompt_file_path, agent_config):
        self.payloads.append(payload)
        return self.responses.pop(0) if self.responses else {"action": {"agent_target": "STOP"}}

    def get_context_limit(self):
        return 100000

    def get_max_tokens(self):
        return 1000


class Registry:
    def __init__(self):
        self.calls = []

    def register_tool(self, name, fn):
        pass

    def get_tool_info(self, name):
        return f"- {name}"

    def execute_tool(self, name, params):
        self.calls.append((name, params))
        return {"status": "SUCCESS", "content": "same result"}

    def get_all_tools(self):
        return {"read_file": lambda **kw: None}


PIPELINE = {
    "entry_point": "MASTER", "max_iterations": 20,
    "agents": {"MASTER": {"role": "management", "prompt_file_path": "m.md",
                          "allowed_targets": ["MASTER", "USER"], "tools": ["read_file"]}},
}


def answer(text, target="MASTER"):
    return {"action": {"tool_name": "null", "agent_target": target}, "response_to_user": text}


def read(path="@ROOT/a.py"):
    return {"action": {"tool_name": "read_file", "tool_parameters": {"path": path}, "agent_target": "SELF"}}


@pytest.fixture
def run(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_functions, "get_root_directory", MagicMock(return_value=str(tmp_path)))

    def _run(responses):
        io, conn, reg = RecordingIO(), Connector(responses), Registry()
        orch = AgentOrchestrator(conn, reg, PIPELINE, MagicMock(), io=io)
        orch._gatekeeper = lambda *a, **k: True
        result = orch.run_loop("question", session_id=f"s-{uuid.uuid4().hex}")
        return result, io, conn, reg, orch

    return _run


def system_notes(conn, step):
    return [m.get("message", "") for m in conn.payloads[step]["messages_received"] if m.get("from") == "SYSTEM"]


def test_answer_to_self_is_nudged_then_handed_to_user(run):
    result, io, conn, _, _ = run([answer("It is in a.py"), answer("It is in a.py"), answer("never asked")])
    assert result.reason == "awaiting_user"
    assert result.message == "It is in a.py"
    assert len(conn.payloads) == 2                       # third response never requested
    assert any("did not end" in m for m in system_notes(conn, 1))
    assert [e.text for e in io.of(AgentEventType.MESSAGE)] == ["It is in a.py"]   # shown once


def test_nudge_that_works_ends_normally(run):
    result, _, conn, _, _ = run([answer("It is in a.py"), answer("It is in a.py", target="USER")])
    assert result.reason == "awaiting_user"
    assert len(conn.payloads) == 2


def test_tool_call_resets_idle_counter(run):
    result, _, conn, reg, _ = run([answer("thinking"), read(), answer("still thinking"), answer("done", target="USER")])
    assert len(reg.calls) == 1
    assert len(conn.payloads) == 4                       # the idle turn after the tool call was only nudged
    assert result.message == "done"


def test_empty_target_without_tool_is_nudged(run):
    result, _, conn, _, _ = run([{"action": {"tool_name": "null"}}, answer("ok", target="USER")])
    assert any("called no tool" in m for m in system_notes(conn, 1))


def test_repeated_identical_tool_calls_warn_then_stop(run):
    result, io, conn, reg, _ = run([read() for _ in range(STAGNATION_STOP + 2)])
    assert len(reg.calls) == STAGNATION_STOP - 1         # the stopping call is not executed
    assert any("same parameters" in m for m in system_notes(conn, 3))
    assert result.reason == "awaiting_user"
    assert any("Stopped: MASTER called read_file" in e.text for e in io.of(AgentEventType.ERROR))


def test_different_parameters_are_not_stagnation(run):
    result, io, _, reg, _ = run([read(f"@ROOT/{i}.py") for i in range(6)] + [answer("done", target="USER")])
    assert len(reg.calls) == 6
    assert not io.of(AgentEventType.ERROR)


def test_agent_name_in_tool_name_delegates(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_functions, "get_root_directory", MagicMock(return_value=str(tmp_path)))
    pipeline = {"entry_point": "MASTER", "max_iterations": 5, "agents": {
        "MASTER": {"role": "management", "prompt_file_path": "m.md", "allowed_targets": ["MASTER", "SECRETARY", "USER"], "tools": ["read_file"]},
        "SECRETARY": {"role": "labor", "prompt_file_path": "s.md", "allowed_targets": ["MASTER"], "tools": ["read_file"]},
    }}
    responses = [
        {"action": {"tool_name": "SECRETARY", "agent_target": "MASTER", "message_to_target": "read a.py"}},
        {"action": {"tool_name": "null", "agent_target": "MASTER", "message_to_target": "a.py defines f()"}},
        answer("a.py defines f()", target="USER"),
    ]
    io, conn, reg = RecordingIO(), Connector(responses), Registry()
    orch = AgentOrchestrator(conn, reg, pipeline, MagicMock(), io=io)
    result = orch.run_loop("what is in a.py?", session_id=f"s-{uuid.uuid4().hex}")
    assert not [e for e in io.events if e.type == AgentEventType.TOOL_RESULT]   # no UNAUTHORIZED tool call
    assert conn.payloads[1]["messages_received"][-1]["message"] == "read a.py"    # SECRETARY got the task
    assert result.reason == "awaiting_user" and result.message == "a.py defines f()"


TEAM = {"entry_point": "MASTER", "max_iterations": 8, "agents": {
    "MASTER": {"role": "management", "prompt_file_path": "m.md", "allowed_targets": ["MASTER", "SECRETARY", "USER"], "tools": ["read_file"]},
    "SECRETARY": {"role": "labor", "prompt_file_path": "s.md", "allowed_targets": ["MASTER"], "tools": ["read_file"]},
}}


def run_team(tmp_path, monkeypatch, responses):
    monkeypatch.setattr(ai_functions, "get_root_directory", MagicMock(return_value=str(tmp_path)))
    io, conn, reg = RecordingIO(), Connector(responses), Registry()
    orch = AgentOrchestrator(conn, reg, TEAM, MagicMock(), io=io)
    orch._gatekeeper = lambda *a, **k: True
    return orch.run_loop("compare config.py and settings.py", session_id=f"s-{uuid.uuid4().hex}"), conn


def test_delegation_without_message_passes_the_task_on(tmp_path, monkeypatch):
    result, conn = run_team(tmp_path, monkeypatch, [
        {"action": {"tool_name": "null", "agent_target": "SECRETARY"}, "response_to_user": "Asking the SECRETARY."},
        answer("config.py loads env vars", target="MASTER"),
        answer("Done", target="USER"),
    ])
    objective = conn.payloads[1]["objective"]
    assert "compare config.py and settings.py" in objective
    assert "Asking the SECRETARY." in objective


def test_labor_objective_survives_tool_calls(tmp_path, monkeypatch):
    result, conn = run_team(tmp_path, monkeypatch, [
        {"action": {"tool_name": "null", "agent_target": "SECRETARY", "message_to_target": "Read config.py and report."}},
        read("@ROOT/config.py"),                                   # SECRETARY calls a tool
        answer("config.py loads env vars", target="MASTER"),       # next SECRETARY step
        answer("Done", target="USER"),
    ])
    assert conn.payloads[1]["objective"] == "Read config.py and report."
    assert conn.payloads[2]["objective"] == "Read config.py and report."   # not 'Continue.' after the tool result


def test_same_call_written_differently_counts_as_repeat():
    from ai.agents.memory_manager import MemoryManager
    mm = MemoryManager(["MASTER"])
    assert not mm.check_stagnation("read_files", {"paths": ["a.py", "b.py"], "intent": "first"})
    assert not mm.check_stagnation("read_files", {"paths": ["b.py", " a.py "], "intent": "again"})
    assert mm.check_stagnation("read_files", {"paths": ["a.py", "b.py"]})
    mm2 = MemoryManager(["MASTER"])
    mm2.check_stagnation("read_file", {"path": ["a.py"]})
    mm2.check_stagnation("read_file", {"path": "a.py"})
    assert mm2.check_stagnation("read_file", {"path": "a.py "})
    assert not MemoryManager(["MASTER"]).check_stagnation("read_file", {"path": "x.py"})
