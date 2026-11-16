"""The ToolCategory contract, its registration in the ToolRegistry and user tool loading."""

import pytest

from ai.tools import ToolCategory, ToolCategoryError, tool
from ai.tools.tool_loader import load_and_register_user_tools
from ai.tools.tool_registry import ToolRegistry


def fresh_registry() -> ToolRegistry:
    reg = object.__new__(ToolRegistry)
    reg._tools, reg._categories, reg._tool_category = {}, {}, {}
    return reg


@tool
def ping(host: str = "x") -> dict:
    """
    Pings a host.

    Args:
        host (string): Host name.
    """
    return {"status": "SUCCESS", "host": host}


@tool
def no_args() -> dict:
    """Returns nothing useful."""
    return {"status": "SUCCESS"}


class Cat(ToolCategory):
    def __init__(self, name, description, tools):
        self.name, self.description, self._tools = name, description, list(tools)

    def get_category_tools(self):
        return self._tools


def make(name="net", description="Network checks.", tools=(ping,)):
    return Cat(name, description, tools)


def test_register_category_and_lookup():
    reg = fresh_registry()
    assert list(reg.register_category(make(tools=(ping, no_args)))) == ["ping", "no_args"]
    assert reg.category_of("ping") == "net"
    assert reg.category_tools("net") == ["ping", "no_args"]
    assert reg.execute_tool("ping", {"host": "a"})["host"] == "a"
    reg.unregister_category("net")
    assert reg.category_of("ping") is None and "ping" not in reg.get_all_tools()


def test_abstract_method_is_required():
    class Missing(ToolCategory):
        name, description = "x1", "y"
    with pytest.raises(TypeError):
        Missing()


@pytest.mark.parametrize("cat, message", [
    (make(name="Bad Name"), "invalid category name"),
    (make(description=""), "description is required"),
    (make(description="two\nlines"), "one line"),
    (make(description="x" * 121), "one line"),
])
def test_category_fields_are_validated(cat, message):
    with pytest.raises(ToolCategoryError, match=message):
        fresh_registry().register_category(cat)


def test_tools_are_validated():
    def plain(host):
        """Doc.

        Args:
            host (string): h.
        """
    with pytest.raises(ToolCategoryError, match="not marked with @tool"):
        fresh_registry().register_category(make(tools=(plain,)))

    @tool
    def undocumented(host):
        pass
    with pytest.raises(ToolCategoryError, match="needs a docstring"):
        fresh_registry().register_category(make(tools=(undocumented,)))

    @tool
    def no_args_section(host):
        """Does things with a host."""
    with pytest.raises(ToolCategoryError, match="Args:"):
        fresh_registry().register_category(make(tools=(no_args_section,)))


def test_a_tool_belongs_to_one_category_and_names_are_unique_per_type():
    reg = fresh_registry()
    reg.register_category(make())
    with pytest.raises(ToolCategoryError, match="already belongs to category 'net'"):
        reg.register_category(make(name="other"))
    reg.register_category(make(tools=(ping, no_args)))          # same category again: replaced
    assert reg.category_tools("net") == ["ping", "no_args"]

    class OtherType(ToolCategory):
        name, description = "net", "Another net."
        def get_category_tools(self):
            return [no_args]
    with pytest.raises(ToolCategoryError, match="already used"):
        reg.register_category(OtherType())


USER_FILE = '''
from ai.tools import ToolCategory, tool

@tool
def git_status(path: str = "@ROOT") -> dict:
    """
    Shows the git status.

    Args:
        path (string, optional): Repository folder.
    """
    return {"status": "SUCCESS"}

class GitTools(ToolCategory):
    name = "git"
    description = "Inspect the repository."
    def get_category_tools(self):
        return [git_status]
'''


def test_user_tools_load_as_categories(tmp_path):
    (tmp_path / "git_tools.py").write_text(USER_FILE)
    (tmp_path / "_example.py").write_text("raise RuntimeError('not loaded')")
    reg = fresh_registry()
    load_and_register_user_tools(reg, str(tmp_path))
    assert reg.category_of("git_status") == "git"


def test_user_tools_load_again_in_the_same_registry(tmp_path):
    """Every agent run imports the user files again (new class objects) into the singleton registry."""
    (tmp_path / "git_tools.py").write_text(USER_FILE)
    reg = fresh_registry()
    load_and_register_user_tools(reg, str(tmp_path))
    load_and_register_user_tools(reg, str(tmp_path))
    assert reg.category_tools("git") == ["git_status"]


def test_another_class_cannot_take_a_category_name(tmp_path):
    (tmp_path / "git_tools.py").write_text(USER_FILE)
    (tmp_path / "other_git.py").write_text(USER_FILE.replace("git_status", "git_log"))
    with pytest.raises(ImportError, match="already used by GitTools"):
        load_and_register_user_tools(fresh_registry(), str(tmp_path))


def test_user_tool_without_category_is_refused(tmp_path):
    (tmp_path / "loose.py").write_text(USER_FILE + '''
@tool
def orphan() -> dict:
    """No category."""
    return {}
''')
    with pytest.raises(ImportError, match="without a category: orphan"):
        load_and_register_user_tools(fresh_registry(), str(tmp_path))


def test_shipped_example_is_valid(tmp_path):
    import shutil
    from pathlib import Path
    example = Path(__file__).parents[3] / "assets/templates/user/tools/_example_tools.py"
    shutil.copy(example, tmp_path / "example_tools.py")
    reg = fresh_registry()
    load_and_register_user_tools(reg, str(tmp_path))
    assert reg.category_tools("git") == ["git_status"]


def test_builtin_providers_follow_the_contract():
    import importlib
    from ai.modules.knowledge.store import KnowledgeStore
    from ai.modules.vector_memory.memory_tools import MemoryTools

    reg = fresh_registry()
    for name in ("filesystem", "search", "shell", "web", "notify"):
        module = importlib.import_module(f"ai.modules.tools_{name}").create_module()
        module.initialize()
        assert reg.register_category(module)
        assert module.name == name
    assert set(reg.register_category(MemoryTools())) == {"query_memory", "remember", "trigger_reflection"}
    store = KnowledgeStore()
    assert "search_knowledge" not in reg.register_category(store.tools)       # no sources yet
    store.ingest_documents("t", [{"component": {"name": "m", "source_path": "/a/m.py"},
                                  "vector_memory": {"semantic_summary": "Module m."}}])
    assert "search_knowledge" in reg.register_category(store.tools)


def test_string_params_are_coerced_to_declared_types():
    def wait(**kwargs):
        """
        Waits.

        Args:
            timeout (int, optional): Seconds.
            loud (bool, optional): Beep.
            label (string, optional): Text.
        """
        return {"status": "SUCCESS", **kwargs}

    reg = fresh_registry()
    reg._tools["wait"] = wait
    out = reg.execute_tool("wait", {"timeout": "180", "loud": "true", "label": "42"})
    assert out["timeout"] == 180 and out["loud"] is True and out["label"] == "42"
    assert reg.execute_tool("wait", {"timeout": "soon"})["timeout"] == "soon"
