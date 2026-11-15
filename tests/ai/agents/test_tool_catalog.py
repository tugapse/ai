"""Agents see tool categories until they open them with open_tools."""

import sys
import uuid
from unittest.mock import MagicMock

import pytest

import ai.functions as ai_functions

sys.modules.setdefault("ai.core.terminal_ui", MagicMock())
sys.modules.setdefault("ai.program", MagicMock())

from ai.agents.agent_io import AgentIO
from ai.agents.agent_orchestrator import AgentOrchestrator
from ai.agents.tool_catalog import OPEN_TOOLS, ToolCatalog, requested_categories
from ai.tools import ToolCategory, tool
from ai.tools.tool_registry import ToolRegistry


@tool
def read_file(path: str) -> dict:
    """
    READ_FILE_DOC reads a file.

    Args:
        path (string): File path.
    """
    return {"status": "SUCCESS", "files": {path: "x"}}


@tool
def web_search(query: str) -> dict:
    """
    WEB_SEARCH_DOC searches the web.

    Args:
        query (string): Query.
    """
    return {"status": "SUCCESS", "results": []}


@tool
def remember(fact: str) -> dict:
    """
    REMEMBER_DOC stores a fact.

    Args:
        fact (string): The fact.
    """
    return {"status": "SUCCESS"}


class Cat(ToolCategory):
    def __init__(self, name, description, tools):
        self.name, self.description, self._tools = name, description, list(tools)

    def get_category_tools(self):
        return self._tools


def fresh_registry():
    reg = object.__new__(ToolRegistry)
    reg._tools, reg._categories, reg._tool_category = {}, {}, {}
    reg.register_category(Cat("filesystem", "Read and write files.", [read_file]))
    reg.register_category(Cat("web", "Search the web.", [web_search]))
    reg.register_category(Cat("memory", "Remember facts.", [remember]))
    return reg


class QuietIO(AgentIO):
    blocking_user_input = False

    def emit(self, event):
        pass

    def request_permission(self, tool, params):
        return "yes"


class Connector:
    def __init__(self, responses):
        self.responses = list(responses)
        self.configs = []
        self.llm = MagicMock()

    def send_request(self, payload, prompt_file_path, agent_config):
        self.configs.append(agent_config)
        return self.responses.pop(0) if self.responses else {"action": {"agent_target": "STOP"}}

    def get_context_limit(self):
        return 100000

    def get_max_tokens(self):
        return 1000


PIPELINE = {
    "entry_point": "MASTER", "max_iterations": 10,
    "agents": {"MASTER": {"role": "management", "prompt_file_path": "m.md",
                          "allowed_targets": ["MASTER", "USER"], "tools": ["read_file", "web_search"]}},
}


def call(name, **params):
    return {"action": {"tool_name": name, "tool_parameters": params, "agent_target": "SELF"}}


def done():
    return {"action": {"tool_name": "null", "agent_target": "USER"}, "response_to_user": "done"}


@pytest.fixture
def run(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_functions, "get_root_directory", MagicMock(return_value=str(tmp_path)))

    def _run(responses, categories=True):
        settings = {"AGENT_TOOL_CATEGORIES": categories}
        monkeypatch.setattr(AgentOrchestrator, "_setting",
                            staticmethod(lambda config, key, default: settings.get(getattr(key, "value", key), default)))
        conn, reg = Connector(responses), fresh_registry()
        orch = AgentOrchestrator(conn, reg, PIPELINE, MagicMock(), io=QuietIO())
        orch._gatekeeper = lambda *a, **k: True
        orch.run_loop("question", session_id=f"s-{uuid.uuid4().hex}")
        return conn, orch

    return _run


def test_prompt_lists_only_allowed_categories_until_opened(run):
    conn, orch = run([call(OPEN_TOOLS, category=["filesystem", "web"]), done()])
    first, second = (c["tool_descriptions"] for c in conn.configs)
    assert "- filesystem: Read and write files." in first and "- web: Search the web." in first
    assert "memory" not in first                       # not allowed for this agent
    assert "READ_FILE_DOC" not in first and "WEB_SEARCH_DOC" not in first
    assert OPEN_TOOLS in conn.configs[0]["tools"]
    assert "READ_FILE_DOC" in second and "WEB_SEARCH_DOC" in second
    # every agent also has the MCP admin category (list/enable MCP servers): still closed here
    assert "- mcp_servers:" in second
    result = orch.memory.context.tool_results[-1]["result"]
    assert result["opened"] == {"filesystem": ["read_file"], "web": ["web_search"]}


def test_unknown_category_fails_with_the_list(run):
    _, orch = run([call(OPEN_TOOLS, category="memory"), done()])
    result = orch.memory.context.tool_results[-1]["result"]
    assert result["status"] == "FAILED" and sorted(result["available_categories"]) == ["filesystem", "mcp_servers", "web"]


def test_calling_a_closed_category_tool_runs_it_and_opens_the_category(run):
    conn, orch = run([call("read_file", path="a.py"), done()])
    assert orch.memory.context.tool_results[-1]["result"]["status"] == "SUCCESS"
    assert "READ_FILE_DOC" in conn.configs[1]["tool_descriptions"]
    assert "WEB_SEARCH_DOC" not in conn.configs[1]["tool_descriptions"]


def test_category_name_called_as_a_tool_opens_it(run):
    conn, orch = run([call("web"), done()])
    assert orch.memory.context.tool_results[-1]["result"]["opened"] == {"web": ["web_search"]}
    assert "WEB_SEARCH_DOC" in conn.configs[1]["tool_descriptions"]


def test_disabled_setting_lists_every_tool(run):
    conn, _ = run([done()], categories=False)
    text = conn.configs[0]["tool_descriptions"]
    assert "READ_FILE_DOC" in text and "WEB_SEARCH_DOC" in text and OPEN_TOOLS not in conn.configs[0]["tools"]


def test_open_categories_survive_session_state():
    from ai.agents.memory_manager import MemoryManager
    mem = MemoryManager(["MASTER"])
    mem.agents["MASTER"].open_categories.append("web")
    restored = MemoryManager(["MASTER"])
    restored.load_state(mem.serialize())
    assert restored.agents["MASTER"].open_categories == ["web"]


def test_requested_categories_accepts_lists_and_commas():
    assert requested_categories({"category": "Filesystem, web"}) == ["filesystem", "web"]
    assert requested_categories({"category": ["web", "web"]}) == ["web"]
    assert requested_categories({}) == []


def test_tools_outside_categories_are_always_shown():
    reg = fresh_registry()
    reg.register_tool("legacy", read_file)
    text = ToolCatalog(reg).describe(["legacy", "web_search"], [])
    assert "READ_FILE_DOC" in text and "WEB_SEARCH_DOC" not in text
