"""
ContextEnricher: puts a small, budgeted slice of project knowledge and long-term memory into
each agent payload, so the agent starts from what is already known instead of re-exploring.

The heavy lifting stays in tools (search_knowledge, get_component, read_doc, query_memory);
this only adds short pointers, recomputed when the task or the touched files change.
"""

import os
import threading
from typing import Any, Dict, Iterable, List, Optional, Tuple

import ai.functions as func
from ai.modules.knowledge.project_paths import display_path

FILE_TOOLS_READ = ("read_file", "read_files", "grep_file")
FILE_TOOLS_WRITE = ("write_file", "patch_file", "delete_file")
PRIORITY_MEMORY_TYPES = ("decision", "user_preference")


def _short(text: str, size: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= size else text[:size - 3].rstrip() + "..."


def _first_sentence(text: str, size: int = 180) -> str:
    text = " ".join((text or "").split())
    cut = text.find(". ")
    if 0 < cut < size:
        return text[:cut + 1]
    return _short(text, size)


def paths_from_params(params: Dict[str, Any]) -> List[str]:
    """File paths named in a tool call's parameters."""
    out: List[str] = []
    for key in ("path", "filepath", "file", "paths", "files"):
        val = (params or {}).get(key)
        if isinstance(val, str) and val.strip():
            out.append(val.strip())
        elif isinstance(val, (list, tuple)):
            out.extend(str(v).strip() for v in val if isinstance(v, str) and v.strip())
    return out


def touched_files(tool_results: Iterable[Dict[str, Any]], limit: int = 3) -> List[str]:
    """Most recent distinct files read or changed by successful tool calls (newest first)."""
    seen: List[str] = []
    for res in reversed(list(tool_results or [])):
        if res.get("tool") not in FILE_TOOLS_READ + FILE_TOOLS_WRITE:
            continue
        result = res.get("result")
        if isinstance(result, dict) and str(result.get("status", "SUCCESS")).upper() not in ("SUCCESS", "OK"):
            continue
        for p in paths_from_params(res.get("parameters") or {}):
            if p not in seen:
                seen.append(p)
            if len(seen) >= limit:
                return seen
    return seen


class ContextEnricher:
    """
    Adds ``relevant_components``, ``related_to_touched_files`` and ``long_term_memory`` to a payload.
    """

    def __init__(self, knowledge: Any = None, ltm: Any = None, knowledge_top_k: int = 4,
                 max_chars: int = 1500, ltm_top_k: int = 4, ltm_min_relevance: float = 0.3):
        """
        Args:
            knowledge: KnowledgeStore (or None).
            ltm: VectorMemory (or None).
            knowledge_top_k: Components listed under relevant_components (0 = off).
            max_chars: Character budget for the knowledge blocks together.
            ltm_top_k: Memories listed under long_term_memory (0 = off).
            ltm_min_relevance: Minimum similarity for a memory to be injected.
        """
        self.knowledge = knowledge
        self.ltm = ltm
        self.knowledge_top_k = max(0, int(knowledge_top_k))
        self.max_chars = max(200, int(max_chars))
        self.ltm_top_k = max(0, int(ltm_top_k))
        self.ltm_min_relevance = float(ltm_min_relevance)
        self._cache: Dict[Tuple, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    @property
    def active(self) -> bool:
        has_kb = bool(self.knowledge is not None and self.knowledge.has_sources() and self.knowledge_top_k)
        return has_kb or bool(self.ltm is not None and self.ltm_top_k)

    def enrich(self, payload: Dict[str, Any], agent: str, task: str, tool_results: Iterable[Dict[str, Any]] = (),
               allowed_sources: Optional[List[str]] = None) -> Dict[str, Any]:
        """Adds the blocks to ``payload`` (in place) and returns it. Never raises."""
        task = (task or "").strip()
        if not task or not self.active:
            return payload
        files = touched_files(tool_results)
        stale = tuple(sorted(k for k in files if self.knowledge is not None and self._is_stale(k)))
        key = (agent, task, tuple(files), stale, tuple(allowed_sources) if allowed_sources is not None else None)
        with self._lock:
            blocks = self._cache.get(key)
        if blocks is None:
            blocks = {}
            try:
                blocks.update(self._knowledge_blocks(task, files, allowed_sources))
            except Exception as e:
                func.debug(f"ContextEnricher: knowledge lookup failed: {e}")
            try:
                memories = self._memory_block(task)
                if memories:
                    blocks["long_term_memory"] = memories
            except Exception as e:
                func.debug(f"ContextEnricher: memory lookup failed: {e}")
            with self._lock:
                if len(self._cache) > 64:
                    self._cache.clear()
                self._cache[key] = blocks
        payload.update(blocks)
        return payload

    def invalidate(self) -> None:
        with self._lock:
            self._cache.clear()

    # ------------------------------------------------------------------ blocks

    def _is_stale(self, path: str) -> bool:
        key = self.knowledge.resolve_key(path)
        return bool(key and self.knowledge.is_stale(key))

    def _knowledge_blocks(self, task: str, files: List[str], allowed: Optional[List[str]]) -> Dict[str, Any]:
        kb = self.knowledge
        if kb is None or not kb.has_sources() or not self.knowledge_top_k:
            return {}
        budget = self.max_chars
        out: Dict[str, Any] = {}

        lines: List[str] = []
        for hit in kb.search(task, top_k=self.knowledge_top_k, sources=allowed):
            line = f"{display_path(hit['path'])} - {_first_sentence(hit.get('summary', ''))}"
            if hit.get("sections"):
                line += f" [doc: {hit['sections'][0]['heading']}]"
            if hit.get("stale"):
                line += " (changed this session)"
            if len(line) > budget:
                break
            lines.append(line)
            budget -= len(line)
        if lines:
            out["relevant_components"] = lines

        related: List[str] = []
        for path in files:
            res = kb.neighbors(path, direction="both", sources=allowed)
            if not res:
                continue
            uses = [display_path(n["path"]) for n in res.get("uses", []) if n["relation"] != "references"][:5]
            used_by = [display_path(n["path"]) for n in res.get("used_by", []) if n["relation"] != "references"][:5]
            if not uses and not used_by:
                continue
            line = f"{display_path(res['path'])}: uses [{', '.join(uses)}]; used by [{', '.join(used_by)}]"
            line = _short(line, max(120, min(400, budget)))
            if len(line) > budget:
                break
            related.append(line)
            budget -= len(line)
        if related:
            out["related_to_touched_files"] = related
        return out

    def _memory_block(self, task: str) -> List[str]:
        if self.ltm is None or not self.ltm_top_k:
            return []
        hits = self.ltm.search(task, top_k=self.ltm_top_k * 2, min_relevance=self.ltm_min_relevance)
        hits.sort(key=lambda h: (h.get("type") in PRIORITY_MEMORY_TYPES, h.get("score", 0)), reverse=True)
        return [f"[{h.get('type', 'memory')}] {_short(h.get('content', ''), 300)}" for h in hits[:self.ltm_top_k]]
