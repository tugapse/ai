


import os
import fcntl
import json

from ai.services.directory_manager import DirectoryManager
import ai.functions as func 

class ProcessManager:

    _state:dict = {}
    _instance = None

    @staticmethod
    def is_process_running(pid):
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        else:
            return True
    @staticmethod
    def get_current_process_id():
        return os.getpid()

    @staticmethod
    def set_state(key,value):
        ProcessManager._state[key]=value
        if ProcessManager._instance is not None and ProcessManager._instance.lock_handle is not None:
            ProcessManager.save()

    @staticmethod
    def save():
        if ProcessManager._instance : 
            ProcessManager._instance.write(json.dumps(ProcessManager._state))
        else:
            func.error("ProcessMAnager - Save error, no ProcessMAnager instance was found!")

    def __init__(self, directory_manager: DirectoryManager):
        self.directory_manager = directory_manager
        self.process_id = os.getpid()
        self.pid_file = None
        self.lock_handle = None
        ProcessManager._instance = self

    def write(self, content):
        if self.lock_handle is None:
            raise RuntimeError("Process lock is not active.")

        self.lock_handle.seek(0)
        self.lock_handle.truncate(0)
        self.lock_handle.write(str(content))
        self.lock_handle.flush()
        os.fsync(self.lock_handle.fileno())

    def start(self):
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
        if self.lock_handle is not None:
            try:
                fcntl.flock(self.lock_handle.fileno(), fcntl.LOCK_UN)
            finally:
                self.lock_handle.close()
                self.lock_handle = None

        if self.pid_file and os.path.exists(self.pid_file):
            os.remove(self.pid_file)
            self.pid_file = None