import shutil

from ai.config import ProgramConfig, RUNTIME_TEMPLATE_DIRS


def test_runtime_dirs_are_not_copied(tmp_path):
    src = tmp_path / "templates"
    for rel in ["system/inject/agent-out.md", "system/logs/old.log", "system/pids/x.pid",
                "system/frontend/v1/index.html", "user/server/devices.json", "user/task/t.md",
                "workspace/scratch.txt"]:
        f = src / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x")

    dest = tmp_path / "user-dir"
    ignore = ProgramConfig._runtime_dirs_ignore(str(src))
    for item in src.iterdir():
        if item.name in RUNTIME_TEMPLATE_DIRS:
            continue
        shutil.copytree(item, dest / item.name, ignore=ignore)

    assert (dest / "system/inject/agent-out.md").exists()
    assert (dest / "user/task/t.md").exists()
    for rel in ["system/logs", "system/pids", "system/frontend", "user/server", "workspace"]:
        assert not (dest / rel).exists(), rel


def test_vector_memory_false_written_by_old_default_is_removed_once():
    cfg = ProgramConfig({"VECTOR_MEMORY_ENABLED": False, "MODEL_CONFIG_NAME": "x.json"})
    assert cfg._migrate_defaults() is True
    assert "VECTOR_MEMORY_ENABLED" not in cfg.config and cfg.config["MODEL_CONFIG_NAME"] == "x.json"
    assert cfg.config["DEFAULTS_MIGRATION"] == 1
    # after the migration, an explicit false stays
    cfg.config["VECTOR_MEMORY_ENABLED"] = False
    assert cfg._migrate_defaults() is False
    assert cfg.config["VECTOR_MEMORY_ENABLED"] is False


def test_migration_keeps_explicit_true():
    cfg = ProgramConfig({"VECTOR_MEMORY_ENABLED": True})
    cfg._migrate_defaults()
    assert cfg.config["VECTOR_MEMORY_ENABLED"] is True


def test_user_settings_in_config_json_are_kept(tmp_path, monkeypatch):
    """Values set in config.json survive loading (they used to be reset to the defaults)."""
    import json
    (tmp_path / "config.json").write_text(json.dumps({
        "HIL_TOOLS": [], "AGENT_THOUGHT": True, "MODEL_CONFIG_NAME": "other.json",
        "VECTOR_DB_PATH": str(tmp_path / "mydb"), "DEFAULTS_MIGRATION": 1,
    }))
    monkeypatch.setenv("AI_ASSISTANT_DIRECTORY", str(tmp_path))
    cfg = ProgramConfig()
    cfg.load_predefined_config(None)
    assert cfg.config["HIL_TOOLS"] == []
    assert cfg.config["AGENT_THOUGHT"] is True
    assert cfg.config["MODEL_CONFIG_NAME"] == "other.json"
    assert cfg.config["VECTOR_DB_PATH"] == str(tmp_path / "mydb")
    assert cfg.config["SYSTEM_PROMPT_FILE"] == "default"      # missing ones still get defaults
