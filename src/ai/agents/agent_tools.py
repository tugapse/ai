import os
import shutil
import subprocess
import requests
import json
import difflib
from typing import Dict, Any, List, Optional
import functions as func

PROJECT_ROOT = os.getcwd()

# --- INTERNAL HELPERS & NOTIFICATIONS ---


def send_notification(**kwargs) -> Dict[str, Any]:
    """
    Sends a desktop notification to the user via the system's notify-send utility.
    Use this to alert the human when a task is completed, if a critical error occurs,
    or if an agent is waiting for manual input/clarification.
    Parameters:
      - title: The headline of the notification (e.g., 'Task Complete').
      - message: The descriptive body text of the alert.
      - urgency: (Optional) 'low', 'normal', or 'critical'. Affects persistence.
      - icon: (Optional) System icon name (default: 'dialog-information').
      - timeout: (Optional) Milliseconds to display the alert (default: 5000).
    """
    title = kwargs.get("title", "Agent Notification")
    message = kwargs.get("message", "")
    urgency = kwargs.get("urgency", "normal")
    icon = kwargs.get("icon", "dialog-information")
    timeout = kwargs.get("timeout", 5000)

    command = ["notify-send", title, message, "-u", urgency, "-i", icon, "-t", str(timeout)]
    try:
        subprocess.run(command, check=True)
        return {"status": "SUCCESS", "message": "Notification sent successfully."}
    except FileNotFoundError:
        return {
            "status": "FAILED",
            "error": "notify-send not found. Install 'libnotify'.",
        }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


def _resolve_path(params: Dict[str, Any]) -> str:
    raw_path = params.get("path") or params.get("filepath") or params.get("location") or "."
    
    # 1. Clean up the @ROOT alias
    normalized = raw_path.replace("@ROOT/", "").replace("@ROOT", ".")
    
    # 2. ANCHOR the path to the PROJECT_ROOT (This is the missing piece)
    # This ensures that even if normalized is '.', it becomes 'sandbox/.'
    absolute_target = os.path.abspath(os.path.join(PROJECT_ROOT, normalized))

    # 3. Security Check
    if not absolute_target.startswith(os.path.abspath(PROJECT_ROOT)):
        # (Optional: send_notification here)
        raise PermissionError(f"Access denied: {raw_path} is outside project boundaries.")
    
    return absolute_target


def _sanitize_output_path(full_path: str) -> str:
    """
    Converts absolute system paths back into the @ROOT format for the LLM.
    Ensures that the agent always sees paths relative to the project base.
    """
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


# --- CORE SYSTEM TOOLS ---


def execute_command(**kwargs) -> Dict[str, Any]:
    """Executes a shell command with @ROOT interpolation."""
    command = kwargs.get("command")
    if not command:
        return {"status": "FAILED", "error": "No command provided."}

    # --- ADD THIS LOGIC ---
    # Convert @ROOT to the actual system path within the command string
    actual_root = os.path.abspath(PROJECT_ROOT)
    command = command.replace("@ROOT/", actual_root + "/").replace("@ROOT", actual_root)
    # ----------------------

    cwd_path = _resolve_path(kwargs)
    timeout = kwargs.get("timeout", 60)

    try:
        process = subprocess.run(
            command, shell=True, cwd=cwd_path,
            capture_output=True, text=True, timeout=timeout
        )
        return {
            "status": "SUCCESS" if process.returncode == 0 else "FAILED",
            "stdout": process.stdout[-2000:],
            "stderr": process.stderr[-2000:],
            "returncode": process.returncode,
            "command": command, # Useful for debugging
        }
    except subprocess.TimeoutExpired:
        return {"status": "FAILED", "error": f"Command timed out after {timeout} seconds."}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

# --- FILESYSTEM & RESEARCH TOOLS ---


