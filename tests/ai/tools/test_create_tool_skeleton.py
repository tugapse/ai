"""--create-tool writes a file the user tool loader accepts (a @tool inside a ToolCategory)."""
import pytest

from ai.cli.tools import build_tool_skeleton, tool_base_name
from ai.tools.tool_loader import load_and_register_user_tools
from ai.tools.tool_registry import ToolRegistry


@pytest.mark.parametrize("raw", ["git_status", "9lives", "_hidden", "x", "Weather API", "my-tool!"])
def test_skeleton_loads(tmp_path, raw):
    name = tool_base_name(raw)
    assert name and not name.startswith("_")
    (tmp_path / f"{name}.py").write_text(build_tool_skeleton(name), encoding="utf-8")
    registry = ToolRegistry()
    load_and_register_user_tools(registry, str(tmp_path))
    assert name in registry.get_all_tools()
    result = registry.execute_tool(name, {"argument": "hi"})
    assert result["status"] == "SUCCESS"


def test_base_name_rejects_empty():
    assert tool_base_name("!!!") == ""
    assert tool_base_name("___") == ""
