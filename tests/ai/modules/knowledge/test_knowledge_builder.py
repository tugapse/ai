import json
import os
import time
from types import SimpleNamespace

import pytest

import ai.modules.knowledge.builder as builder_mod
from ai.modules.knowledge.builder import (
    KnowledgeBuilder, KnowledgeService, clean_output, resolve_build_config, validate_output,
)
from ai.modules.knowledge.knowledge_module import KnowledgeModule
from ai.modules.knowledge.registry import KnowledgeRegistry, project_slug
from ai.modules.knowledge.sources import SourceSpec
from ai.modules.knowledge.store import KnowledgeStore

MAIN = "from app import util\nfrom app.util import helper\n\ndef main():\n    return helper()\n"
UTIL = "def helper():\n    return 42\n"


class FakeLLM:
    """Answers like the model: Markdown for docs, component JSON for knowledge."""

    def __init__(self, bad_json_times=0):
        self.calls = []
        self.bad_json_times = bad_json_times

    def __call__(self, messages, system_prompt):
        self.calls.append(messages)
        context = messages[3]["content"]
        source = context.split("CURRENT SOURCE: ", 1)[1].split(" |", 1)[0]
        if "CURRENT TARGET:" in context and ".json" in context.split("\n", 1)[0]:
            if self.bad_json_times > 0:
                self.bad_json_times -= 1
                return "Sure! Here is the JSON: {not valid"
            return "```json\n" + json.dumps({
                "component": {"name": os.path.basename(source).split(".")[0], "source_path": f"/{source}",
                              "type": "module"},
                "vector_memory": {"semantic_summary": f"Summary of {source}, which computes helper values."},
                "graph_nodes": [{"id": f"/{source}#helper", "label": "Function", "name": "helper", "signature": "helper()"}],
                "graph_edges": [],
            }) + "\n```"
        return f"## 1. Overview & Purpose\nThe file {source} " + "provides helper logic for the application " * 4


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    (root / "src" / "app").mkdir(parents=True)
    (root / "src" / "app" / "main.py").write_text(MAIN)
    (root / "src" / "app" / "util.py").write_text(UTIL)
    (root / "src" / "app" / "notes.txt").write_text("not source")
    (root / "src" / ".hidden").mkdir()
    (root / "src" / ".hidden" / "x.py").write_text("x = 1")
    return root


@pytest.fixture
def registry(tmp_path):
    return KnowledgeRegistry(str(tmp_path / "registry" / "projects.json"))


def make_config(project, tmp_path, **kw):
    kw.setdefault("extensions", ["py"])
    return resolve_build_config(str(project), None, None, output_dir=str(tmp_path / "out"), **kw)


class TestConfig:
    def test_defaults(self, project, registry, tmp_path):
        cfg = resolve_build_config(str(project), registry, {"KNOWLEDGE_OUTPUT_DIR": str(tmp_path / "kb")})
        assert cfg.source_root == str(project / "src")
        assert cfg.extensions == [] and cfg.all_files and cfg.extensions_label == "all text files"
        assert cfg.output_dir == str(tmp_path / "kb" / project_slug(str(project)))
        assert cfg.target_rel("knowledge", "app/main.py") == "app/main.json"

    def test_registry_values_win_over_defaults(self, project, registry, tmp_path):
        registry.set_build_config(str(project), source_root=".", extensions=["ts", "js"], output=str(tmp_path / "o"))
        cfg = resolve_build_config(str(project), registry, None)
        assert cfg.source_root == str(project) and cfg.extensions == ["ts", "js"] and cfg.output_dir == str(tmp_path / "o")
        assert resolve_build_config(str(project), registry, None, extensions=[".py, md"]).extensions == ["py", "md"]


