import os

from ai.modules.knowledge.sources import SourceSpec, agent_allowed_sources, parse_source_entry, resolve_sources


def test_parse_entry_forms(tmp_path):
    base = str(tmp_path)
    assert parse_source_entry("docs", base) == SourceSpec(id="docs", path=os.path.join(base, "docs"), kind="auto")
    spec = parse_source_entry({"id": "api", "path": "/abs/api-docs", "kind": "DOCS"}, base)
    assert spec == SourceSpec(id="api", path="/abs/api-docs", kind="docs")
    assert parse_source_entry("@ROOT/kb", base).path == os.path.join(base, "kb")
    assert parse_source_entry({"path": "x", "kind": "weird"}, base).kind == "auto"
    assert parse_source_entry({"id": "no-path"}, base) is None
    assert parse_source_entry(42, base) is None


def test_resolve_merges_config_pipeline_and_cli(tmp_path):
    base = str(tmp_path)
    config = ["_knowledge", {"id": "code-docs", "path": "_docs", "kind": "docs"}]
    pipeline = [{"id": "team", "path": "/shared/kb"}, "_knowledge"]      # duplicate path is dropped
    cli = ["other/_knowledge"]                                            # same basename -> id gets a suffix
    specs = resolve_sources(config, pipeline, cli, None, base_dir=base)
    assert [s.id for s in specs] == ["knowledge", "code-docs", "team", "knowledge-2"]
    assert specs[1].kind == "docs"
    assert specs[3].path == os.path.join(base, "other", "_knowledge")


def test_single_entry_group(tmp_path):
    assert len(resolve_sources("kb", base_dir=str(tmp_path))) == 1


def test_agent_allowed_sources():
    assert agent_allowed_sources(None) is None
    assert agent_allowed_sources({"tools": []}) is None
    assert agent_allowed_sources({"knowledge": "docs"}) == ["docs"]
    assert agent_allowed_sources({"knowledge": []}) == []
