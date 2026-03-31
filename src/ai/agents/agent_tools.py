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
    """
    Converts @ROOT or relative paths into absolute system paths.
    Validates that the target path stays within the PROJECT_ROOT to prevent
    directory traversal attacks. Handles various parameter keys (path, file, etc.).
    """
    raw_path = (
        params.get("path") or params.get("filepath") or params.get("location") or "."
    )
    normalized = raw_path.replace("@ROOT/", "./").replace("@ROOT", ".")
    absolute_target = os.path.abspath(normalized)

    if not absolute_target.startswith(PROJECT_ROOT):
        send_notification(
            title="SECURITY ALERT",
            message=f"Agent attempted to access forbidden path: {raw_path}",
            urgency="critical",
        )
        func.error(f"Security Block: {absolute_target}")
        raise PermissionError(
            f"Access denied: {raw_path} is outside project boundaries."
        )
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
    """
    Executes a shell command on the local system. This is a powerful 'Cowboy' tool.
    Use this for installing dependencies, running tests, or building the project.
    Parameters:
      - command: The full shell command string to execute (e.g., 'npm install').
      - path: (Optional) The directory to execute the command in (cwd). Defaults to @ROOT.
      - timeout: (Optional) Max seconds to wait for execution (default: 60).
    """
    command = kwargs.get("command")
    cwd_path = _resolve_path(kwargs)
    timeout = kwargs.get("timeout", 60)

    if not command:
        return {"status": "FAILED", "error": "No command provided."}

    try:
        process = subprocess.run(
            command, shell=True, cwd=cwd_path,
            capture_output=True, text=True, timeout=timeout
        )
        return {
            "status": "SUCCESS" if process.returncode == 0 else "FAILED",
            "stdout": process.stdout[-2000:],  # Return the tail for LLM context
            "stderr": process.stderr[-2000:],
            "returncode": process.returncode,
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "FAILED",
            "error": f"Command timed out after {timeout} seconds.",
        }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


# --- FILESYSTEM & RESEARCH TOOLS ---


def read_dir(**kwargs) -> Dict[str, Any]:
    """
    Explores a directory and returns lists of its child files and folders.
    Use this for project reconnaissance and mapping the file structure.
    Parameters:
      - path: The directory path to explore (e.g., '@ROOT/src'). Defaults to @ROOT.
    """
    try:
        target = _resolve_path(kwargs)
        items = os.listdir(target)
        return {
            "status": "SUCCESS",
            "current_dir": _sanitize_output_path(target),
            "files": [f for f in items if os.path.isfile(os.path.join(target, f))],
            "folders": [f for f in items if os.path.isdir(os.path.join(target, f))],
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
                    results["matched_filenames"].append(
                        _sanitize_output_path(os.path.join(root, name))
                    )

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
