import os
import shutil
import subprocess
import requests
import json
from typing import Dict, Any, List, Optional
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
    Provides a structural overview of immediate child items.
    Parameters:
      - path: The directory path to explore (e.g., '@ROOT/src' or '@ROOT'). Defaults to project root.
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
    Finds files using keyword or regex search. Inspects both names and content.
    Parameters:
      - pattern: The string or regex pattern to search for (e.g., "config", "index.*").
      - path: (Optional) The directory to start searching from. Defaults to project root.
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
        
        for root, dirs, files in os.walk(full_path):
            for name in dirs + files:
                if pattern.lower().replace(".*", "") in name.lower():
                    results["matched_filenames"].append(_sanitize_output_path(os.path.join(root, name)))

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
    Retrieves the full text content of a specific file.
    Parameters:
      - path: Absolute or relative file path to read (e.g., '@ROOT/README.md').
    """
    func.log(f"Tool execution: read_file")
    try:
        full_path = _resolve_path(kwargs)
        with open(full_path, 'r', encoding='utf-8') as f:
            return {"status": "SUCCESS", "content": f.read(), "path": _sanitize_output_path(full_path)}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

def read_files(**kwargs) -> Dict[str, Any]:
    """
    Retrieves the full text content of multiple files at once.
    Parameters:
      - paths: A list of absolute or relative file paths to read (e.g., ['@ROOT/README.md', '@ROOT/src/main.py']).
    """
    func.log("Tool execution: read_files")
    paths = kwargs.get("paths") or kwargs.get("files")
    
    if not paths:
        return {"status": "FAILED", "error": "No paths provided. Expected a list of file paths."}
        
    if not isinstance(paths, list):
        if isinstance(paths, str):
            paths = [paths]
        else:
            return {"status": "FAILED", "error": "The 'paths' parameter must be a list of strings."}

    contents = {}
    errors = {}
    for p in paths:
        try:
            full_path = _resolve_path({"path": p})
            with open(full_path, 'r', encoding='utf-8') as f:
                contents[_sanitize_output_path(full_path)] = f.read()
        except Exception as e:
            errors[p] = str(e)

    if not contents:
        return {"status": "FAILED", "error": "Could not read any of the requested files.", "details": errors}

    response = {"status": "SUCCESS", "contents": contents}
    if errors:
        response["errors"] = errors
        
    return response

def write_file(**kwargs) -> Dict[str, Any]:
    """
    Creates or overwrites a file with the provided content.
    Parameters:
      - path: Absolute or relative file path to write to.
      - content: The exact data or source code to write into the file.
    """
    func.log(f"Tool execution: write_file")
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
    Searches for a specific pattern within a single file, returning matching lines with surrounding context.
    Parameters:
      - path: The file path to search inside.
      - pattern: The regex or text pattern to look for.
    """
    func.log(f"Tool execution: grep_file")
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

def web_search(**kwargs) -> Dict[str, Any]:
    """
    Performs a live web search to retrieve real-time data, news, or technical documentation.
    Parameters:
      - query: The search query string.
      - max_results: (Optional) Maximum number of snippets to return (default 5).
    """
    func.log(f"Tool execution: web_search")
    query = kwargs.get("query") or kwargs.get("search")
    max_results = kwargs.get("max_results", 5)

    if not query:
        return {"status": "FAILED", "error": "No search query provided."}

    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            func.debug(f"Web search success: {query}")
            return {"status": "SUCCESS", "results": results}
    except ImportError:
        return {"status": "FAILED", "error": "Search dependency missing. Run 'pip install ddgs'."}
    except Exception as e:
        func.error(f"web_search failed: {e}")
        return {"status": "FAILED", "error": str(e)}

def web_read(**kwargs) -> Dict[str, Any]:
    """
    Extracts the full text content from a URL in clean Markdown. Optimized for dynamic apps and documentation.
    Parameters:
      - url: The full web address to read.
      - wait_for: (Optional) UI element selector to wait for before extraction (e.g., 'main' or '#root').
      - timeout: (Optional) Max seconds to wait for page rendering (default 15).
    """
    func.log(f"Tool execution: web_read")
    url = kwargs.get("url") or kwargs.get("link")
    wait_selector = kwargs.get("wait_for")
    timeout = kwargs.get("timeout", 15)

    if not url:
        return {"status": "FAILED", "error": "No URL provided."}

    headers = {
        "Accept": "application/json",
        "X-Timeout": str(timeout),
        "X-Wait-For-Selector": wait_selector if wait_selector else ""
    }

    try:
        response = requests.get(f"https://r.jina.ai/{url}", headers=headers, timeout=timeout + 5)
        response.raise_for_status()
        
        data = response.json()
        result_data = data.get("data", {})
        content = result_data.get("content", "")
        
        func.log(f"Web read success: {result_data.get('title', url)}")
        
        return {
            "status": "SUCCESS", 
            "content": content[:9000], 
            "title": result_data.get("title"),
            "url": url
        }
    except Exception as e:
        func.error(f"web_read failed: {e}")
        return {"status": "FAILED", "error": str(e)}

AVAILABLE_TOOLS = {
    "read_dir": read_dir, 
    "read_file": read_file, 
    "read_files": read_files,
    "write_file": write_file,
    "grep_file": grep_file, 
    "smart_search": smart_search,
    "web_search": web_search,
    "web_read": web_read
}