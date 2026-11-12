"""Search tools: find files and content across the project, or inside one file."""

import os
import re
import subprocess
from typing import Any, Dict, List

from ai.tools.base import tool, resolve_path as _resolve_path, sanitize_output_path as _sanitize_output_path, ensure_list, get_project_root


@tool
def smart_search(**kwargs) -> Dict[str, Any]:
    """
    Search the whole project (or one folder) for a word or regex, in file NAMES and file CONTENTS.
    Use it to find where something is defined or used. To search inside one known file use grep_file.

    Args:
        pattern (string): Word or regex, e.g. 'load_config' or 'class .*Manager'. Case-insensitive.
        path (string, optional): Folder to search, e.g. '@ROOT/src'. Default '@ROOT'.
        exclude_dirs (list, optional): Extra folder names to skip. Repeat the tag per folder. .git, node_modules, venv, dist, build are always skipped.
        page (int, optional): Results come 50 per page. Default 1.

    Returns:
        matched_filenames (paths whose name matches), matched_content (grep lines 'path:line:text' with
        one line of context), and pagination. If the last line says 'Call tool again with page=N',
        request that page to see more.
    """
    import re
    import math
    
    try:
        full_path = _resolve_path(kwargs)
        raw_pattern = kwargs.get("pattern") or kwargs.get("search")

        if isinstance(raw_pattern, list):
            raw_pattern = raw_pattern[0] if raw_pattern else ""

        if not raw_pattern or not isinstance(raw_pattern, str):
            return {"status": "FAILED", "error": "No valid search pattern provided."}

        raw_exclude = kwargs.get("exclude_dirs", [])
        if not isinstance(raw_exclude, list):
            raw_exclude = [str(raw_exclude)]
            
        default_excludes = [".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"]
        exclude_list = list(set(default_excludes + [str(e).strip() for e in raw_exclude if e]))

        def is_excluded(path_string: str) -> bool:
            normalized_path = "/" + path_string.replace(os.sep, "/").strip("/") + "/"
            for ex in exclude_list:
                clean_ex = ex.replace(os.sep, "/").strip("/")
                if f"/{clean_ex}/" in normalized_path:
                    return True
            return False

        try:
            page = int(kwargs.get("page", 1))
            page = max(1, page)
        except (ValueError, TypeError):
            page = 1
            
        PAGE_SIZE = 50
        start_idx = (page - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE

        pattern_str = raw_pattern
        if "*" in pattern_str and not any(c in pattern_str for c in "(|)"):
            pattern_str = pattern_str.replace("*", ".*")

        all_matched_filenames = []
        regex_compiled = None
        try:
            regex_compiled = re.compile(pattern_str, re.IGNORECASE)
        except re.error:
            pass

        literal_pattern = raw_pattern.lower().replace(".*", "").replace("*", "")

        for root, dirs, files in os.walk(full_path):
            dirs[:] = [d for d in dirs if not is_excluded(os.path.join(root, d))]
            for name in dirs + files:
                full_item_path = os.path.join(root, name)
                if not is_excluded(full_item_path):
                    match_found = False
                    if regex_compiled and regex_compiled.search(name):
                        match_found = True
                    elif literal_pattern in name.lower():
                        match_found = True
                    if match_found:
                        all_matched_filenames.append(_sanitize_output_path(full_item_path))

        grep_cmd = ["grep", "-E", "-n", "-i", "-r", "-H", "-C", "1", "-I"]
        for ex in exclude_list:
            if "/" not in ex and "\\" not in ex:
                grep_cmd.append(f"--exclude-dir={ex}")
        grep_cmd.extend([raw_pattern, full_path])
        
        grep_res = subprocess.run(grep_cmd, capture_output=True, text=True)
        all_raw_lines = []
        if grep_res.returncode <= 1:
            for line in grep_res.stdout.splitlines():
                filepath_part = line.split(":")[0].split("-")[0]
                if not is_excluded(filepath_part):
                    all_raw_lines.append(line)

        total_file_matches = len(all_matched_filenames)
        total_content_matches = len(all_raw_lines)
        total_pages = max(1, math.ceil(max(total_file_matches, total_content_matches) / PAGE_SIZE))

        paginated_filenames = all_matched_filenames[start_idx:end_idx]
        paginated_content = [
            line.replace(get_project_root(), "@ROOT").replace(os.sep, "/")
            for line in all_raw_lines[start_idx:end_idx]
        ]

        if page < total_pages:
            paginated_content.append(f"... [End of Page {page}. Call tool again with page={page + 1} to see more] ...")

        return {
            "status": "SUCCESS",
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_filename_matches": total_file_matches,
                "total_content_matches": total_content_matches,
            },
            "matched_filenames": paginated_filenames,
            "matched_content": paginated_content
        }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


@tool
def grep_file(**kwargs) -> Dict[str, Any]:
    """
    Find lines in ONE file that match a regex or plain text, with line numbers and nearby lines.
    Use it to locate code in a big file instead of reading the whole file. To search many files,
    use smart_search. Before patch_file, copy the exact matched lines into its 'search' value.

    Args:
        path (string): The file to search, e.g. '@ROOT/src/app.py'.
        pattern (string): Regex or plain text, e.g. 'def load_' or 'TODO'.
        context (int, optional): Lines shown before and after each match. Default 2.
        ignore_case (bool, optional): 'true' or 'false'. Default 'true'.
        max_matches (int, optional): Stop after this many matches. Default 50.

    Returns:
        total_matches and output in grep format: '12:matched line', '11-nearby line', and '--' between
        separate places. 'No matches.' when nothing is found.
    """
    pattern = kwargs.get("pattern") or kwargs.get("search")
    if isinstance(pattern, list):
        pattern = pattern[0] if pattern else ""
    if not pattern:
        return {"status": "FAILED", "error": "No pattern provided."}
    try:
        full_path = _resolve_path(kwargs)
        if not os.path.isfile(full_path):
            return {"status": "FAILED", "error": f"No such file: '{kwargs.get('path')}'"}

        def as_int(name, default, low, high):
            try:
                return max(low, min(high, int(kwargs.get(name, default))))
            except (TypeError, ValueError):
                return default

        context = as_int("context", 2, 0, 20)
        max_matches = as_int("max_matches", 50, 1, 500)
        ignore_case = str(kwargs.get("ignore_case", "true")).strip().lower() not in ("false", "0", "no")
        flags = re.IGNORECASE if ignore_case else 0
        try:
            regex = re.compile(pattern, flags)
        except re.error:
            regex = re.compile(re.escape(pattern), flags)

        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()

        hits = [i for i, line in enumerate(lines) if regex.search(line)]
        shown = hits[:max_matches]
        shown_set = set(shown)
        out: List[str] = []
        last_printed = -2
        for i in shown:
            start, end = max(0, i - context), min(len(lines), i + context + 1)
            if out and start > last_printed + 1:
                out.append("--")
            for j in range(max(start, last_printed + 1), end):
                out.append(f"{j + 1}{':' if j in shown_set else '-'}{lines[j]}")
            last_printed = end - 1
        if len(hits) > max_matches:
            out.append(f"... {len(hits) - max_matches} more matches (raise max_matches to see them)")

        return {
            "status": "SUCCESS",
            "path": _sanitize_output_path(full_path),
            "total_matches": len(hits),
            "output": "\n".join(out) if out else "No matches.",
        }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}
