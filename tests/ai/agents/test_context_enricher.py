import json
import sys
import uuid
from unittest.mock import MagicMock

import pytest

import ai.functions as ai_functions

sys.modules.setdefault("ai.core.terminal_ui", MagicMock())
# Same fuse as test_message_orchestrator: importing the orchestrator must not load ai.program.
sys.modules.setdefault("ai.program", MagicMock())

from ai.agents.context_enricher import ContextEnricher, touched_files
from ai.agents.agent_orchestrator import AgentOrchestrator
from ai.modules.knowledge.sources import SourceSpec
from ai.modules.knowledge.store import KnowledgeStore


def component(path, summary, edges=()):
    return {
        "component": {"name": path.rsplit("/", 1)[-1], "source_path": f"/{path}", "type": "module"},
        "vector_memory": {"semantic_summary": summary},
        "graph_nodes": [],
        "graph_edges": [{"source": f"/{path}", "target": f"/{t}", "relation": "imports"} for t in edges],
    }


@pytest.fixture
def store():
    s = KnowledgeStore()
    s.ingest_documents("code", [
        component("app/billing.py", "Computes invoices and applies tax rules. Second sentence.", edges=["app/db.py"]),
        component("app/db.py", "Database connection pool."),
        component("app/api.py", "HTTP routes for invoices.", edges=["app/billing.py"]),
    ])
    s.ingest_documents("ops", [{"path": "runbook.md", "content": "## Restart\nRestart the invoice workers with systemctl."}])
    return s


class FakeLTM:
    def __init__(self, hits=()):
        self.hits = list(hits)
        self.added = []
        self.new_memories = 0
        self.reflections = 0
        self.tools = MagicMock()
        self.tools.get_tools.return_value = {}

    def search(self, query, top_k=5, types=None, min_relevance=0.0):
        return [h for h in self.hits if h.get("relevance", 1) >= min_relevance][:top_k]

    def add_memory(self, content, source, memory_type="observation", metadata=None):
        self.added.append((content, source, memory_type))
        self.new_memories += 1

    def trigger_reflection(self):
        self.reflections += 1
        self.new_memories = 0


def test_touched_files_newest_first():
    results = [
        {"tool": "read_file", "parameters": {"path": "a.py"}, "result": {"status": "SUCCESS"}},
        {"tool": "smart_search", "parameters": {"pattern": "x"}, "result": {"status": "SUCCESS"}},
        {"tool": "read_files", "parameters": {"paths": ["b.py", "a.py"]}, "result": {"status": "SUCCESS"}},
        {"tool": "patch_file", "parameters": {"path": "c.py"}, "result": {"status": "FAILED"}},
    ]
    assert touched_files(results) == ["b.py", "a.py"]


def test_enrich_adds_budgeted_blocks(store):
    ltm = FakeLTM([
        {"content": "Old chat line", "type": "chat_turn", "score": 2.5, "relevance": 0.9},
        {"content": "Tax is always computed per line item", "type": "decision", "score": 1.0, "relevance": 0.8},
        {"content": "irrelevant", "type": "fact", "score": 3.0, "relevance": 0.1},
    ])
    enricher = ContextEnricher(knowledge=store, ltm=ltm, knowledge_top_k=2, max_chars=1000, ltm_top_k=2)
    tool_results = [{"tool": "read_file", "parameters": {"path": "src/app/billing.py"}, "result": {"status": "SUCCESS"}}]
    payload = enricher.enrich({}, "MASTER", "fix the invoice tax rules", tool_results)

    assert payload["relevant_components"][0] == "app/billing.py - Computes invoices and applies tax rules."
    assert len(payload["relevant_components"]) <= 2
    assert payload["related_to_touched_files"] == ["app/billing.py: uses [app/db.py]; used by [app/api.py]"]
    # decisions first, low-relevance memories dropped
    assert payload["long_term_memory"] == ["[decision] Tax is always computed per line item", "[chat_turn] Old chat line"]


def test_enrich_respects_sources_and_budget(store):
    enricher = ContextEnricher(knowledge=store, ltm=None, knowledge_top_k=5, max_chars=200)
    payload = enricher.enrich({}, "OPS", "restart invoice workers", allowed_sources=["ops"])
    assert payload["relevant_components"] == ["runbook.md - Restart the invoice workers with systemctl. [doc: Restart]"]
    assert sum(len(x) for x in enricher.enrich({}, "M", "invoices tax database routes")["relevant_components"]) <= 200


def test_enrich_noop_without_sources():
    enricher = ContextEnricher(knowledge=KnowledgeStore(), ltm=None)
    assert enricher.enrich({"a": 1}, "M", "task") == {"a": 1}


# --------------------------------------------------------------------------- orchestrator wiring

