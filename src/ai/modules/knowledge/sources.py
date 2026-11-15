"""
Where knowledge comes from. Nothing is read from a fixed folder: sources are listed in
config.json (KNOWLEDGE_SOURCES), in the pipeline JSON ("knowledge"), passed with
--knowledge, or fed at runtime (ingest_knowledge tool / server API).

An entry is either a path string or {"id": ..., "path": ..., "kind": "auto|knowledge|docs"}.
Relative paths resolve against the workspace (the project root).
"""

import os
import re
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional

import ai.functions as func

SOURCE_KINDS = ("auto", "knowledge", "docs")


@dataclass(frozen=True)
class SourceSpec:
    id: str
    path: str               # absolute directory (or file) path
    kind: str = "auto"


def _slug(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_.-]+", "-", text).strip("-._")
    return s or "knowledge"


def parse_source_entry(entry: Any, base_dir: Optional[str] = None) -> Optional[SourceSpec]:
    """
    Turns one configuration entry into a SourceSpec.

    Args:
        entry: A path string or a dict with path (required), id and kind.
        base_dir: Directory that relative paths resolve against (default: current directory).

    Returns:
        The SourceSpec, or None (with a log line) for unusable entries.
    """
    if isinstance(entry, str):
        path, sid, kind = entry, None, "auto"
    elif isinstance(entry, dict):
        path, sid, kind = entry.get("path"), entry.get("id"), entry.get("kind") or "auto"
    else:
        func.log(f"Knowledge: ignoring source entry {entry!r}", level="WARN")
        return None

    if not path or not str(path).strip():
        func.log(f"Knowledge: source entry without path: {entry!r}", level="WARN")
        return None

    path = os.path.expanduser(str(path).strip())
    if path.startswith("@ROOT"):
        path = path[len("@ROOT"):].lstrip("/\\") or "."
    if not os.path.isabs(path):
        path = os.path.join(base_dir or os.getcwd(), path)
    path = os.path.normpath(os.path.abspath(path))

    kind = str(kind).strip().lower()
    if kind not in SOURCE_KINDS:
        func.log(f"Knowledge: unknown kind '{kind}' for {path}, using auto.", level="WARN")
        kind = "auto"

    sid = str(sid).strip() if sid else _slug(os.path.basename(path.rstrip(os.sep)) or path)
    return SourceSpec(id=sid, path=path, kind=kind)


def resolve_sources(*groups: Optional[Iterable[Any]], base_dir: Optional[str] = None) -> List[SourceSpec]:
    """
    Merges source entries from several origins (config, pipeline, CLI, ...), in order.

    Duplicated paths keep the first entry; a duplicated id for a different path gets a suffix.
    """
    out: List[SourceSpec] = []
    seen_paths, seen_ids = set(), set()
    for group in groups:
        if not group:
            continue
        if isinstance(group, (str, dict)):
            group = [group]
        for entry in group:
            spec = parse_source_entry(entry, base_dir)
            if not spec or spec.path in seen_paths:
                continue
            sid, n = spec.id, 2
            while sid in seen_ids:
                sid = f"{spec.id}-{n}"
                n += 1
            if sid != spec.id:
                spec = SourceSpec(id=sid, path=spec.path, kind=spec.kind)
            seen_paths.add(spec.path)
            seen_ids.add(spec.id)
            out.append(spec)
    return out


def agent_allowed_sources(agent_config: Optional[dict]) -> Optional[List[str]]:
    """
    The source ids an agent may see (its "knowledge" list in the pipeline), or None for all.
    """
    if not agent_config:
        return None
    allowed = agent_config.get("knowledge")
    if allowed is None:
        return None
    if isinstance(allowed, str):
        allowed = [allowed]
    return [str(a) for a in allowed]
