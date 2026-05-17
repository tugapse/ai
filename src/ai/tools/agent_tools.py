import os
import subprocess
import json
import difflib
from typing import Dict, Any, List, Optional

PROJECT_ROOT = os.getcwd()

def tool(func):
    """
    Decorator to mark a function as an agent tool.
    This allows the system to discover and register it automatically.
    """
    func._is_tool = True
    return func

# --- INTERNAL HELPERS & NOTIFICATIONS ---
def _resolve_path(params: Dict[str, Any]) -> str:
    """
    Resolves a path with strict type-safety to prevent 'normalize' crashes.
    """
    # 1. Extraction with fallback
    raw_path = params.get("path") or params.get("filepath") or params.get("location") or "."

    # 2. Resilience: If the LLM sent a list or a nested dictionary by mistake
    if isinstance(raw_path, list) and len(raw_path) > 0:
        raw_path = raw_path[0]
    elif isinstance(raw_path, dict):
        # Extract the first string value found in the dict, or default to root
        raw_path = next((v for v in raw_path.values() if isinstance(v, str)), ".")

    # 3. Type Enforcement: Ensure we have a string before calling .replace() or os.path
    if not isinstance(raw_path, str):
        raw_path = str(raw_path) if raw_path is not None else "."

    # 4. Normalization
    normalized = raw_path.replace("@ROOT/", "").replace("@ROOT", ".")
    absolute_target = os.path.abspath(os.path.join(PROJECT_ROOT, normalized))

    # 5. Security Check
    if not absolute_target.startswith(os.path.abspath(PROJECT_ROOT)):
        raise PermissionError(f"Access denied: {raw_path} is outside project boundaries.")
    
    return absolute_target

def _sanitize_output_path(full_path: str) -> str:
    """Converts absolute system paths back into the @ROOT format."""
    try:
        full_path = os.path.abspath(full_path)
        if full_path.startswith(PROJECT_ROOT):
            relative = os.path.relpath(full_path, PROJECT_ROOT)
            return (
                "@ROOT" if relative == "." else f"@ROOT/{relative.replace(os.sep, '/')}"
            )
        return "EXTERNAL_PATH"
    except:
        return "@ROOT/unknown"

def ensure_list(input_val: Any) -> List[str]:
    """Helper to ensure input is a list."""
    if isinstance(input_val, list):
        return input_val
    if isinstance(input_val, str):
        cleaned = input_val.strip()
        if cleaned.startswith("'") and cleaned.endswith("'"):
            cleaned = cleaned[1:-1]
        if cleaned.startswith("[") and cleaned.endswith("]"):
            try:
                return json.loads(cleaned)
            except:
                return [cleaned]
        return [cleaned]
    return []

# --- CORE SYSTEM TOOLS ---

def execute_command(**kwargs) -> Dict[str, Any]:
    """
    Executes a shell command within the project environment.
    
    Use the '@ROOT' token in commands to refer to the absolute path of the project base directory.
    
    Args:
        intent (str): Clear reasoning of why this tool is being called and the expected outcome. Required.
        command (str): The raw shell command to execute. Required.
        path (str): The directory path to run the command in. Defaults to '@ROOT'.
        timeout (int): Maximum execution time in seconds. Defaults to 180.
    """
    command = kwargs.get("command")
    if not command:
        return {"status": "FAILED", "error": "No command provided."}

    actual_root = os.path.abspath(PROJECT_ROOT)
    command = command.replace("@ROOT/", actual_root + "/").replace("@ROOT", actual_root)

    cwd_path = _resolve_path(kwargs)
    timeout = kwargs.get("timeout", 180)

    try:
        process = subprocess.run(
            command, shell=True, cwd=cwd_path,
            capture_output=True, text=True, timeout=timeout
        )
        result = {
            "status": "SUCCESS" if process.returncode == 0 else "FAILED",
            "stdout": process.stdout[-2000:],
            "stderr": process.stderr[-2000:],
            "returncode": process.returncode,
            "command": command,
        }
    except subprocess.TimeoutExpired:
        result = {"status": "FAILED", "error": f"Command timed out after {timeout} seconds."}
    except Exception as e:
        result = {"status": "FAILED", "error": str(e)}

    return result

def read_dir(**kwargs) -> Dict[str, Any]:
    """
    Explores one or more directories and returns a mapped structure of their files and folders.
    
    Use the '@ROOT' token to refer to the absolute path of the project base directory.
    
    Args:
        intent (str): Clear reasoning of why this tool is being called and the expected outcome. Required.
        paths (str | List[str]): A single path string or a list of paths to inspect. Defaults to '@ROOT'.
        depth (int): How many levels deep to recursively list folders. Defaults to 0 (current directory only).
    """
    try:
        path_input = kwargs.get("paths", kwargs.get("path", "@ROOT"))
        paths = ensure_list(path_input)
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

        for p in paths:
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
            if len(paths) == 1:
                error_summary = next(iter(results.values()))
            return {"status": "FAILED", "error": error_summary, "results": results}

        return {"status": "SUCCESS", "results": results}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

def read_file(**kwargs) -> Dict[str, Any]:
    """
    Retrieves the full UTF-8 text content of one or more specific files.
    
    Args:
        intent (str): Clear reasoning of why this tool is being called and the expected outcome. Required.
        paths (str | List[str]): A single file path or a list of file paths to read. Required.
    """
    try:
        path_input = kwargs.get("paths", kwargs.get("path", []))
        paths = ensure_list(path_input)
        
        results = {}
        had_errors = False

        for p in paths:
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
            if len(paths) == 1:
                error_summary = next(iter(results.values()))
            return {"status": "FAILED", "error": error_summary, "files": results}

        return {"status": "SUCCESS", "files": results}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

def write_file(**kwargs) -> Dict[str, Any]:
    """
    Creates a new file or overwrites an existing file with the provided text content.
    Automatically creates necessary parent directories.
    
    Args:
        intent (str): Clear reasoning of why this tool is being called and the expected outcome. Required.
        path (str): The destination file path to write to. Required.
        content (str): The raw text or code to write into the file. MANDATORY: Use the YAML pipe (|) for all multi-line content. Required.
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

def smart_search(**kwargs) -> Dict[str, Any]:
    """
    Searches for a keyword or regex pattern within filenames and file contents.
    Paginates results to prevent context window overflow (50 items per page).
    
    Args:
        intent (str): Clear reasoning of why this tool is being called and the expected outcome. Required.
        pattern (str): The search keyword or regex pattern to look for. Required.
        path (str): The base directory to search within. Defaults to '@ROOT'.
        exclude_dirs (List[str]): Additional directory names to ignore during the search.
        page (int): The page number for paginated results. Defaults to 1.
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
            line.replace(PROJECT_ROOT, "@ROOT").replace(os.sep, "/")
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

def patch_file(**kwargs) -> Dict[str, Any]:
    """
    Surgically replaces a specific block of text within a file without overwriting the entire file.
    
    Args:
        intent (str): Clear reasoning of why this tool is being called and the expected outcome. Required.
        path (str): The exact path to the file to modify. Required.
        search (str): The exact string block currently in the file to find. MANDATORY: Use the YAML pipe (|). Required.
        replace (str): The new string block to insert. MANDATORY: Use the YAML pipe (|). Required.
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

# --- REGISTRY ---
AVAILABLE_TOOLS = {
    "read_dir": read_dir,
    "read_file": read_file,
    "write_file": write_file,
    "patch_file": patch_file,
    "execute_command": execute_command,
    "smart_search": smart_search,
}