class Connector:
    def __init__(self, responses):
        self.responses = list(responses)
        self.payloads = []
        self.llm = MagicMock()

    def send_request(self, payload, prompt_file_path, agent_config):
        self.payloads.append(json.loads(json.dumps(payload, default=str)))
        self.agent_configs = getattr(self, "agent_configs", []) + [agent_config]
        return self.responses.pop(0) if self.responses else {"action": {"agent_target": "STOP"}}

    def get_context_limit(self):
        return 100000

    def get_max_tokens(self):
        return 1000


class Registry:
    def __init__(self):
        self.tools = {"patch_file": lambda **kw: {"status": "SUCCESS"}}

    def register_tool(self, name, fn):
        self.tools[name] = fn

    def get_tool_info(self, name):
        return f"- {name}"

    def execute_tool(self, name, params):
        return self.tools[name](**params)

    def get_all_tools(self):
        return self.tools


class FakeKnowledgeModule:
    def __init__(self, store):
        self.store = store
        self.added = []

    def add_sources(self, entries, base_dir=None, **kwargs):
        self.added.append(list(entries))

    def get_instance(self):
        return self.store


class FakeLTMModule:
    def __init__(self, ltm):
        self.ltm = ltm
        self.init_args = None

    def initialize(self, session_id, llm, scope_key=None):
        self.init_args = (session_id, scope_key)

    def get_instance(self):
        return self.ltm


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_functions, "get_root_directory", MagicMock(return_value=str(tmp_path / "root")))
    import ai.tools.base as base
    monkeypatch.setattr(base, "PROJECT_ROOT", str(tmp_path / "project"))
    return tmp_path


def test_orchestrator_uses_knowledge_and_records_episode(store, workspace):
    ltm = FakeLTM([{"content": "Use Decimal for money", "type": "decision", "score": 1, "relevance": 0.9}])
    kb_mod, ltm_mod = FakeKnowledgeModule(store), FakeLTMModule(ltm)
    modules = MagicMock()
    modules.items.return_value = [("knowledge", kb_mod), ("vector_memory", ltm_mod)]

    pipeline = {
        "entry_point": "MASTER", "max_iterations": 5, "knowledge": ["extra_kb"],
        "agents": {"MASTER": {"role": "management", "prompt_file_path": "m.md", "allowed_targets": ["STOP", "USER"],
                              "tools": ["patch_file", "search_knowledge", "get_component"]}},
    }
    connector = Connector([
        {"action": {"tool_name": "patch_file", "tool_parameters": {"path": "@ROOT/src/app/billing.py"}}},
        {"action": {"agent_target": "STOP"}, "response_to_user": "Fixed the tax rounding."},
    ])
    registry = Registry()
    orch = AgentOrchestrator(connector, registry, pipeline, modules)
    orch._gatekeeper = lambda *a, **k: True

    orch.run_loop("fix invoice tax rounding", session_id=f"s-{uuid.uuid4().hex}")

    # pipeline sources handed to the module; LTM opened for the workspace scope
    assert kb_mod.added == [["extra_kb"]]
    assert ltm_mod.init_args[1] == f"project:{workspace / 'project'}"
    # knowledge tools registered and described to the agent
    assert "search_knowledge" in registry.tools
    assert "- search_knowledge" in connector.agent_configs[0]["tool_descriptions"]
    # first payload carries knowledge + memory
    first = connector.payloads[0]
    assert first["relevant_components"][0].startswith("app/billing.py")
    assert first["long_term_memory"] == ["[decision] Use Decimal for money"]
    # the patched file is flagged as changed this session
    assert store.get_component("app/billing.py")["stale"] is True
    assert "(changed this session)" in connector.payloads[1]["relevant_components"][0]
    # the turn is remembered as an episode
    content, source, kind = ltm.added[-1]
    assert kind == "episode"
    assert "Task: fix invoice tax rounding" in content
    assert "Fixed the tax rounding." in content
    assert "Files changed: @ROOT/src/app/billing.py" in content


def test_orchestrator_without_sources_registers_no_knowledge_tools(workspace):
    modules = MagicMock()
    modules.items.return_value = [("knowledge", FakeKnowledgeModule(KnowledgeStore()))]
    pipeline = {"entry_point": "MASTER", "max_iterations": 2,
                "agents": {"MASTER": {"role": "management", "prompt_file_path": "m.md", "allowed_targets": ["STOP"], "tools": []}}}
    connector = Connector([{"action": {"agent_target": "STOP"}}])
    registry = Registry()
    orch = AgentOrchestrator(connector, registry, pipeline, modules)
    orch.run_loop("hello", session_id=f"s-{uuid.uuid4().hex}")
    assert "search_knowledge" not in registry.tools
    assert "relevant_components" not in connector.payloads[0]
