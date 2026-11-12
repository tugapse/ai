"""
Filesystem tools: list, read, write, patch and delete project files.

Enabled by default; disable with "TOOLS_FILESYSTEM_ENABLED": false in config.json.
"""

from ai.modules.base_module import ToolModule
from ai.modules.tools_filesystem.tools import read_dir, read_file, read_files, write_file, patch_file, delete_file

TOOLS = [read_dir, read_file, read_files, write_file, patch_file, delete_file]


def create_module() -> ToolModule:
    return ToolModule("tools_filesystem", TOOLS, description='Filesystem tools: list, read, write, patch and delete project files.')
