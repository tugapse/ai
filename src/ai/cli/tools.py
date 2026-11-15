"""``ai tools``: your own agent tools."""
import re

from ai.cli.base import SUPPRESS, add_actions, add_command

NAME = "tools"
HELP = "Create your own agent tools"
DESCRIPTION = """User tools are Python files in <AI folder>/user/tools/: each @tool belongs to a
ToolCategory. Add the tool names to an agent's "tools" list in a pipeline to use them.

  ai tools create NAME             write a ready-to-load skeleton
"""

DEFAULTS = {"create_tool": None}

LEGACY = {"--create-tool": "ai tools create"}


def register(subparsers, parent):
    parser = add_command(subparsers, NAME, HELP, DESCRIPTION, usage="%(prog)s ACTION")
    actions = add_actions(parser, "tools_command")
    create = add_command(actions, "create", "Write a new tool skeleton to user/tools/", usage="%(prog)s NAME")
    create.add_argument("create_tool", metavar="NAME", help="Tool (and file) name")


def add_legacy(parser):
    parser.add_argument("--create-tool", type=str, metavar="TOOL_NAME", help=SUPPRESS)


# --- handlers -----------------------------------------------------------------------

def tool_base_name(raw: str) -> str:
    """
    File and function name for --create-tool NAME: letters, digits and '_' only. A name starting
    with a digit or '_' gets a 'tool_' prefix (files starting with '_' are not loaded).
    """
    base = re.sub(r"[^a-zA-Z0-9_]", "", (raw or "").strip().replace(" ", "_").replace("-", "_"))
    base = base.lstrip("_")
    if base and not base[0].isalpha():
        base = f"tool_{base}"
    return base


def build_tool_skeleton(function_name: str) -> str:
    """
    Source of a new user tool file: one @tool function inside its own ToolCategory, the shape the
    tool loader accepts (see ai.tools.category and user/tools/_example_tools.py).
    """
    category = re.sub(r"[^a-z0-9_]", "", function_name.lower()).strip("_")
    if not category or not category[0].isalpha():
        category = f"tools_{category}".rstrip("_")
    category = category[:40]
    if len(category) < 2:
        category = f"{category}_tools"
    class_name = "".join(part.capitalize() for part in category.split("_") if part) + "Tools"
    return f'''"""
User tool: {function_name}. Loaded from <AI folder>/user/tools/ at startup.

Add "{function_name}" to an agent's "tools" list in a pipeline to give it to that agent.
Rules (checked at load time): every @tool belongs to a ToolCategory; the category name is 2-40
lowercase letters, digits or '_'; the description is one line (max 120 characters); each tool has a
docstring with an 'Args:' section.
"""

from ai.tools import ToolCategory, tool
from ai.tools.base import resolve_path  # use it for path parameters: keeps them inside @ROOT


@tool
def {function_name}(argument: str) -> dict:
    """
    Describe what this tool does and when the agent should use it.

    Args:
        argument (string): What this value is, with an example.

    Returns:
        result: what the tool returns, or an error.
    """
    try:
        result = f"Executing {function_name} with: {{argument}}"
        return {{"status": "SUCCESS", "result": result}}
    except Exception as e:
        return {{"status": "FAILED", "error": str(e)}}


class {class_name}(ToolCategory):
    name = "{category}"
    description = "One line: what this group of tools is for."

    def get_category_tools(self):
        return [{function_name}]
'''


def create_tool(prog, args, directory_manager) -> None:
    """
    Handles the creation of a new tool skeleton file based on the provided name.

    :param args: The parsed command-line arguments containing the tool name.
    :param directory_manager: The service responsible for managing file paths.
    :raises SystemExit: Exits if the tool name is invalid or the file already exists.
    """
    import os
    import sys
    import ai.functions as func
    from ai.color import Color
    if not args.create_tool:
        return

    tool_name = args.create_tool

    base_name = tool_base_name(tool_name)

    if not base_name:
        func.error("Invalid tool name. Please use alphanumeric characters, spaces, or hyphens.")
        sys.exit(1)

    filename = f"{base_name}.py"
    function_name = base_name

    user_tools_dir = directory_manager.get_user_tools_directory()
    func.ensure_directory_exists(user_tools_dir)

    file_path = os.path.join(user_tools_dir, filename)

    if os.path.exists(file_path):
        func.error(f"Tool file already exists: {file_path}")
        sys.exit(1)

    skeleton_content = build_tool_skeleton(function_name)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(skeleton_content.strip())

        func.out(f"{Color.GREEN}[+] Tool skeleton created successfully at: {file_path}{Color.RESET}")
        func.out(f"    Add '{function_name}' to an agent's \"tools\" list in your pipeline to use it.")

    except Exception as e:
        func.error(f"Failed to create tool file: {e}")
        sys.exit(1)

    sys.exit(0)


# Run before the model loads (see ai.cli.run_maintenance).
MAINTENANCE = (create_tool,)