class TestAllFiles:
    """No --ext: every text file, without binaries, lockfiles, big or git-ignored files."""

    @pytest.fixture
    def mixed(self, tmp_path):
        import subprocess
        root = tmp_path / "mixed"
        (root / "web").mkdir(parents=True)
        (root / "web" / "card.component.ts").write_text("export class Card {}\n")
        (root / "web" / "card.component.html").write_text("<div>card</div>\n")
        (root / "web" / "app.min.js").write_text("var a=1;")
        (root / "Dockerfile").write_text("FROM python:3.12\n")
        (root / "README.md").write_text("# Mixed\n")
        (root / "package-lock.json").write_text("{}")
        (root / "logo.png").write_bytes(b"\x89PNG\r\n")
        (root / "blob.dat").write_bytes(b"abc\0def")
        (root / "big.txt").write_text("x" * (builder_mod.MAX_FILE_BYTES + 1))
        (root / "gen").mkdir()
        (root / "gen" / "out.py").write_text("x = 1\n")
        (root / "secret.env").write_text("A=1\n")
        (root / ".gitignore").write_text("gen/\n*.env\n")
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        return root

    def test_scan_skips_what_should_not_be_documented(self, mixed, tmp_path):
        b = KnowledgeBuilder(resolve_build_config(str(mixed), None, None, output_dir=str(tmp_path / "out")))
        assert b.scan() == ["Dockerfile", "README.md", "web/card.component.html", "web/card.component.ts"]
        assert b.to_rel("logo.png") is None and b.to_rel("README.md") == "README.md"

    def test_same_name_without_extension_keeps_full_name(self, mixed, tmp_path):
        b = KnowledgeBuilder(resolve_build_config(str(mixed), None, None, output_dir=str(tmp_path / "out")))
        b.scan()
        assert b.config.target_rel("docs", "web/card.component.ts") == "web/card.component.ts.md"
        assert b.config.target_rel("docs", "web/card.component.html") == "web/card.component.html.md"
        assert b.config.target_rel("docs", "README.md") == "README.md"

    def test_output_inside_the_project_is_not_scanned(self, mixed):
        (mixed / "kb" / "docs").mkdir(parents=True)
        (mixed / "kb" / "docs" / "README.md").write_text("# doc\n")
        b = KnowledgeBuilder(resolve_build_config(str(mixed), None, None, output_dir=str(mixed / "kb")))
        assert not [f for f in b.scan() if f.startswith("kb/")]

    @pytest.mark.parametrize("value", ["all", "*", ["ALL"], ".py, all"])
    def test_ext_all_resets_saved_extensions(self, project, registry, value):
        registry.set_build_config(str(project), extensions=["py"])
        assert resolve_build_config(str(project), registry, None).extensions == ["py"]
        assert resolve_build_config(str(project), registry, None, extensions=[value] if isinstance(value, str) else value).extensions == []

    def test_saved_all_wins_over_config(self, project, registry):
        registry.set_build_config(str(project), extensions=[])
        assert resolve_build_config(str(project), registry, {"KNOWLEDGE_EXTENSIONS": ["py"]}).extensions == []
        assert resolve_build_config(str(project), None, {"KNOWLEDGE_EXTENSIONS": ["py"]}).extensions == ["py"]
        assert resolve_build_config(str(project), None, {"KNOWLEDGE_EXTENSIONS": ["all"]}).extensions == []


class TestOutputChecks:
    def test_clean_output(self):
        assert clean_output("knowledge", '```json\n{"a": 1}\n```') == '{"a": 1}\n'
        assert clean_output("knowledge", 'Here you go: {"a": 1} hope it helps') == '{"a": 1}\n'
        assert clean_output("docs", "```markdown\n# Doc\ntext\n```") == "# Doc\ntext\n"

    def test_validate(self):
        assert validate_output("knowledge", "{bad") .startswith("invalid JSON")
        assert validate_output("knowledge", '{"x": 1}') == "JSON has no 'component' object"
        assert "schema" in validate_output("knowledge", '{"component": {"name": "x"}}')
        assert validate_output("docs", "too short") == "documentation too short"


