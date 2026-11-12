"""Filesystem tools: list, read, write, patch and delete project files."""

import os
import difflib
from typing import Any, Dict

from ai.tools.base import tool, resolve_path as _resolve_path, sanitize_output_path as _sanitize_output_path, ensure_list, get_project_root


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
    Read the full text of a file. For several files use read_files; to find something in a big
    file without reading all of it use grep_file.

    Args:
        path (list): File like '@ROOT/src/app.py'. Repeat the <path> tag to read several files.

    Returns:
        files: {path: content}. If a file cannot be read, status is FAILED and its entry holds the error.
    """
    try:
        path_input = kwargs.get("path")
        path = ensure_list(path_input)
        
        results = {}
        had_errors = False

        for p in path:
            try:
                full_path = _resolve_path({"path": p})
                if not os.path.isfile(full_path):
                    raise FileNotFoundError(f"No such file: '{p}'")
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    sanitized_path = _sanitize_output_path(full_path)
                    results[sanitized_path] = content
            except Exception as e:
                results[p] = f"FAILED: {str(e)}"
                had_errors = True
        
        if had_errors:
            error_summary = "One or more files could not be read."
            if len(path) == 1:
                error_summary = next(iter(results.values()))
            return {"status": "FAILED", "error": error_summary, "files": results}

        return {"status": "SUCCESS", "files": results}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

@tool
def write_file(**kwargs) -> Dict[str, Any]:
    """
    Create a file, or REPLACE an existing file's whole content. Missing folders are created.
    To change only part of an existing file, use patch_file instead (it keeps the rest intact).

    Args:
        path (string): Destination file like '@ROOT/src/app.py'.
        content (string): The complete file content. Wrap it in <![CDATA[ ... ]]> so code with <, > or & is kept exactly.

    Returns:
        status SUCCESS and the written path, or status FAILED with the reason.
    """
    try:
        full_path = _resolve_path(kwargs)
        content = kwargs.get("content") or ""
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        sanitized = _sanitize_output_path(full_path)
        return {"status": "SUCCESS", "path": sanitized}
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

    Returns:
        status SUCCESS and diff_summary (a short unified diff). FAILED if the search block is not
        found (check indentation/whitespace) or is not unique (include more context).
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

        if search_normalized not in content_normalized:
            return {"status": "FAILED", "error": "The 'search' block was not found. Check indentation."}

        if content_normalized.count(search_normalized) > 1:
            return {"status": "FAILED", "error": "The 'search' block is not unique. Provide more context."}

        new_content = content_normalized.replace(search_normalized, replace_normalized, 1)
        diff = list(difflib.unified_diff(
            content_normalized.splitlines(), new_content.splitlines(),
            fromfile="original", tofile="patched", lineterm=""
        ))

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return {
            "status": "SUCCESS",
            "path": _sanitize_output_path(full_path),
            "diff_summary": "\n".join(diff[:15]) + ("\n..." if len(diff) > 15 else ""),
        }
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
