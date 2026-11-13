import os
import fcntl
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ai.services.directory_manager import DirectoryManager
import ai.functions as func

# Project root this instance runs from (src/ai/services/process_manager.py -> root).
_INSTALL_PATH = str(Path(__file__).resolve().parents[3])


class ProcessManager:
    """
    Registry entry for a running JARVIS instance.

    Each instance holds an exclusive ``flock`` on ``pids/<pid>.pid`` for its whole life and keeps
    a short plain-text status in it, one ``key: value`` per line::

        pid:      3868145
        mode:     agent
        install:  /home/user/Code/ai
        started:  2026-11-13 21:02:11
        model:    gemma4
        activity: [3/20] coder: Implement the config parser
        endpoint: http://127.0.0.1:9999        (server mode only)

    Other instances read these files (``list_instances``) to know what is running; a file whose
    lock can be taken belongs to a dead process and is removed.
    """
    FIELDS = ("pid", "mode", "install", "started", "model", "activity", "endpoint")
    MAX_VALUE_LENGTH = 200

    _state: Dict[str, str] = {}
    _instance = None

    @staticmethod
    def is_process_running(pid):
        """
        Checks if a process with the given PID is currently running.

        Args:
            pid (int): The Process ID to check.

        Returns:
            bool: True if the process is running, False otherwise.
        """
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # exists, owned by another user
        except OSError:
            return False
        return True

    @staticmethod
    def get_current_process_id():
        """
        Retrieves the Process ID of the current running process.

        Returns:
            int: The current process ID.
        """
        return os.getpid()

    @staticmethod
    def _clean_value(value) -> str:
        """Collapses a value to one line of bounded length so it can never break the file format."""
        text = " ".join(str(value if value is not None else "").split())
        if len(text) > ProcessManager.MAX_VALUE_LENGTH:
            text = text[:ProcessManager.MAX_VALUE_LENGTH - 1] + "…"
        return text

    @staticmethod
    def serialize(state: Dict[str, str]) -> str:
        """Renders a state dict as aligned ``key: value`` lines, in FIELDS order."""
        width = max(len(k) for k in ProcessManager.FIELDS) + 1
        lines = [f"{(key + ':').ljust(width)} {state[key]}" for key in ProcessManager.FIELDS if key in state]
        return "\n".join(lines) + "\n"

    @staticmethod
    def parse(text: str) -> Dict[str, str]:
        """Parses ``key: value`` lines, splitting on the first colon only (values may contain colons)."""
        state = {}
        for line in text.splitlines():
            key, sep, value = line.partition(":")
            if sep and key.strip():
                state[key.strip()] = value.strip()
        return state

    @staticmethod
    def set_state(key, value):
        """
        Sets one status field and saves it if this process holds its PID lock.

        Args:
            key (str): One of ``ProcessManager.FIELDS``.
            value: The value; reduced to a single line of at most MAX_VALUE_LENGTH characters.

        Raises:
            ValueError: If ``key`` is not a known field.
        """
        if key not in ProcessManager.FIELDS:
            raise ValueError(f"Unknown process state field '{key}'. Allowed: {', '.join(ProcessManager.FIELDS)}")
        value = ProcessManager._clean_value(value)
        if ProcessManager._state.get(key) == value:
            return
        ProcessManager._state[key] = value
        if ProcessManager._instance is not None and ProcessManager._instance.lock_handle is not None:
            ProcessManager.save()

    @staticmethod
    def save():
        """
        Writes the current state to the PID file of the active ProcessManager instance.
        """
        if ProcessManager._instance:
            ProcessManager._instance.write(ProcessManager.serialize(ProcessManager._state))
        else:
            func.error("ProcessManager - Save error, no ProcessManager instance was found!")

    @staticmethod
    def list_instances(pid_directory: str) -> List[Dict[str, str]]:
        """
        Returns the status of every live instance registered in ``pid_directory``.

        A PID file whose lock can be taken and whose process is gone is stale and gets removed.
        A file being created right now (lock not yet held) belongs to a live PID, so it is kept.

        Args:
            pid_directory: The directory holding the ``<pid>.pid`` files.

        Returns:
            One state dict per live instance, sorted by PID.
        """
        instances = []
        if not os.path.isdir(pid_directory):
            return instances

        for name in os.listdir(pid_directory):
            stem, ext = os.path.splitext(name)
            if ext != ".pid" or not stem.isdigit():
                continue
            pid, path = int(stem), os.path.join(pid_directory, name)
            try:
                with open(path, "r") as handle:
                    try:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                        unlocked = True
                    except BlockingIOError:
                        unlocked = False
                    if unlocked and not ProcessManager.is_process_running(pid):
                        os.remove(path)
                        continue
                    state = ProcessManager.parse(handle.read())
            except FileNotFoundError:
                continue  # its owner shut down while we were listing
            except OSError as e:
                func.debug(f"ProcessManager: cannot read {path}: {e}")
                continue
            state.setdefault("pid", str(pid))
            instances.append(state)

        return sorted(instances, key=lambda s: int(s["pid"]) if s["pid"].isdigit() else 0)

    def __init__(self, directory_manager: DirectoryManager):
        """
        Initializes the ProcessManager instance.

        Args:
            directory_manager (DirectoryManager): The manager responsible for file system operations.
        """
        self.directory_manager = directory_manager
        self.process_id = os.getpid()
        self.pid_file = None
        self.lock_handle = None
        ProcessManager._instance = self

    def write(self, content):
        """
        Writes the provided content to the associated PID file handle, ensuring atomicity.

        Args:
            content (str): The serialized content to write.

        Raises:
            RuntimeError: If the process lock handle is not active.
        """
        if self.lock_handle is None:
            raise RuntimeError("Process lock is not active.")

        self.lock_handle.seek(0)
        self.lock_handle.truncate(0)
        self.lock_handle.write(str(content))
        self.lock_handle.flush()
        os.fsync(self.lock_handle.fileno())

    def start(self):
        """
        Registers this instance: takes an exclusive lock on its PID file and writes the initial status.

        Fields set before ``start`` (e.g. ``mode``) are kept.

        Raises:
            RuntimeError: If the PID file is already locked.
        """
        self.pid_file = os.path.join(self.directory_manager.get_pid_directory(), f"{self.process_id}.pid")

        if self.lock_handle is not None:
            self.shutdown()

        pid_directory = os.path.dirname(self.pid_file)
        if not os.path.exists(pid_directory):
            os.makedirs(pid_directory, exist_ok=True)

        self.lock_handle = open(self.pid_file, "w+")
        try:
            fcntl.flock(self.lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self.lock_handle.close()
            self.lock_handle = None
            raise RuntimeError(f"Process {self.process_id} is already running.") from exc

        ProcessManager._state.update({
            "pid": str(self.process_id),
            "install": _INSTALL_PATH,
            "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        ProcessManager._instance = self  # the registered instance is the one later saves go to
        self.write(ProcessManager.serialize(ProcessManager._state))

    def shutdown(self):
        """
        Gracefully shuts down the process instance: removes the PID file, then releases the lock.

        Removing first means a lister never sees our file unlocked while it still exists.
        """
        if self.pid_file and os.path.exists(self.pid_file):
            os.remove(self.pid_file)
        self.pid_file = None

        if self.lock_handle is not None:
            try:
                fcntl.flock(self.lock_handle.fileno(), fcntl.LOCK_UN)
            finally:
                self.lock_handle.close()
                self.lock_handle = None
