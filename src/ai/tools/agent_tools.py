"""
Backwards-compatibility shim.

Built-in tools now live in app modules (``ai.modules.tools_*``) and are loaded by
the ModuleRegistry; shared helpers live in ``ai.tools.base``. This module keeps old
imports working (``from ai.tools.agent_tools import tool``, ``AVAILABLE_TOOLS``,
individual tool functions, ``PROJECT_ROOT``).
"""

import subprocess  # noqa: F401  (kept so existing patches of agent_tools.subprocess.* still apply)
import sys
import types

from ai.tools import base as _base
from ai.tools.base import tool, ensure_list, resolve_path, sanitize_output_path, _resolve_path, _sanitize_output_path  # noqa: F401

from ai.modules.tools_filesystem.tools import read_dir, read_file, read_files, write_file, patch_file, delete_file  # noqa: F401
from ai.modules.tools_search.tools import smart_search, grep_file  # noqa: F401
from ai.modules.tools_shell.tools import execute_command, _run_non_interactive, _kill_process_tree, _NON_INTERACTIVE_ENV  # noqa: F401
from ai.modules.tools_web.tools import web_search, web_read  # noqa: F401
from ai.modules.tools_notify.tools import send_notification  # noqa: F401

# Every built-in tool, regardless of which modules are enabled in config.
AVAILABLE_TOOLS = {
    fn.__name__: fn for fn in (
        read_dir, read_file, read_files, write_file, patch_file, delete_file,
        smart_search, grep_file, execute_command,
        web_search, web_read, send_notification,
    )
}


class _CompatModule(types.ModuleType):
    """Forwards PROJECT_ROOT reads/writes to ai.tools.base so old code that repoints it still works."""

    @property
    def PROJECT_ROOT(self):
        return _base.PROJECT_ROOT

    @PROJECT_ROOT.setter
    def PROJECT_ROOT(self, value):
        _base.PROJECT_ROOT = value


sys.modules[__name__].__class__ = _CompatModule