def read_dir(**kwargs) -> Dict[str, Any]:
    """
    Explores a directory and returns its contents. 
    Can peek into subdirectories to provide deeper architectural context in one call.
    Parameters:
      - path: The directory path to explore (e.g., '@ROOT/src'). Defaults to @ROOT.
      - depth: (Optional) How many levels to peek into subfolders. Default is 0 (just current dir).
               Max recommended depth is 1 or 2 to avoid token overflow.
    """
    try:
        target = _resolve_path(kwargs)
        depth = int(kwargs.get("depth", 0))
        
        def get_structure(current_path, current_depth):
            items = os.listdir(current_path)
            res = {
                "files": [f for f in items if os.path.isfile(os.path.join(current_path, f))],
                "folders": {}
            }
            
            # If we still have depth, crawl the folders
            found_folders = [d for d in items if os.path.isdir(os.path.join(current_path, d))]
            
            for d in found_folders:
                full_d_path = os.path.join(current_path, d)
                if current_depth > 0:
                    # Recursive peek
                    res["folders"][d] = get_structure(full_d_path, current_depth - 1)
                else:
                    # Just list the folder name
                    res["folders"][d] = "[Sub-entries hidden. Increase depth to see.]"
            return res

        structure = get_structure(target, depth)
        
        return {
            "status": "SUCCESS",
            "path": _sanitize_output_path(target),
            "structure": structure,
        }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

def read_file(**kwargs) -> Dict[str, Any]:
    """
    Retrieves the full UTF-8 text content of a specific file.
    Parameters:
      - path: The relative or @ROOT path to the file.
    """
    try:
        full_path = _resolve_path(kwargs)
        with open(full_path, "r", encoding="utf-8") as f:
            return {
                "status": "SUCCESS",
                "content": f.read(),
                "path": _sanitize_output_path(full_path),
            }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


def write_file(**kwargs) -> Dict[str, Any]:
    """
    Creates or overwrites a file with the provided content.
    Strictly Atomic: Only handles one file per call.
    Parameters:
      - path: Target path for the file.
      - content: The full string/source code to be written.
    """
    try:
        full_path = _resolve_path(kwargs)
        content = kwargs.get("content") or ""
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        sanitized = _sanitize_output_path(full_path)
        send_notification(title="File Written", message=f"Saved: {sanitized}")
        return {"status": "SUCCESS", "path": sanitized}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}



