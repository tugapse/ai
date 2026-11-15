import json
import os

import pytest

from ai.modules.knowledge.docs_loader import chunk_text, parse_markdown
from ai.modules.knowledge.schema import path_key
from ai.modules.knowledge.sources import SourceSpec
from ai.modules.knowledge.store import KnowledgeStore, tokenize


def component(path, summary, nodes=(), edges=(), env=(), deps=()):
    return {
        "component": {"name": os.path.basename(path).split(".")[0], "source_path": f"/{path}",
                      "doc_path": f"/{path.rsplit('.', 1)[0]}.json", "type": "service"},
        "vector_memory": {"semantic_summary": summary},
        "graph_nodes": [{"id": f"/{path}#{n}", "label": l, "name": n, "signature": s} for n, l, s in nodes],
        "graph_edges": [{"source": f"/{path}", "target": f"/{t}", "relation": r} for t, r in edges],
        "metadata": {"environment_variables": list(env), "external_dependencies": list(deps), "has_side_effects": False},
    }


MEMORY_DOC = """## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| MemoryManager | ai/agents/memory_manager |

Central state service for agents. See [Sentinel](/ai/agents/context_sentinel.md).

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| check_stagnation | Method | Tracks tool call fingerprints to detect repetitive looping behaviour. |

## 3. Implementation Details & Side Effects
The stagnation check keeps a sliding window of fingerprints.

```python
## not a heading inside a code fence
```
"""

ORPHAN_DOC = """# Deployment guide

## Docker
Build the image with the bundled Dockerfile and expose port 8000.
"""

OVERVIEW_ONLY_DOC = """## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Sentinel** | [src/ai/agents/context_sentinel.py](/src/ai/agents/context_sentinel.py) |

Measures context pressure and prunes history when the window fills up.
"""


@pytest.fixture
def kb_dirs(tmp_path):
    kn = tmp_path / "kn" / "ai" / "agents"
    kn.mkdir(parents=True)
    (kn / "memory_manager.json").write_text(json.dumps(component(
        "ai/agents/memory_manager.py",
        "Central state service. Implements loop detection via tool call fingerprint tracking.",
        nodes=[("MemoryManager", "Class", ""), ("MemoryManager.check_stagnation", "Method", "check_stagnation(tool_name) -> bool")],
    )))
    (kn / "context_sentinel.json").write_text(json.dumps(component(
        "ai/agents/context_sentinel.py",
        "Monitors context pressure and distills heavy tool outputs into long term memory.",
        nodes=[("ContextSentinel", "Class", "")],
        edges=[("ai/agents/memory_manager.py", "depends_on")],
    )))
    (kn / "agent_orchestrator.json").write_text(json.dumps(component(
        "ai/agents/agent_orchestrator.py",
        "Routes messages between agents and executes tools.",
        nodes=[("AgentOrchestrator", "Class", "")],
        edges=[("ai/agents/memory_manager.py", "imports"), ("ai/agents/context_sentinel.py", "imports")],
        env=["JARVIS_HOME"],
    )))
    (kn / "broken.json").write_text(json.dumps({"component": {"name": "no path"}}))
    (kn / "other.json").write_text(json.dumps({"not": "a component"}))
    (kn / "notes.txt").write_text("ignored")

    docs = tmp_path / "docs" / "ai" / "agents"
    docs.mkdir(parents=True)
    (docs / "memory_manager.md").write_text(MEMORY_DOC)
    (docs / "sentinel_notes.md").write_text(OVERVIEW_ONLY_DOC)
    (tmp_path / "docs" / "deploy.md").write_text(ORPHAN_DOC)
    (tmp_path / "docs" / ".ai-engine-resume").write_text("state")
    return tmp_path


@pytest.fixture
def store(kb_dirs):
    s = KnowledgeStore()
    s.add_source(SourceSpec(id="code", path=str(kb_dirs / "kn")))
    s.add_source(SourceSpec(id="docs", path=str(kb_dirs / "docs"), kind="docs"))
    return s