class TestBuilder:
    def test_scan_and_to_rel(self, project, tmp_path):
        b = KnowledgeBuilder(make_config(project, tmp_path))
        assert b.scan() == ["app/main.py", "app/util.py"]
        assert b.to_rel("@ROOT/src/app/main.py") == "app/main.py"
        assert b.to_rel("src/app/util.py") == "app/util.py"
        assert b.to_rel("app/util.py") == "app/util.py"
        assert b.to_rel("src/app/notes.txt") is None
        assert b.to_rel("/etc/passwd") is None

    def test_full_build_mirrors_tree_with_doc_context_and_filtered_manifest(self, project, tmp_path):
        llm = FakeLLM()
        b = KnowledgeBuilder(make_config(project, tmp_path), llm_call=llm)
        report = b.run(mode="missing")
        assert report["done"] == ["app/main.py", "app/util.py"] and not report["failed"]
        out = tmp_path / "out"
        assert (out / "docs" / "app" / "main.md").read_text().startswith("## 1. Overview")
        data = json.loads((out / "knowledge" / "app" / "util.json").read_text())
        assert data["component"]["source_path"] == "/app/util.py"
        # docs first, then knowledge with the doc as context
        main_calls = [c for c in llm.calls if "CURRENT SOURCE: app/main.py" in c[3]["content"]]
        assert ".md" in main_calls[0][3]["content"].split("\n")[0]
        assert "END OF DOCUMENTATION CONTEXT" in main_calls[1][2]["content"]
        # manifest: main refers to util, util refers to nothing else
        assert "[app/util.py -> app/util.md]" in main_calls[0][3]["content"]
        util_call = next(c for c in llm.calls if "CURRENT SOURCE: app/util.py" in c[3]["content"])
        assert "app/main" not in util_call[3]["content"]
        assert b.status()["knowledge"]["ok"] == 2

    def test_changed_mode_uses_source_sha(self, project, tmp_path):
        llm = FakeLLM()
        b = KnowledgeBuilder(make_config(project, tmp_path), llm_call=llm)
        b.run()
        calls = len(llm.calls)
        assert KnowledgeBuilder(make_config(project, tmp_path), llm_call=llm).run()["done"] == []
        assert len(llm.calls) == calls
        (project / "src" / "app" / "util.py").write_text(UTIL + "\n# changed\n")
        b2 = KnowledgeBuilder(make_config(project, tmp_path), llm_call=llm)
        assert b2.status()["docs"]["outdated"] == 1
        assert b2.run()["done"] == ["app/util.py"]
        assert len(llm.calls) == calls + 2

    def test_invalid_output_is_retried_then_recorded(self, project, tmp_path):
        llm = FakeLLM(bad_json_times=4)  # both files fail twice (first try + retry)
        b = KnowledgeBuilder(make_config(project, tmp_path, kinds=["knowledge"]), llm_call=llm)
        report = b.run()
        assert [f["file"] for f in report["failed"]] == ["app/main.py", "app/util.py"]
        assert "invalid JSON" in report["failed"][0]["error"]
        assert "rejected" in llm.calls[1][-1]["content"]          # the retry tells the model why
        st = b.status()["knowledge"]
        assert st["error"] == 2 and st["error_files"] == ["app/main.py", "app/util.py"]
        # failed files are retried by the next run
        assert KnowledgeBuilder(make_config(project, tmp_path, kinds=["knowledge"]), llm_call=FakeLLM()).run()["done"] == \
            ["app/main.py", "app/util.py"]

    def test_retry_can_succeed(self, project, tmp_path):
        b = KnowledgeBuilder(make_config(project, tmp_path, kinds=["knowledge"]), llm_call=FakeLLM(bad_json_times=1))
        report = b.run(files=["src/app/util.py"])
        assert report["done"] == ["app/util.py"] and not report["failed"]

    def test_max_files_and_explicit_files(self, project, tmp_path):
        b = KnowledgeBuilder(make_config(project, tmp_path), llm_call=FakeLLM())
        report = b.run(max_files=1)
        assert report["done"] == ["app/main.py"] and report["remaining"] == 1
        # explicit files are regenerated even when up to date
        llm = FakeLLM()
        b2 = KnowledgeBuilder(make_config(project, tmp_path), llm_call=llm)
        assert b2.run(files=["@ROOT/src/app/main.py", "src/app/notes.txt"])["done"] == ["app/main.py"]
        assert len(llm.calls) == 2

    def test_too_large_for_context(self, project, tmp_path):
        llm = SimpleNamespace(token_info_count=SimpleNamespace(max_context_window=200, max_output_tokens=100))
        assert builder_mod._context_limit(llm) == 100
        # gguf before loading: token_info_count says 2048, the configured n_ctx wins
        loading = SimpleNamespace(_n_ctx=35000, token_info_count=SimpleNamespace(max_context_window=2048, max_output_tokens=12096))
        assert builder_mod._context_limit(loading) == 35000 - 12096
        b = KnowledgeBuilder(make_config(project, tmp_path), llm=llm, llm_call=FakeLLM())
        report = b.run(files=["src/app/util.py"])
        assert "too large" in report["failed"][0]["error"]

    def test_cancel(self, project, tmp_path):
        b = KnowledgeBuilder(make_config(project, tmp_path), llm_call=FakeLLM())
        b.cancel_event.set()
        report = b.run()
        assert report["done"] == [] and report["cancelled"] is True


