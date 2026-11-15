"""
Maps knowledge paths to files in the current project.

Knowledge paths are relative to whatever root the knowledge was generated from (often 'src/'),
e.g. 'ai/agents/context_sentinel.py' while the file is '@ROOT/src/ai/agents/context_sentinel.py'.
Agents pass these paths to filesystem tools, so results show the real '@ROOT/...' path.
"""

import os
import threading
from typing import Dict, List, Optional, Tuple

_SKIP = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
_PREFERRED = ("src", "lib", "app", "source")

_found: Dict[Tuple[str, str], str] = {}
_subdirs: Dict[str, List[str]] = {}
_lock = threading.Lock()


def _project_root() -> str:
    from ai.tools.base import get_project_root
    return os.path.abspath(get_project_root())


def _candidate_dirs(root: str) -> List[str]:
    with _lock:
        cached = _subdirs.get(root)
    if cached is not None:
        return cached
    try:
        names = [n for n in os.listdir(root)
                 if n not in _SKIP and not n.startswith(".") and os.path.isdir(os.path.join(root, n))]
    except OSError:
        names = []
    names.sort(key=lambda n: (n not in _PREFERRED, _PREFERRED.index(n) if n in _PREFERRED else 0, n))
    with _lock:
        _subdirs[root] = names
    return names


def project_path(path: str, root: Optional[str] = None) -> Optional[str]:
    """
    '@ROOT/...' path of the project file a knowledge path refers to, or None when no such file exists.
    Looks at <root>/<path>, then <root>/<subdir>/<path> (src/ first).
    """
    if not path:
        return None
    p = str(path).strip().replace("\\", "/")
    if p.startswith("@ROOT"):
        return p
    p = p.lstrip("/")
    root = os.path.abspath(root or _project_root())
    key = (root, p)
    with _lock:
        hit = _found.get(key)
    if hit:
        return hit
    found = None
    if os.path.isfile(os.path.join(root, p)):
        found = f"@ROOT/{p}"
    else:
        for d in _candidate_dirs(root):
            if os.path.isfile(os.path.join(root, d, p)):
                found = f"@ROOT/{d}/{p}"
                break
    if found:
        with _lock:
            _found[key] = found
    return found


def display_path(path: str, root: Optional[str] = None) -> str:
    """The project path when the file exists, else the knowledge path unchanged."""
    try:
        return project_path(path, root) or path
    except Exception:
        return path