def smart_search(**kwargs) -> Dict[str, Any]:
    """
    Searches for a keyword or regex pattern in both filenames and file contents.
    
    Parameters:
      - pattern (str): The string or regex pattern to search for (e.g., "api_key", "def test_.*").
      - path (str, optional): The directory to search inside. Defaults to the project root.
      - exclude_dirs (list of str, optional): An array of folder names to strictly exclude from 
        the search (e.g. ["tests", "legacy_code"]).
      - page (int, optional): The page number for results. Results are limited to 50 per page.
    """
    import os
    import re
    import subprocess
    import math
    from typing import Any, Dict
    
    func.log("Tool execution: smart_search")
    try:
        full_path = _resolve_path(kwargs)
        raw_pattern = kwargs.get("pattern") or kwargs.get("search")

        if isinstance(raw_pattern, list):
            raw_pattern = raw_pattern[0] if raw_pattern else ""

        if not raw_pattern or not isinstance(raw_pattern, str):
            return {"status": "FAILED", "error": "No valid search pattern provided."}

        # --- Strict Exclusion Setup ---
        raw_exclude = kwargs.get("exclude_dirs", [])
        if not isinstance(raw_exclude, list):
            raw_exclude = [str(raw_exclude)]
            
        # Hardcoded defaults to prevent freezing on massive third-party folders
        default_excludes = [".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"]
        
        # Combine user inputs with defaults and ensure they are valid strings
        exclude_list = list(set(default_excludes + [str(e).strip() for e in raw_exclude if e]))

        def is_excluded(path_string: str) -> bool:
            """
            Strictly checks if any excluded folder exists in the given path.
            Formats strings with surrounding slashes to prevent false partial matches 
            (e.g., preventing "venv" from blocking "my_venv_file.py").
            """
            normalized_path = "/" + path_string.replace(os.sep, "/").strip("/") + "/"
            for ex in exclude_list:
                clean_ex = ex.replace(os.sep, "/").strip("/")
                if f"/{clean_ex}/" in normalized_path:
                    return True
            return False

        # --- Pagination Setup ---
        try:
            page = int(kwargs.get("page", 1))
            page = max(1, page)
        except (ValueError, TypeError):
            page = 1
            
        PAGE_SIZE = 50
        start_idx = (page - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE

        # Prepare pattern for regex
        pattern_str = raw_pattern
        if "*" in pattern_str and not any(c in pattern_str for c in "(|)"):
            pattern_str = pattern_str.replace("*", ".*")

        all_matched_filenames = []

        # 1. Filename & Directory Search (Python os.walk)
        regex_compiled = None
        try:
            regex_compiled = re.compile(pattern_str, re.IGNORECASE)
        except re.error:
            pass # We will fallback to literal match below

        literal_pattern = raw_pattern.lower().replace(".*", "").replace("*", "")

        for root, dirs, files in os.walk(full_path):
            # THE HARD WAY: Modify dirs in-place. If we remove a folder from 'dirs' here, 
            # os.walk completely ignores it and will not search inside it.
            dirs[:] = [d for d in dirs if not is_excluded(os.path.join(root, d))]
            
            # Search both the valid directories AND files for the name match
            for name in dirs + files:
                full_item_path = os.path.join(root, name)
                
                # Double check the item itself isn't excluded
                if not is_excluded(full_item_path):
                    match_found = False
                    if regex_compiled and regex_compiled.search(name):
                        match_found = True
                    elif literal_pattern in name.lower():
                        match_found = True
                        
                    if match_found:
                        all_matched_filenames.append(_sanitize_output_path(full_item_path))


        # 2. Content search (Grep)
        grep_cmd = ["grep", "-E", "-n", "-i", "-r", "-H", "-C", "1", "-I"]
        
        # Pass exclusions to grep so it runs fast natively
        for ex in exclude_list:
            if "/" not in ex and "\\" not in ex: # grep natively prefers base folder names
                grep_cmd.append(f"--exclude-dir={ex}")
                
        grep_cmd.extend([raw_pattern, full_path])
        
        grep_res = subprocess.run(grep_cmd, capture_output=True, text=True)
        
        all_raw_lines = []
        if grep_res.returncode <= 1:
            for line in grep_res.stdout.splitlines():
                # Extract just the file path from grep's output string 
                # Output format is usually /path/to/file:line_num:content
                filepath_part = line.split(":")[0].split("-")[0]
                
                # THE HARD WAY: Double-filter grep's output. If grep's native exclude 
                # failed for some OS-specific reason, Python catches and destroys it here.
                if not is_excluded(filepath_part):
                    all_raw_lines.append(line)

        # --- Apply Pagination ---
        total_file_matches = len(all_matched_filenames)
        total_content_matches = len(all_raw_lines)
        
        file_pages = math.ceil(total_file_matches / PAGE_SIZE)
        content_pages = math.ceil(total_content_matches / PAGE_SIZE)
        total_pages = max(1, max(file_pages, content_pages))

        # Slice the results for the current page
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
                "showing_results": f"{start_idx + 1} to {min(end_idx, max(total_file_matches, total_content_matches))}"
            },
            "matched_filenames": paginated_filenames,
            "matched_content": paginated_content
        }

    except Exception as e:
        func.error(f"smart_search failed: {e}")
        return {"status": "FAILED", "error": str(e)}
    
    
def patch_file(**kwargs) -> Dict[str, Any]:
    """
    Surgically replaces a block of text within a file.
    Use this to modify specific functions or lines without overwriting the whole file.
    Parameters:
      - path: Target path for the file.
      - search: The exact snippet of text to be replaced.
      - replace: The new text to insert.
    """
    try:
        full_path = _resolve_path(kwargs)
        search_block = kwargs.get("search")
        replace_block = kwargs.get("replace")

        if not search_block or replace_block is None:
            return {
                "status": "FAILED",
                "error": "Both 'search' and 'replace' parameters are required.",
            }

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        if search_block not in content:
            return {
                "status": "FAILED",
                "error": "The 'search' block was not found exactly as provided in the file. Check indentation and spacing.",
            }

        # Perform the replacement
        new_content = content.replace(
            search_block, replace_block, 1
        )  # Only replace first occurrence for safety

        # Generate a small diff for the notification/log
        diff = list(
            difflib.unified_diff(
                content.splitlines(),
                new_content.splitlines(),
                fromfile="original",
                tofile="patched",
                lineterm="",
            )
        )

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        sanitized = _sanitize_output_path(full_path)
        send_notification(
            title="File Patched",
            message=f"Applied changes to {sanitized}",
            urgency="low",
        )

        return {
            "status": "SUCCESS",
            "path": sanitized,
            "diff_summary": "\n".join(diff[:10]) + ("\n..." if len(diff) > 10 else ""),
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
    "send_notification": send_notification,
    "smart_search": smart_search,
}
