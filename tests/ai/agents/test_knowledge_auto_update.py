"""Knowledge kept in sync: files written in a run are regenerated when the turn ends."""

import sys
import uuid
from unittest.mock import MagicMock

import pytest

import ai.functions as ai_functions

sys.modules.setdefault("ai.core.terminal_ui", MagicMock())
sys.modules.setdefault("ai.program", MagicMock())

from ai.agents.agent_io import AgentIO
from ai.agents.agent_orchestrator import AgentOrchestrator


class QuietIO(AgentIO):
    blocking_user_input = False

    def emit(self, event):
        pass

    def request_permission(self, tool, params):
        return "yes"
from ai.modules.knowledge.store import KnowledgeStore


class Connector:
    def __init__(self, responses):
        self.responses = list(responses)
        self.llm = MagicMock(name="llm")

    def send_request(self, payload, prompt_file_path, agent_config):
        return self.responses.pop(0) if self.responses else {"action": {"agent_target": "STOP"}}

    def get_context_limit(self):
        return 100000

    def get_max_tokens(self):
        return 1000


class Registry:
    def __init__(self):
        self.tools = {}

    def register_tool(self, name, fn):
        self.tools[name] = fn

    def get_tool_info(self, name):
        return f"- {name}"

    def execute_tool(self, name, params):
        if name in self.tools:
            return self.tools[name](**params)
        return {"status": "SUCCESS"}

    def get_all_tools(self):
        return {"write_file": None, **self.tools}


class FakeService:
    def __init__(self, built=True):
        self.calls = []
        self.registry = MagicMock()
        self.registry.build_config.return_value = {"output": "/kb/out"} if built else {}

    def build(self, project, llm=None, files=None, max_files=None, **kw):
        self.calls.append({"project": project, "llm": llm, "files": files, "max_files": max_files})
        return {"done": ["app/main.py"], "failed": [], "remaining": 0}


class Module:
    def __init__(self, store):
        self.store = store

    def ensure_project(self, root):
        return []

    def get_instance(self):
        return self.store


PIPELINE = {"entry_point": "MASTER", "max_iterations": 5, "agents": {"MASTER": {
    "role": "management", "prompt_file_path": "m.md", "allowed_targets": ["MASTER", "USER"],
    "tools": ["write_file", "knowledge_status", "update_knowledge"]}}}


@pytest.fixture
def run(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_functions, "get_root_directory", MagicMock(return_value=str(tmp_path)))
    import ai.tools.base as base
    monkeypatch.setattr(base, "PROJECT_ROOT", str(tmp_path / "project"))

    def _run(service, responses):
        store = KnowledgeStore()
        store.service = service
        modules = MagicMock()
        modules.items.return_value = [("knowledge", Module(store))]
        conn, reg = Connector(responses), Registry()
        orch = AgentOrchestrator(conn, reg, PIPELINE, modules, io=QuietIO())
        orch._gatekeeper = lambda *a, **k: True
        result = orch.run_loop("change main", session_id=f"s-{uuid.uuid4().hex}")
        return result, conn, reg

    return _run


WRITE = {"action": {"tool_name": "write_file", "tool_parameters": {"path": "@ROOT/src/app/main.py", "content": "x"},
                    "agent_target": "SELF"}}
DONE = {"action": {"tool_name": "null", "agent_target": "USER"}, "response_to_user": "Changed main.py"}


def test_changed_files_are_regenerated_at_turn_end(run, tmp_path):
    service = FakeService()
    result, conn, reg = run(service, [WRITE, DONE])
    assert result.reason == "awaiting_user"
    assert service.calls == [{"project": str(tmp_path / "project"), "llm": conn.llm,
                              "files": ["@ROOT/src/app/main.py"], "max_files": 5}]
    # build tools are offered even when no knowledge is loaded yet; query tools are not
    assert {"knowledge_status", "update_knowledge"} <= set(reg.tools) and "search_knowledge" not in reg.tools


def test_no_update_without_app_built_knowledge(run):
    service = FakeService(built=False)
    run(service, [WRITE, DONE])
    assert service.calls == []


def test_no_update_without_changes(run):
    service = FakeService()
    run(service, [DONE])
    assert service.calls == []


def test_auto_update_can_be_disabled(run, monkeypatch):
    from ai.config import ProgramConfig, ProgramSetting
    config = ProgramConfig.get_current()
    monkeypatch.setitem(config.config, str(ProgramSetting.KNOWLEDGE_AUTO_UPDATE), False)
    service = FakeService()
    run(service, [WRITE, DONE])
    assert service.calls == []