class TestServiceAndRegistry:
    def test_registry_roundtrip(self, registry, project):
        registry.add_sources(str(project), [SourceSpec("a", "/x/a", "docs"), SourceSpec("b", "/x/b")])
        registry.add_sources(str(project), [SourceSpec("a", "/x/a2", "docs")])     # same id: replaced
        assert [(s.id, s.path) for s in registry.sources(str(project))] == [("b", "/x/b"), ("a", "/x/a2")]
        assert registry.remove_source(str(project), "b") and not registry.remove_source(str(project), "b")
        registry.set_build_config(str(project), extensions=["py"])
        assert KnowledgeRegistry(registry.path).build_config(str(project)) == {"extensions": ["py"]}

    def test_build_registers_and_loads_outputs(self, project, registry, tmp_path):
        store = KnowledgeStore()
        service = KnowledgeService(store=store, registry=registry, config={"KNOWLEDGE_OUTPUT_DIR": str(tmp_path / "kb"),
                                                                       "KNOWLEDGE_EXTENSIONS": ["py"]})
        store.mark_stale(str(project / "src" / "app" / "util.py"))
        report = service.build(str(project), llm_call=FakeLLM())
        assert report["done"] == ["app/main.py", "app/util.py"]
        entry = registry.get(str(project))
        assert entry["build"]["source_root"] == "src" and entry["build"]["extensions"] == ["py"]
        assert {s["id"] for s in entry["sources"]} == {"proj-docs", "proj-knowledge"}
        card = store.get_component("app/main.py")
        assert card["summary"].startswith("Summary of app/main.py") and card["doc"]["path"] == "app/main.md"
        assert store.stale_keys() == []      # regenerated knowledge is current again

    def test_module_loads_registered_sources_for_a_project(self, project, registry, tmp_path):
        service = KnowledgeService(store=None, registry=registry, config={"KNOWLEDGE_OUTPUT_DIR": str(tmp_path / "kb")})
        service.build(str(project), llm_call=FakeLLM())
        module = KnowledgeModule(registry=registry)
        store = module.get_instance()
        assert not store.has_sources()
        loaded = module.ensure_project(str(project))
        assert len(loaded) == 2 and store.get_component("app/util.py")
        assert module.ensure_project(str(project)) == []     # already loaded

    def test_add_sources_remembers_for_project(self, project, registry, tmp_path):
        kb = tmp_path / "kbsrc"
        kb.mkdir()
        (kb / "a.md").write_text("## Intro\nSome documentation text here.")
        module = KnowledgeModule(registry=registry)
        module.add_sources([str(kb)], base_dir=str(project))
        assert [s.path for s in registry.sources(str(project))] == [str(kb)]
        module.add_sources([str(kb)], base_dir=str(tmp_path), remember=False)
        assert registry.sources(str(tmp_path)) == []


class TestTools:
    def test_status_and_update_tools(self, project, registry, tmp_path, monkeypatch):
        import ai.tools.base as base
        monkeypatch.setattr(base, "PROJECT_ROOT", str(project))
        llm = FakeLLM()
        monkeypatch.setattr(builder_mod, "default_llm_call", lambda model: llm)
        module = KnowledgeModule(registry=registry, config={"KNOWLEDGE_OUTPUT_DIR": str(tmp_path / "kb"),
                                                            "KNOWLEDGE_EXTENSIONS": "py"})
        store = module.get_instance()
        tools = store.tools.get_build_tools()

        status = tools["knowledge_status"]()
        assert status["status"] == "SUCCESS" and status["docs"]["missing"] == 2

        assert tools["update_knowledge"]()["error"] == "No model available to build knowledge."
        store.tools.set_llm(object())
        res = tools["update_knowledge"](max_files=1)
        assert res["status"] == "SUCCESS" and res["done"] == ["app/main.py"] and res["remaining"] == 1
        res = tools["update_knowledge"](paths=["@ROOT/src/app/util.py"])
        assert res["done"] == ["app/util.py"]
        assert store.has_sources() and store.find_symbol("helper")
        assert tools["update_knowledge"](paths=["@ROOT/README.md"])["status"] == "FAILED"
