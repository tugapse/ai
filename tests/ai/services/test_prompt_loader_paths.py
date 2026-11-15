"""System prompts are resolved inside <root>/system/system-prompt/ (real files, no os.path mocks)."""
from unittest.mock import patch

from ai.services.prompt_loader import PromptLoader, DEFAULT_SYSTEM_PROMPT


class _Config:
    def __init__(self, settings=None):
        self._settings = settings or {}

    def get(self, key, default=None):
        return self._settings.get(key, default)


def _load(root, name):
    with patch("ai.services.prompt_loader.func.get_root_directory", return_value=str(root)), \
            patch("ai.services.prompt_loader.TemplateInjection") as injection:
        injection.side_effect = lambda text: type("T", (), {"replace_system_template": lambda self: text})()
        return PromptLoader.load_system_prompt(_Config(), name)


def _write(root, rel, text):
    path = root / "system" / "system-prompt" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_named_prompt_is_found_in_system_prompt_folder(tmp_path):
    _write(tmp_path, "chat/default.md", "You are JARVIS.")
    assert _load(tmp_path, "chat/default") == "You are JARVIS."


def test_default_uses_system_prompt_default_md(tmp_path):
    _write(tmp_path, "default.md", "Default persona.")
    assert _load(tmp_path, "default") == "Default persona."


def test_empty_default_md_falls_back_to_builtin(tmp_path):
    _write(tmp_path, "default.md", "")
    assert _load(tmp_path, "default") == DEFAULT_SYSTEM_PROMPT


def test_missing_named_prompt_returns_empty(tmp_path):
    assert _load(tmp_path, "nope") == ""


def test_user_prompt_wins_over_system(tmp_path):
    _write(tmp_path, "default.md", "Shipped persona.")
    user = tmp_path / "user" / "system-prompt" / "default.md"
    user.parent.mkdir(parents=True)
    user.write_text("My persona.", encoding="utf-8")
    assert _load(tmp_path, "default") == "My persona."


def test_shipped_default_prompts_are_not_empty():
    from pathlib import Path
    base = Path(__file__).resolve().parents[3] / "assets" / "templates" / "system" / "system-prompt"
    for name in ("default.md", "chat/default.md"):
        assert "JARVIS" in (base / name).read_text(encoding="utf-8")
