"""Agent prompt files: user/system-prompt/ wins over system/system-prompt/."""
from ai.services.directory_manager import DirectoryManager


def _dm(tmp_path, monkeypatch):
    monkeypatch.setattr("ai.services.directory_manager.func.get_root_directory", lambda: str(tmp_path))
    return DirectoryManager()


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_user_prompt_wins(tmp_path, monkeypatch):
    _write(tmp_path / "system" / "system-prompt" / "agents" / "a.md", "system")
    _write(tmp_path / "user" / "system-prompt" / "agents" / "a.md", "user")
    assert open(_dm(tmp_path, monkeypatch).resolve_prompt_file("agents/a.md")).read() == "user"


def test_falls_back_to_system(tmp_path, monkeypatch):
    _write(tmp_path / "system" / "system-prompt" / "agents" / "b.md", "system")
    assert open(_dm(tmp_path, monkeypatch).resolve_prompt_file("agents/b.md")).read() == "system"


def test_missing_is_none(tmp_path, monkeypatch):
    assert _dm(tmp_path, monkeypatch).resolve_prompt_file("agents/none.md") is None
