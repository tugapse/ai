"""
Per-project knowledge registry.

Remembers, for each project folder, which knowledge sources it uses and how its knowledge is
built, so `--knowledge` only has to be passed once:

    <root>/system/knowledge/projects.json
    {"/abs/project": {"sources": [{"id", "path", "kind"}], "build": {...}, "updated_at": ...}}
"""

import hashlib
import json
import os
import re
import threading
import time
from typing import Any, Dict, Iterable, List, Optional

import ai.functions as func
from ai.modules.knowledge.sources import SourceSpec

_LOCK = threading.RLock()


def default_registry_path() -> str:
    try:
        root = func.get_root_directory()
    except Exception:
        root = os.path.expanduser("~/Ai")
    return os.path.join(root, "system", "knowledge", "projects.json")


def project_key(project: str) -> str:
    return os.path.normpath(os.path.abspath(os.path.expanduser(project)))


def project_slug(project: str) -> str:
    """Folder name for a project's generated knowledge: '<name>-<hash8>'."""
    key = project_key(project)
    name = re.sub(r"[^A-Za-z0-9_.-]+", "-", os.path.basename(key) or "project").strip("-") or "project"
    return f"{name}-{hashlib.sha1(key.encode()).hexdigest()[:8]}"


class KnowledgeRegistry:
    """JSON-file backed registry. Thread-safe; every write is atomic (temp file + replace)."""

    def __init__(self, path: Optional[str] = None):
        self.path = path or default_registry_path()

    # ------------------------------------------------------------------ io
    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except FileNotFoundError:
            return {}
        except Exception as e:
            func.error(f"Knowledge registry unreadable ({self.path}): {e}")
            return {}

    def _save(self, data: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = f"{self.path}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, self.path)

    def _update(self, project: str, fn) -> Dict[str, Any]:
        key = project_key(project)
        with _LOCK:
            data = self._load()
            entry = data.get(key) or {"sources": [], "build": {}}
            fn(entry)
            entry["updated_at"] = time.time()
            data[key] = entry
            self._save(data)
            return entry

    # ------------------------------------------------------------------ reads
    def projects(self) -> Dict[str, Any]:
        with _LOCK:
            return self._load()

    def get(self, project: str) -> Dict[str, Any]:
        return self.projects().get(project_key(project)) or {"sources": [], "build": {}}

    def sources(self, project: str) -> List[SourceSpec]:
        out = []
        for s in self.get(project).get("sources", []):
            if isinstance(s, dict) and s.get("path"):
                out.append(SourceSpec(id=str(s.get("id") or os.path.basename(s["path"])), path=s["path"],
                                      kind=str(s.get("kind") or "auto")))
        return out

    def build_config(self, project: str) -> Dict[str, Any]:
        return dict(self.get(project).get("build") or {})

    # ------------------------------------------------------------------ writes
    def add_sources(self, project: str, specs: Iterable[SourceSpec]) -> None:
        """Registers sources for a project (same path: updated in place; same id, other path: replaced)."""
        specs = [s for s in specs if s and s.path and not s.path.startswith("memory://")]
        if not specs:
            return

        def apply(entry):
            current = [s for s in entry.get("sources", []) if isinstance(s, dict)]
            for spec in specs:
                current = [s for s in current if s.get("path") != spec.path and s.get("id") != spec.id]
                current.append({"id": spec.id, "path": spec.path, "kind": spec.kind})
            entry["sources"] = current

        self._update(project, apply)

    def remove_source(self, project: str, source_id: str) -> bool:
        removed = {"n": 0}

        def apply(entry):
            before = entry.get("sources", [])
            entry["sources"] = [s for s in before if s.get("id") != source_id]
            removed["n"] = len(before) - len(entry["sources"])

        self._update(project, apply)
        return removed["n"] > 0

    def set_build_config(self, project: str, **values: Any) -> Dict[str, Any]:
        def apply(entry):
            build = dict(entry.get("build") or {})
            build.update({k: v for k, v in values.items() if v is not None})
            entry["build"] = build

        return self._update(project, apply).get("build", {})
