import os
import shutil
import subprocess
from typing import Dict, Any, List
import functions as func

PROJECT_ROOT = os.getcwd()

def _resolve_path(params: Dict[str, Any]) -> str:
    """Converts @ROOT or relative paths from the Agent into absolute system paths."""
    for key in ["path", "filepath", "target", "location"]:
        if key in params and isinstance(params[key], str):
            raw = params[key]
            resolved = raw.replace("@ROOT/", "./").replace("@ROOT", ".")
            return os.path.abspath(resolved)
    return PROJECT_ROOT

def _sanitize_output_path(full_path: str) -> str:
    """Converts absolute system paths back into @ROOT format for the LLM."""
    try:
        full_path = os.path.abspath(full_path)
        if full_path.startswith(PROJECT_ROOT):
            relative = os.path.relpath(full_path, PROJECT_ROOT)
            if relative == ".": return "@ROOT"
            return f"@ROOT/{relative.replace(os.sep, '/')}"
        return full_path
    except:
        return full_path

def read_dir(**kwargs) -> Dict[str, Any]:
    """
    Explores the filesystem and returns distinct lists of files and folders in a directory.
    It also provides a peek into the immediate child directories.
    Parameters:
      - path: The directory path to explore (e.g., '@ROOT/src'). Defaults to project root.
    """
    func.log(f"Tool execution: read_dir")
    try:
        path = _resolve_path(kwargs)
        target = os.path.abspath(path)
        if not target.startswith(PROJECT_ROOT):
            return {"status": "FAILED", "error": "Access denied."}

        items = os.listdir(target)
        files = [f for f in items if os.path.isfile(os.path.join(target, f))]
        folders = [f for f in items if os.path.isdir(os.path.join(target, f))]
        
        # --- CHILD DIRECTORY PEEK ---
        structure_peek = {}
        for folder in folders:
            folder_path = os.path.join(target, folder)
            try:
                sub_items = os.listdir(folder_path)
                structure_peek[folder] = {
                    "files": [f for f in sub_items if os.path.isfile(os.path.join(folder_path, f))],
                    "subfolders": [f for f in sub_items if os.path.isdir(os.path.join(folder_path, f))]
                }
            except:
                structure_peek[folder] = "Hidden/Unreadable"

        sanitized_path = _sanitize_output_path(target)
        func.log(f"Read directory success: {sanitized_path}")
        return {
            "status": "SUCCESS",
            "current_dir": sanitized_path,
            "files": files,
            "folders": folders,
            "sub_directory_contents": structure_peek
        }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

def smart_search(**kwargs) -> Dict[str, Any]:
    """
    Finds files using keyword or regex search. Checks both filenames and file content.
    Parameters:
      - pattern: The string or regex pattern to search for (e.g., "auth", "*.py").
      - path: (Optional) The directory to start the search from. Defaults to project root.
    """
    func.log(f"Tool execution: smart_search")
    try:
        full_path = _resolve_path(kwargs)
        raw_pattern = kwargs.get("pattern") or kwargs.get("search")
        
        if isinstance(raw_pattern, list):
            raw_pattern = raw_pattern[0] if raw_pattern else ""
        
        if not raw_pattern or not isinstance(raw_pattern, str):
            return {"status": "FAILED", "error": "No valid search pattern provided."}
            
        pattern = raw_pattern.strip("*").replace("*", ".*")
        results = {"matched_filenames": [], "matched_content": []}
        
        # Filename Search
        for root, dirs, files in os.walk(full_path):
            for name in dirs + files:
                if pattern.lower().replace(".*", "") in name.lower():
                    results["matched_filenames"].append(_sanitize_output_path(os.path.join(root, name)))

        # Content Search
        grep_cmd = ["grep", "-E", "-n", "-i", "-r", "-H", "-C", "1", "-I", pattern, full_path]
        grep_res = subprocess.run(grep_cmd, capture_output=True, text=True)
        if grep_res.returncode <= 1:
            results["matched_content"] = [
                line.replace(PROJECT_ROOT, "@ROOT").replace(os.sep, "/") 
                for line in grep_res.stdout.splitlines()[:50]
            ]

        return {"status": "SUCCESS", **results}
    except Exception as e:
        func.error(f"smart_search failed: {e}")
        return {"status": "FAILED", "error": str(e)}

def read_file(**kwargs) -> Dict[str, Any]:
    """
    Reads the exact content of a specific file.
    Parameters:
      - path: Absolute or relative file path to read (e.g., '@ROOT/src/main.py').
    """
    try:
        full_path = _resolve_path(kwargs)
        with open(full_path, 'r', encoding='utf-8') as f:
            return {"status": "SUCCESS", "content": f.read(), "path": _sanitize_output_path(full_path)}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

def write_file(**kwargs) -> Dict[str, Any]:
    """
    Creates or overwrites a file with the provided content.
    Parameters:
      - path: Absolute or relative file path to write to.
      - content: The exact string content or code to write into the file. Must be properly escaped.
    """
    try:
        full_path = _resolve_path(kwargs)
        content = kwargs.get("content") or kwargs.get("code") or ""
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"status": "SUCCESS", "path": _sanitize_output_path(full_path)}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

def grep_file(**kwargs) -> Dict[str, Any]:
    """
    Searches for a specific pattern within a single file, returning matching lines with context.
    Parameters:
      - path: The file to search inside.
      - pattern: The regex or string pattern to look for.
    """
    try:
        full_path = _resolve_path(kwargs)
        pattern = kwargs.get("pattern") or kwargs.get("search")
        if isinstance(pattern, list): pattern = pattern[0]
        
        cmd = ["grep", "-E", "-n", "-i", "-C", "2", "-H", pattern, full_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        sanitized = [l.replace(PROJECT_ROOT, "@ROOT").replace(os.sep, "/") for l in res.stdout.splitlines()[:50]]
        return {"status": "SUCCESS", "results": sanitized}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

AVAILABLE_TOOLS = {
    "read_dir": read_dir, "read_file": read_file, "write_file": write_file,
    "grep_file": grep_file, "smart_search": smart_search
}