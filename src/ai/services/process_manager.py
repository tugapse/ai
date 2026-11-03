import os
import fcntl
import json

from ai.services.directory_manager import DirectoryManager
import ai.functions as func 

class ProcessManager:
    """
    Manages the state and lifecycle of a running process instance.

    This class handles process identification, state persistence via a lock file,
    and ensures that only one instance of the process runs at a time.
    It uses file locking (fcntl) to guarantee atomic operations on the state file.
    """
    _state:dict = {}
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
        except OSError:
            return False
        else:
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
    def set_state(key,value):
        """
        Sets a key-value pair in the shared process state and triggers a save if an instance exists.

        Args:
            key (str): The state key.
            value: The value associated with the key.
        """
        ProcessManager._state[key]=value
        if ProcessManager._instance is not None and ProcessManager._instance.lock_handle is not None:
            ProcessManager.save()

    @staticmethod
    def save():
        """
        Saves the current internal state dictionary to the persistent storage
        managed by the active ProcessManager instance.

        Raises:
            func.Error: If no ProcessManager instance is available to perform the save operation.
        """
        if ProcessManager._instance : 
            ProcessManager._instance.write(json.dumps(ProcessManager._state))
        else:
            func.error("ProcessMAnager - Save error, no ProcessMAnager instance was found!")

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
            content (str): The serialized content (e.g., JSON string) to write.

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
        Starts the process instance by acquiring an exclusive lock on the PID file.

        This method ensures that if another instance is running, it raises an error.
        It creates the necessary directory structure if it does not exist.

        Raises:
            RuntimeError: If the process is already running (lock acquisition fails).
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

        self.write(self.process_id)

    def shutdown(self):
        """
        Gracefully shuts down the process instance by releasing the lock and removing the PID file.
        """
        if self.lock_handle is not None:
            try:
                fcntl.flock(self.lock_handle.fileno(), fcntl.LOCK_UN)
            finally:
                self.lock_handle.close()
                self.lock_handle = None

        if self.pid_file and os.path.exists(self.pid_file):
            os.remove(self.pid_file)
            self.pid_file = None