import json

from ai.template_sync import MANIFEST_NAME, sync_system_templates


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _setup(tmp_path):
    src, dst = tmp_path / "templates" / "system", tmp_path / "Ai" / "system"
    _write(src / "config" / "mcp_config.json", "v1")
    _write(src / "inject" / "plan.md", "plan v1")
    _write(src / "logs" / "old.log", "runtime")
    return src, dst


def _sync(src, dst):
    return sync_system_templates(str(src), str(dst), skip=lambda rel: rel == "logs")


def test_first_sync_copies_files_and_skips_runtime(tmp_path):
    src, dst = _setup(tmp_path)
    assert _sync(src, dst) == []
    assert (dst / "config" / "mcp_config.json").read_text() == "v1"
    assert not (dst / "logs").exists()
    manifest = json.loads((dst / MANIFEST_NAME).read_text())
    assert set(manifest) == {"config/mcp_config.json", "inject/plan.md"}


def test_untouched_file_is_updated_without_backup(tmp_path):
    src, dst = _setup(tmp_path)
    _sync(src, dst)
    _write(src / "inject" / "plan.md", "plan v2")
    assert _sync(src, dst) == []
    assert (dst / "inject" / "plan.md").read_text() == "plan v2"
    assert not (dst / "backup").exists()


def test_edited_file_is_backed_up_then_updated(tmp_path):
    src, dst = _setup(tmp_path)
    _sync(src, dst)
    _write(dst / "config" / "mcp_config.json", "my edits")
    _write(src / "config" / "mcp_config.json", "v2")
    assert _sync(src, dst) == ["config/mcp_config.json"]
    assert (dst / "config" / "mcp_config.json").read_text() == "v2"
    backups = list((dst / "backup").rglob("mcp_config.json"))
    assert [b.read_text() for b in backups] == ["my edits"]


def test_old_install_without_manifest_backs_up_differences(tmp_path):
    src, dst = _setup(tmp_path)
    _write(dst / "config" / "mcp_config.json", "old shipped version")
    _write(dst / "inject" / "plan.md", "plan v1")
    assert _sync(src, dst) == ["config/mcp_config.json"]
    assert (dst / "config" / "mcp_config.json").read_text() == "v1"


def test_files_not_shipped_are_left_alone(tmp_path):
    src, dst = _setup(tmp_path)
    _write(dst / "models" / "mine.json", "{}")
    _sync(src, dst)
    assert (dst / "models" / "mine.json").read_text() == "{}"


def test_nothing_rewritten_when_up_to_date(tmp_path):
    src, dst = _setup(tmp_path)
    _sync(src, dst)
    mtime = (dst / MANIFEST_NAME).stat().st_mtime_ns
    assert _sync(src, dst) == []
    assert (dst / MANIFEST_NAME).stat().st_mtime_ns == mtime
