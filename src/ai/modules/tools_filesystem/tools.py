"""Filesystem tools: list, read, write, patch and delete project files."""

import ast
import difflib
import json
import os
import re
from typing import Any, Dict, Optional, Tuple

from ai.tools.base import tool, resolve_path as _resolve_path, sanitize_output_path as _sanitize_output_path, ensure_list, get_project_root


ESCAPE_NOTE = ("Literal \\n sequences were converted to line breaks. Write real line breaks inside CDATA, "
               "never \\n escapes.")
_ESCAPES = {"n": "\n", "t": "\t", "r": "", '"': '"', "'": "'"}


def _unescape_text(text: str) -> str:
    return re.sub(r"\\(n|t|r|\"|')", lambda m: _ESCAPES[m.group(1)], text)


def _looks_escaped(text: Optional[str]) -> bool:
    """
    True for code sent with JSON-style escapes instead of line breaks: no real line break, at least
    two literal \\n, and not a valid one-line JSON document (minified JSON legitimately has them).
    """
    if not text or "\n" in text or text.count("\\n") < 2:
        return False
    try:
        json.loads(text)
        return False
    except (ValueError, TypeError):
        return True


def _fix_escapes(text: Optional[str]) -> Tuple[Optional[str], bool]:
    """(text, changed): undoes JSON-style escapes when the text looks escaped (see _looks_escaped)."""
    if _looks_escaped(text):
        return _unescape_text(text), True
    return text, False