class TestHelpers:
    def test_path_key(self):
        assert path_key("/ai/agents/memory_manager.py") == "ai/agents/memory_manager"
        assert path_key("ai\\agents\\memory_manager.md") == "ai/agents/memory_manager"
        assert path_key("@ROOT/src/x.py#Cls") == "src/x"
        assert path_key("./a//b.json") == "a/b"

    def test_chunk_text(self):
        text = " ".join(f"word{i}" for i in range(1, 11))
        assert chunk_text(text, chunk_size=4, overlap=2) == [
            "word1 word2 word3 word4", "word3 word4 word5 word6",
            "word5 word6 word7 word8", "word7 word8 word9 word10"]
        assert chunk_text("", 4, 2) == []
        assert chunk_text("word1 word2", 4, 2) == ["word1 word2"]

    def test_tokenize_splits_identifiers(self):
        toks = tokenize("check_stagnation ContextSentinel")
        assert {"check", "stagnation", "context", "sentinel", "checkstagnation"} <= set(toks)

    def test_parse_markdown(self):
        doc = parse_markdown(MEMORY_DOC, doc_key="ai/agents/memory_manager")
        assert doc.headings == ["1. Overview & Purpose", "2. Public API & Interfaces", "3. Implementation Details & Side Effects"]
        assert doc.links == ["ai/agents/context_sentinel"]
        assert doc.source_file_key == "ai/agents/memory_manager"
        assert "not a heading inside a code fence" in doc.chunks[-1].text

    def test_overview_link_cell(self):
        doc = parse_markdown(OVERVIEW_ONLY_DOC, doc_key="ai/agents/sentinel_notes")
        assert doc.source_file_key == "src/ai/agents/context_sentinel"


