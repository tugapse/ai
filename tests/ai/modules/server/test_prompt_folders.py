"""Listing prompts by folder: the client's chat uses only the 'chat' folder."""

import pytest

from ai.modules.server.services.prompt_manager import InvalidPathError, PromptManager


@pytest.fixture
def manager(tmp_path):
    (tmp_path / "chat" / "work").mkdir(parents=True)
    (tmp_path / "chat" / "brief.md").write_text("Be brief.")
    (tmp_path / "chat" / "work" / "review.md").write_text("Review.")
    (tmp_path / "agent.md").write_text("Agent.")
    return PromptManager(tmp_path)


def test_chat_folder_lists_only_its_prompts_with_full_paths(manager):
    assert sorted(p["path"] for p in manager.list_prompts("chat")) == ["chat/brief", "chat/work/review"]


def test_missing_folder_is_empty(manager):
    assert manager.list_prompts("nope") == []


@pytest.mark.parametrize("folder", ["../", "chat/../..", "/etc"])
def test_folder_outside_the_root_is_refused(manager, folder):
    with pytest.raises(InvalidPathError):
        manager.list_prompts(folder)