def _syntax_warning(path: str, content: str) -> Optional[str]:
    """Why a written .py/.json file no longer parses, or None (other types are not checked)."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".py":
            ast.parse(content)
        elif ext == ".json":
            json.loads(content)
        return None
    except SyntaxError as e:
        line = (e.text or "").strip()
        return f"The file no longer parses: SyntaxError line {e.lineno}: {e.msg}" + (f" -> {line[:120]}" if line else "")
    except ValueError as e:
        return f"The file is not valid JSON: {e}"


def _duplicate_warning(search: str, replace: str, after: str) -> Optional[str]:
    """
    Warns when the lines right after the patched block repeat lines that the replace text added:
    usually the search held only the first line of a block that replace rewrote in full.
    """
    following = [l.strip() for l in after.split("\n") if l.strip()][:3]
    if len(following) < 2:
        return None
    rep_lines = [l.strip() for l in replace.split("\n") if l.strip()]
    search_lines = {l.strip() for l in search.split("\n") if l.strip()}
    for i in range(len(rep_lines) - len(following) + 1):
        if rep_lines[i:i + len(following)] == following and not set(following) <= search_lines:
            return ("The lines after the replaced block repeat lines of your replace text (now duplicated). "
                    "The search text probably held only the start of the block: read the file and remove the duplicate.")
    return None


INDENT_NOTE = "The search block matched only when ignoring indentation; the file's indentation was used."


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def _shift(line: str, delta: int) -> str:
    if not line.strip() or delta == 0:
        return line
    if delta > 0:
        return " " * delta + line
    return line[min(-delta, _indent(line)):]


def _match_ignoring_indent(content: str, search: str, replace: str) -> Optional[Tuple[str, str]]:
    """
    (file_block, adjusted_replace) when search matches exactly one block of the file once leading
    whitespace is ignored; replace is shifted by the indentation difference of the first line, and
    a first line indented on its own (XML nesting) is aligned like the rest.
    """
    s_lines = search.split("\n")
    while s_lines and not s_lines[-1].strip():
        s_lines.pop()
    if not s_lines or not s_lines[0].strip():
        return None
    f_lines = content.split("\n")
    wanted = [l.strip() for l in s_lines]
    hits = [i for i in range(len(f_lines) - len(s_lines) + 1)
            if [l.strip() for l in f_lines[i:i + len(s_lines)]] == wanted]
    if len(hits) != 1:
        return None
    block = f_lines[hits[0]:hits[0] + len(s_lines)]
    r_lines = replace.split("\n")
    first_delta = _indent(block[0]) - _indent(s_lines[0])
    if len(s_lines) > 1:
        body_delta = _indent(block[1]) - _indent(s_lines[1])
        if r_lines:
            r_lines[0] = _shift(r_lines[0], first_delta)
        r_lines[1:] = [_shift(l, body_delta) for l in r_lines[1:]]
    else:
        r_lines = [_shift(l, first_delta) for l in r_lines]
    return "\n".join(block), "\n".join(r_lines)


def _write_result(full_path: str, content: str, result: Dict[str, Any], notes) -> Dict[str, Any]:
    warning = _syntax_warning(full_path, content)
    if warning:
        result["warning"] = warning + ". Read the file and fix it."
    notes = [n for n in notes if n]
    if notes:
        result["note"] = " ".join(notes)
    return result


@tool
def read_dir(**kwargs) -> Dict[str, Any]:
    """
    List the files and folders in a directory. Use it to explore the project structure.

    Args:
        path (list, optional): Folder like '@ROOT/src'. Repeat the <path> tag to list several folders. Default '@ROOT'.
        depth (int, optional): How many folder levels to open. 0 = only this folder. Default 0.

    Returns:
        results: {folder: {files: [...], folders: {...}}}. Folders deeper than depth show
        '[Sub-entries hidden. Increase depth to see.]': call again with a bigger depth to open them.
    """
    try:
        path_input = kwargs.get("paths", kwargs.get("path", "@ROOT"))
        path = ensure_list(path_input)
        depth = int(kwargs.get("depth", 0))
        results = {}
        had_errors = False

        def get_structure(current_path, current_depth):
            items = os.listdir(current_path)
            res = {
                "files": [f for f in items if os.path.isfile(os.path.join(current_path, f))],
                "folders": {}
            }
            found_folders = [d for d in items if os.path.isdir(os.path.join(current_path, d))]
            for d in found_folders:
                full_d_path = os.path.join(current_path, d)
                if current_depth > 0:
                    res["folders"][d] = get_structure(full_d_path, current_depth - 1)
                else:
                    res["folders"][d] = "[Sub-entries hidden. Increase depth to see.]"
            return res

        for p in path:
            try:
                target = _resolve_path({"path": p})
                if not os.path.isdir(target):
                    raise FileNotFoundError(f"No such directory: '{p}'")
                structure = get_structure(target, depth)
                results[_sanitize_output_path(target)] = structure
            except Exception as e:
                results[p] = f"ERROR: {str(e)}"
                had_errors = True

        if had_errors:
            error_summary = "One or more paths could not be read."
            if len(path) == 1:
                error_summary = next(iter(results.values()))
            return {"status": "FAILED", "error": error_summary, "results": results}

        return {"status": "SUCCESS", "results": results}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

@tool
def read_file(**kwargs) -> Dict[str, Any]:
    """
    Read the text of a file (all of it, or a range of lines). For several files use read_files; to
    find something in a big file without reading all of it use grep_file.

    Args:
        path (list): File like '@ROOT/src/app.py'. Repeat the <path> tag to read several files.
        start_line (int, optional): First line to read (1-based). Use it to continue a truncated file.
        end_line (int, optional): Last line to read (inclusive). Default: end of the file.

    Returns:
        files: {path: content}. If a file cannot be read, status is FAILED and its entry holds the error.
        With start_line/end_line, line_ranges gives {path: [first, last, total_lines]}.
    """
    try:
        path_input = kwargs.get("path")
        path = ensure_list(path_input)

        def as_int(value):
            try:
                return int(value) if value not in (None, "") else None
            except (TypeError, ValueError):
                return None

        start_line, end_line = as_int(kwargs.get("start_line")), as_int(kwargs.get("end_line"))
        ranged = start_line is not None or end_line is not None
        results = {}
        line_ranges = {}
        had_errors = False

        for p in path:
            try:
                full_path = _resolve_path({"path": p})
                if not os.path.isfile(full_path):
                    raise FileNotFoundError(f"No such file: '{p}'")
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    sanitized_path = _sanitize_output_path(full_path)
                    if ranged:
                        lines = content.split("\n")
                        first = max(1, start_line or 1)
                        last = min(len(lines), end_line or len(lines))
                        content = "\n".join(lines[first - 1:last])
                        line_ranges[sanitized_path] = [first, last, len(lines)]
                    results[sanitized_path] = content
            except Exception as e:
                results[p] = f"FAILED: {str(e)}"
                had_errors = True
        
        if had_errors:
            error_summary = "One or more files could not be read."
            if len(path) == 1:
                error_summary = next(iter(results.values()))
            return {"status": "FAILED", "error": error_summary, "files": results}

        response = {"status": "SUCCESS", "files": results}
        if ranged:
            response["line_ranges"] = line_ranges
        return response
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

@tool
def write_file(**kwargs) -> Dict[str, Any]:
    """
    Create a file, or REPLACE an existing file's whole content. Missing folders are created.
    To change only part of an existing file, use patch_file instead (it keeps the rest intact).

    Args:
        path (string): Destination file like '@ROOT/src/app.py'.
        content (string): The complete file content. Wrap it in <![CDATA[ ... ]]> so code with <, > or & is kept exactly. Use real line breaks, never \\n escapes.

    Returns:
        status SUCCESS and the written path, or status FAILED with the reason. A 'warning' means a
        .py/.json file no longer parses: read it and fix it.
    """
    if "content" not in kwargs or kwargs.get("content") is None:
        return {"status": "FAILED", "error": "No content given: nothing was written. Pass the complete file "
                                             "content, or use patch_file to change part of a file."}
    try:
        full_path = _resolve_path(kwargs)
        content, unescaped = _fix_escapes(str(kwargs.get("content")))
        if not content.strip() and os.path.isfile(full_path) and os.path.getsize(full_path) > 0:
            # An empty write over a real file is almost always a lost parameter, not intent.
            return {"status": "FAILED", "error": "Refusing to replace a non-empty file with empty content. "
                                                 "Use patch_file to change it, or delete_file to remove it."}
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        sanitized = _sanitize_output_path(full_path)
        return _write_result(full_path, content, {"status": "SUCCESS", "path": sanitized},
                             [ESCAPE_NOTE if unescaped else None])
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

@tool
def patch_file(**kwargs) -> Dict[str, Any]:
    """
    Replace one exact block of text inside an existing file, keeping everything else unchanged.
    Read the file (or grep_file it) first and copy the block EXACTLY, including indentation.

    Args:
        path (string): The file to change, e.g. '@ROOT/src/app.py'.
        search (string): The exact current text to replace. Must appear exactly once in the file; add surrounding lines if it is not unique. Wrap in <![CDATA[ ... ]]>.
        replace (string): The new text that takes its place. Wrap in <![CDATA[ ... ]]>. Use an empty value to delete the block.

    Only the search text is replaced: to add code after a function, put that whole function in search
    and repeat it in replace followed by the new code. Use real line breaks, never \\n escapes.

    Returns:
        status SUCCESS and diff_summary (a short unified diff). FAILED if the search block is not
        found (check indentation/whitespace) or is not unique (include more context). A 'warning'
        means a .py/.json file no longer parses after the change: read it and fix it.
    """
    try:
        full_path = _resolve_path(kwargs)
        search_block = kwargs.get("search")
        replace_block = kwargs.get("replace")

        if not search_block or replace_block is None:
            return {"status": "FAILED", "error": "Both 'search' and 'replace' are required."}

        if not os.path.exists(full_path):
            return {"status": "FAILED", "error": f"File not found at path: {full_path}"}

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        content_normalized = content.replace("\r\n", "\n")
        search_normalized = search_block.replace("\r\n", "\n")
        replace_normalized = replace_block.replace("\r\n", "\n")

        notes = []
        if search_normalized not in content_normalized and _looks_escaped(search_normalized):
            candidate = _unescape_text(search_normalized)
            if candidate in content_normalized:
                search_normalized = candidate
                notes.append(ESCAPE_NOTE)
        # replace written with escapes while the code has real line breaks (search or file)
        if "\n" in search_normalized or "\n" in content_normalized:
            replace_normalized, unescaped = _fix_escapes(replace_normalized)
            if unescaped and ESCAPE_NOTE not in notes:
                notes.append(ESCAPE_NOTE)

        if search_normalized not in content_normalized:
            tolerant = _match_ignoring_indent(content_normalized, search_normalized, replace_normalized)
            if tolerant is None:
                return {"status": "FAILED", "error": "The 'search' block was not found. Check indentation."}
            search_normalized, replace_normalized = tolerant
            notes.append(INDENT_NOTE)

        # search without its indentation matched inside an indented line, while replace repeats
        # that indentation: drop it from replace's first line so it is not indented twice
        pos = content_normalized.find(search_normalized)
        line_start = content_normalized.rfind("\n", 0, pos) + 1
        indent = content_normalized[line_start:pos]
        if indent and not indent.strip() and replace_normalized.startswith(indent):
            replace_normalized = replace_normalized[len(indent):]

        if content_normalized.count(search_normalized) > 1:
            return {"status": "FAILED", "error": "The 'search' block is not unique. Provide more context."}

        new_content = content_normalized.replace(search_normalized, replace_normalized, 1)
        start = content_normalized.index(search_normalized)
        duplicate = _duplicate_warning(search_normalized, replace_normalized,
                                       content_normalized[start + len(search_normalized):])
        diff = list(difflib.unified_diff(
            content_normalized.splitlines(), new_content.splitlines(),
            fromfile="original", tofile="patched", lineterm=""
        ))

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        result = _write_result(full_path, new_content, {
            "status": "SUCCESS",
            "path": _sanitize_output_path(full_path),
            "diff_summary": "\n".join(diff[:15]) + ("\n..." if len(diff) > 15 else ""),
        }, notes)
        if duplicate:
            result["warning"] = (result.get("warning", "") + " " + duplicate).strip()
        return result
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

@tool
def read_files(**kwargs) -> Dict[str, Any]:
    """
    Read several files in ONE call. Prefer this over calling read_file once per file.

    Args:
        paths (list): File paths like '@ROOT/src/app.py'. Repeat the <paths> tag once per file.

    Returns:
        status SUCCESS and files: {path: content}. If any file cannot be read, status is FAILED and
        that file's entry holds the error instead of content (the other files are still returned).
    """
    paths = kwargs.get("paths", kwargs.get("path"))
    if not paths:
        return {"status": "FAILED", "error": "No paths provided. Pass one <paths> tag per file."}
    return read_file(path=ensure_list(paths))


@tool
def delete_file(**kwargs) -> Dict[str, Any]:
    """
    Delete ONE file, or an EMPTY folder, inside the project. The user is asked to approve it first.
    To remove a folder that still has files, delete those files first. Cannot delete @ROOT itself.

    Args:
        path (string): The file or empty folder, e.g. '@ROOT/build/old.log'.

    Returns:
        status SUCCESS and the deleted path, or status FAILED with the reason (not found, not empty,
        outside the project, or denied by the user).
    """
    if not (kwargs.get("path") or kwargs.get("filepath")):
        return {"status": "FAILED", "error": "No path provided."}
    try:
        full_path = _resolve_path(kwargs)
        if os.path.abspath(full_path) == os.path.abspath(get_project_root()):
            return {"status": "FAILED", "error": "Refusing to delete the project root."}
        if os.path.islink(full_path) or os.path.isfile(full_path):
            os.remove(full_path)
        elif os.path.isdir(full_path):
            if os.listdir(full_path):
                return {"status": "FAILED", "error": "Directory is not empty. Delete its files first (only empty directories can be removed)."}
            os.rmdir(full_path)
        else:
            return {"status": "FAILED", "error": f"No such file or directory: '{kwargs.get('path')}'"}
        return {"status": "SUCCESS", "path": _sanitize_output_path(full_path)}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}