class TestLoading:
    def test_sources_and_invalid_files(self, store):
        sources = {s["id"]: s for s in store.list_sources()}
        assert sources["code"]["components"] == 3
        assert sources["code"]["errors"] == 1          # broken.json; other.json is just not a component
        assert sources["docs"]["docs"] == 3
        assert sources["docs"]["components"] == 0

    def test_missing_source(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            KnowledgeStore().add_source(SourceSpec(id="x", path=str(tmp_path / "nope")))

    def test_kind_filters_files(self, kb_dirs):
        s = KnowledgeStore()
        s.add_source(SourceSpec(id="docs-only", path=str(kb_dirs), kind="docs"))
        assert s.list_sources()[0]["components"] == 0
        s.add_source(SourceSpec(id="all", path=str(kb_dirs), kind="auto"))
        assert {x["id"]: x["components"] for x in s.list_sources()}["all"] == 3

    def test_reload_and_remove(self, store, kb_dirs):
        f = kb_dirs / "kn" / "ai" / "agents" / "agent_orchestrator.json"
        f.unlink()
        store.add_source(SourceSpec(id="code", path=str(kb_dirs / "kn")), reload=True)
        assert store.get_component("ai/agents/agent_orchestrator.py") is None
        assert store.remove_source("docs")
        assert store.read_doc("memory_manager") is None
        assert not store.remove_source("docs")

    def test_ingest_documents(self):
        s = KnowledgeStore()
        res = s.ingest_documents("fed", [
            component("app/main.py", "Entry point that boots the web server."),
            {"path": "app/main.md", "content": "## Usage\nRun main to start the web server on port 8080."},
            {"bogus": True},
        ])
        assert res == {"id": "fed", "components": 1, "docs": 1, "errors": 1}
        card = s.get_component("app/main.py")
        assert card["doc"]["sections"] == ["Usage"]
        # merging into the same source keeps earlier documents
        s.ingest_documents("fed", [component("app/util.py", "Helpers.")])
        assert s.get_component("app/main.py") and s.get_component("app/util.py")


class TestQueries:
    def test_docs_link_to_components(self, store):
        card = store.get_component("src/ai/agents/memory_manager.py")
        assert card["doc"]["path"] == "ai/agents/memory_manager.md"
        assert card["used_by"] == ["ai/agents/agent_orchestrator.py", "ai/agents/context_sentinel.py"]
        # doc linked through its Overview table, not its file name
        sentinel = store.get_component("context_sentinel")
        assert sentinel["doc"]["path"] == "ai/agents/sentinel_notes.md"
        # Markdown links become 'references' edges
        refs = store.neighbors("ai/agents/memory_manager.py", relation="references")
        assert {"relation": "references", "path": "ai/agents/context_sentinel.py"} in refs["uses"]

    def test_component_card(self, store):
        card = store.get_component("@ROOT/src/ai/agents/agent_orchestrator.py")
        assert card["path"] == "ai/agents/agent_orchestrator.py"
        assert card["uses"] == ["ai/agents/context_sentinel.py", "ai/agents/memory_manager.py"]
        assert card["environment_variables"] == ["JARVIS_HOME"]
        assert card["stale"] is False

    def test_neighbors_directions(self, store):
        out = store.neighbors("memory_manager", direction="out")
        assert "used_by" not in out
        inc = store.neighbors("memory_manager", direction="in")
        assert {n["path"] for n in inc["used_by"]} == {"ai/agents/agent_orchestrator.py", "ai/agents/context_sentinel.py"}

    def test_find_symbol(self, store):
        hits = store.find_symbol("check_stagnation")
        assert hits[0]["path"] == "ai/agents/memory_manager.py"
        assert hits[0]["signature"] == "check_stagnation(tool_name) -> bool"
        assert store.find_symbol("contextsent")[0]["symbol"] == "ContextSentinel"
        assert store.find_symbol("nothing_like_this") == []

    def test_read_doc(self, store):
        index = store.read_doc("memory_manager")
        assert index["sections"][0] == "1. Overview & Purpose"
        section = store.read_doc("memory_manager", section="implementation")
        assert "sliding window" in section["text"]
        assert "error" in store.read_doc("memory_manager", section="nope")
        orphan = store.read_doc("deploy")
        assert orphan["title"] == "Deployment guide"

    def test_search_groups_by_component(self, store):
        hits = store.search("where are tool call loops detected", top_k=3)
        assert hits[0]["path"] == "ai/agents/memory_manager.py"
        assert hits[0]["kind"] == "component"
        assert hits[0]["score"] == 1.0
        assert len({h["path"] for h in hits}) == len(hits)

    def test_search_doc_only_results(self, store):
        hits = store.search("docker image port", top_k=2)
        assert hits[0]["kind"] == "doc"
        assert hits[0]["path"] == "deploy.md"
        assert hits[0]["sections"][0]["heading"] == "Docker"

    def test_search_respects_allowed_sources(self, store):
        assert store.search("docker image", sources=["code"]) == []
        assert store.find_symbol("ContextSentinel", sources=["docs"]) == []
        assert store.get_component("memory_manager", sources=["docs"])["kind"] == "doc"

    def test_mark_stale(self, store):
        assert store.mark_stale("/abs/project/src/ai/agents/context_sentinel.py")
        assert store.get_component("context_sentinel")["stale"] is True
        assert not store.mark_stale("unknown/file.py")
        hit = next(h for h in store.search("context pressure") if h["path"] == "ai/agents/context_sentinel.py")
        assert hit["stale"] is True


class TestTools:
    def test_tools_scope_and_results(self, store, tmp_path, monkeypatch):
        import ai.tools.base as base
        monkeypatch.setattr(base, "PROJECT_ROOT", str(tmp_path / "empty-project"))
        tools = store.tools.get_tools()
        res = tools["search_knowledge"](query="loop detection fingerprints")
        assert res["status"] == "SUCCESS" and res["results"][0]["path"] == "ai/agents/memory_manager.py"
        assert tools["get_component"](path="nope.py")["status"] == "FAILED"
        assert tools["find_symbol"](name="MemoryManager")["matches"][0]["symbol"] == "MemoryManager"
        assert tools["read_doc"](path="memory_manager", section="Public")["status"] == "SUCCESS"
        assert tools["knowledge_neighbors"](path="memory_manager", direction="in")["status"] == "SUCCESS"

        store.tools.set_scope(["docs"])
        assert tools["find_symbol"](name="MemoryManager")["matches"] == []
        store.tools.set_scope(None)

    def test_ingest_tool_stays_inside_project(self, store, kb_dirs, monkeypatch):
        import ai.tools.base as base
        monkeypatch.setattr(base, "PROJECT_ROOT", str(kb_dirs / "docs"))
        tools = store.tools.get_tools()
        tools = store.tools.get_build_tools()
        assert tools["ingest_knowledge"](path="/etc")["status"] == "FAILED"
        res = tools["ingest_knowledge"](path="@ROOT/ai", id="agents-docs")
        assert res["status"] == "SUCCESS" and res["docs"] == 2


class TestSemanticIndex:
    def test_vector_sync_is_incremental(self, kb_dirs, tmp_path, monkeypatch):
        """VectorIndex embeds only new/changed items and deletes vanished ones (fake DB + embedder)."""
        import ai.modules.knowledge.store as store_mod

        class FakeDB:
            def __init__(self):
                self.rows = {}
            def get(self):
                return {i: m for i, (v, m) in self.rows.items()}
            def delete(self, ids):
                for i in ids:
                    self.rows.pop(i, None)
            def upsert_many(self, ids, vectors, metadatas):
                for i, v, m in zip(ids, vectors, metadatas):
                    self.rows[i] = (v, m)
            def query(self, vector, top_k):
                return [{"id": i, "score": 0.9} for i in list(self.rows)[:top_k]]

        class FakeEmbedder:
            calls = 0
            def embed(self, text):
                return [1.0]
            def embed_many(self, texts):
                FakeEmbedder.calls += len(texts)
                return [[1.0] for _ in texts]

        db = FakeDB()

        def fake_init(self, db_path, spec):
            self.db, self.embedder = db, FakeEmbedder()

        monkeypatch.setattr(store_mod.VectorIndex, "__init__", fake_init)
        s = KnowledgeStore(db_path=str(tmp_path / "db"), use_vectors=True, background=False)
        s.add_source(SourceSpec(id="code", path=str(kb_dirs / "kn")))
        assert FakeEmbedder.calls == 3 and s.list_sources()[0]["semantic"] is True

        s.add_source(SourceSpec(id="code", path=str(kb_dirs / "kn")), reload=True)
        assert FakeEmbedder.calls == 3  # unchanged: nothing re-embedded

        (kb_dirs / "kn" / "ai" / "agents" / "agent_orchestrator.json").unlink()
        s.add_source(SourceSpec(id="code", path=str(kb_dirs / "kn")), reload=True)
        assert len(db.rows) == 2
        assert s.search("anything at all")  # vector hits are used even without keyword overlap


class TestProjectPaths:
    def test_paths_point_at_project_files(self, store, tmp_path, monkeypatch):
        """Knowledge paths are relative to src/; tools answer with the real @ROOT path."""
        import ai.tools.base as base
        from ai.modules.knowledge.project_paths import display_path, project_path
        project = tmp_path / "project"
        (project / "src" / "ai" / "agents").mkdir(parents=True)
        (project / "src" / "ai" / "agents" / "memory_manager.py").write_text("")
        (project / "src" / "ai" / "agents" / "context_sentinel.py").write_text("")
        (project / "README.md").write_text("")
        monkeypatch.setattr(base, "PROJECT_ROOT", str(project))

        assert project_path("ai/agents/memory_manager.py") == "@ROOT/src/ai/agents/memory_manager.py"
        assert project_path("README.md") == "@ROOT/README.md"
        assert project_path("ai/agents/missing.py") is None
        assert display_path("ai/agents/missing.py") == "ai/agents/missing.py"

        tools = store.tools.get_tools()
        assert tools["search_knowledge"](query="loop detection fingerprints")["results"][0]["path"] == \
            "@ROOT/src/ai/agents/memory_manager.py"
        card = tools["get_component"](path="@ROOT/src/ai/agents/memory_manager.py")
        assert card["path"] == "@ROOT/src/ai/agents/memory_manager.py"
        assert "@ROOT/src/ai/agents/context_sentinel.py" in card["used_by"]
        assert tools["find_symbol"](name="ContextSentinel")["matches"][0]["path"] == "@ROOT/src/ai/agents/context_sentinel.py"
        neighbors = tools["knowledge_neighbors"](path="memory_manager", direction="in")
        assert {"relation": "depends_on", "path": "@ROOT/src/ai/agents/context_sentinel.py"} in neighbors["used_by"]
