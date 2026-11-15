"""
Size limits for what goes into an agent payload.

A single tool result (a big file, a long command output) can fill most of a small model's context
and degrade its output format. Results above the limit are cut in the payload only (memory keeps
the full result for the Sentinel / long-term memory), with a note on how to get the rest.
"""

import json
from typing import Any, Dict

DEFAULT_TOOL_RESULT_MAX_CHARS = 12000


def _truncate_text(text: str, budget: int, first_line: int = 1):
    lines = text.split("\n")
    kept, size = [], 0
    for line in lines:
        if kept and size + len(line) + 1 > budget:
            break
        kept.append(line[:budget] if not kept else line)
        size += len(line) + 1
    last = first_line + len(kept) - 1
    total = first_line + len(lines) - 1
    note = (f"\n... [truncated: showing lines {first_line}-{last} of {total}. Read the rest with "
            f"read_file start_line={last + 1}, or search it with grep_file.]")
    return "\n".join(kept) + note


def cap_tool_result(result: Any, max_chars: int = DEFAULT_TOOL_RESULT_MAX_CHARS) -> Any:
    """The result itself when small enough, else a cut-down copy that says how to get the rest."""
    if not max_chars or max_chars <= 0:
        return result
    try:
        text = json.dumps(result, default=str)
    except Exception:
        text = str(result)
    if len(text) <= max_chars:
        return result

    if isinstance(result, dict) and isinstance(result.get("files"), dict) and result["files"]:
        files = result["files"]
        starts = result.get("line_ranges") or {}
        budget = max(500, max_chars // len(files))
        capped = {}
        for path, content in files.items():
            if isinstance(content, str) and len(content) > budget:
                first = (starts.get(path) or [1])[0] if isinstance(starts.get(path), (list, tuple)) else 1
                capped[path] = _truncate_text(content, budget, int(first or 1))
            else:
                capped[path] = content
        return {**result, "files": capped, "truncated": True}

    out: Dict[str, Any] = {}
    if isinstance(result, dict):
        out = {k: result[k] for k in ("status", "error", "path") if k in result}
    out.update({
        "truncated": True,
        "preview": text[:max_chars],
        "note": (f"Result truncated ({len(text)} characters). Ask for a smaller part: grep_file, "
                 "read_file with start_line/end_line, a narrower search or the next page."),
    })
    return out
