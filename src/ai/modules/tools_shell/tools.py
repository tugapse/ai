"""Shell tool: run non-interactive commands in the project."""

import os
import subprocess
from typing import Any, Dict

from ai.tools.base import tool, resolve_path as _resolve_path, sanitize_output_path as _sanitize_output_path, ensure_list, get_project_root


@tool
def execute_command(**kwargs) -> Dict[str, Any]:
    """
    Run a shell command in the project and get its output (tests, git, build tools, scripts).
    The user may be asked to approve it first.
    Commands run WITHOUT a terminal (no keyboard input): never start interactive programs such as
    editors, pagers, REPLs, or password and y/N prompts. Use non-interactive flags instead, e.g.
    'git commit -m "msg"', 'git --no-pager log', 'apt-get -y', 'npm init -y'.

    Args:
        command (string): The shell command. '@ROOT' is replaced with the project folder.
        path (string, optional): Folder to run it in, e.g. '@ROOT/frontend'. Default '@ROOT'.
        timeout (int, optional): Seconds before the command is stopped. Default 180.

    Returns:
        returncode, stdout and stderr (the last 2000 characters of each). status is SUCCESS only when
        returncode is 0. A timeout error usually means the command was waiting for input.
    """
    command = kwargs.get("command")
    if not command:
        return {"status": "FAILED", "error": "No command provided."}

    actual_root = os.path.abspath(get_project_root())
    command = command.replace("@ROOT/", actual_root + "/").replace("@ROOT", actual_root)

    cwd_path = _resolve_path(kwargs)
    timeout = kwargs.get("timeout", 180)

    try:
        stdout, stderr, returncode = _run_non_interactive(command, cwd_path, timeout)
        result = {
            "status": "SUCCESS" if returncode == 0 else "FAILED",
            "stdout": stdout[-2000:],
            "stderr": stderr[-2000:],
            "returncode": returncode,
            "command": command,
        }
    except subprocess.TimeoutExpired:
        result = {
            "status": "FAILED",
            "error": (
                f"Command timed out after {timeout} seconds. Commands run without a terminal: "
                "avoid interactive programs (editors, pagers, prompts); pass flags such as -y, -m or --no-pager."
            ),
        }
    except Exception as e:
        result = {"status": "FAILED", "error": str(e)}

    return result


# Environment that keeps common tools from waiting on a human.
_NON_INTERACTIVE_ENV = {
    "PAGER": "cat",
    "GIT_PAGER": "cat",
    "GIT_TERMINAL_PROMPT": "0",   # no git credential prompts
    "GIT_EDITOR": "true",         # `git commit` without -m aborts instead of opening an editor
    "DEBIAN_FRONTEND": "noninteractive",
    "PIP_NO_INPUT": "1",
    "CI": "1",
}


def _run_non_interactive(command: str, cwd: str, timeout: float):
    """
    Runs a shell command fully detached from the user's terminal.

    The agent UI owns the terminal, so a child that reads it (editor, pager,
    sudo/ssh password prompt, "continue? [y/N]") would block forever and steal
    keystrokes. stdin is closed, the child gets its own session (no controlling
    terminal, so /dev/tty cannot be opened), and on timeout the whole process
    group is killed, not just the shell.

    Returns:
        (stdout, stderr, returncode)

    Raises:
        subprocess.TimeoutExpired: If the command does not finish in time.
    """
    env = os.environ.copy()
    env.update(_NON_INTERACTIVE_ENV)

    popen_kwargs: Dict[str, Any] = dict(
        shell=True, cwd=cwd, env=env,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
    )
    if os.name == "posix":
        popen_kwargs["start_new_session"] = True
    else:
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)

    process = subprocess.Popen(command, **popen_kwargs)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_process_tree(process)
        process.communicate()
        raise
    return stdout or "", stderr or "", process.returncode


def _kill_process_tree(process: subprocess.Popen) -> None:
    """Kills a process started by _run_non_interactive together with its children."""
    try:
        if os.name == "posix":
            import signal
            os.killpg(process.pid, signal.SIGKILL)
        else:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        process.kill()
