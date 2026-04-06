import os
import time
import errno
import datetime

from config import (
    ProgramConfig,
    ProgramSetting,
)

class ThinkingLogManager:
    """
    Manages a log file for "thinking" content with robust None-type handling.
    """

    DEFAULT_LOG_SUBDIR = os.path.join("Ai", "logs", "thinking")
    DEFAULT_FILENAME = "thinking_process.log"

    def __init__(
        self,
        log_file_name: str = None,
        max_lock_wait_time: int = 10,
        lock_poll_interval: float = 0.1,
    ):
        self.max_lock_wait_time = max_lock_wait_time
        self.lock_poll_interval = lock_poll_interval
        self._lock_fd = None

        # --- CRITICAL FIX: Handle NoneType input ---
        # If history.get_log_path() returns None, fallback to default
        actual_name = log_file_name if log_file_name else self.DEFAULT_FILENAME
        
        # Ensure we are working with a string before calling .replace()
        sanitized_file_name = str(actual_name).replace(" ", "_")
        if not sanitized_file_name.endswith(".log"):
            sanitized_file_name += ".log"

        self.log_file_name = sanitized_file_name

        # Access ProgramConfig safely
        base_log_dir = None
        if ProgramConfig.current:
            base_log_dir = ProgramConfig.current.get(ProgramSetting.PATHS_LOGS)
            
        if base_log_dir:
            self.log_dir = os.path.join(base_log_dir, "thinking")
        else:
            self.log_dir = os.path.join(
                os.path.expanduser("~"), self.DEFAULT_LOG_SUBDIR
            )

        os.makedirs(self.log_dir, exist_ok=True)

        self.log_file_path = os.path.join(self.log_dir, self.log_file_name)
        
        # Determine the active log path safely
        active_base = base_log_dir if base_log_dir else self.log_dir
        self._default_log_filename = os.path.join(active_base, "active_thinking_process.log")
        
        self.lock_file_path = f"{self.log_file_path}.lock"

    def _acquire_write_lock(self):
        start_time = time.time()
        while True:
            try:
                self._lock_fd = os.open(
                    self.lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                )
                os.close(self._lock_fd)
                self._lock_fd = None
                return True
            except OSError as e:
                if e.errno == errno.EEXIST:
                    if time.time() - start_time > self.max_lock_wait_time:
                        raise TimeoutError(f"Lock timeout: {self.log_file_path}")
                    time.sleep(self.lock_poll_interval)
                else:
                    raise IOError(f"Lock error: {e}")

    def _release_write_lock(self):
        try:
            if os.path.exists(self.lock_file_path):
                os.remove(self.lock_file_path)
        except OSError:
            pass

    def write_thinking_log(self, content: str):
        try:
            self._acquire_write_lock()
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(content)
            with open(self._default_log_filename, "a", encoding="utf-8") as f:
                f.write(content)
        except (TimeoutError, IOError) as e:
            print(f"[!] Log Write Error: {e}")
        finally:
            self._release_write_lock()

    def write_session_header(self, tags: str = ""):
        try:
            self._acquire_write_lock()
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            header = f"\n--- Session Start ({tags}): {timestamp} ---\n\n"
            
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(header)
            with open(self._default_log_filename, "w", encoding="utf-8") as f:
                f.write(header)
        except (TimeoutError, IOError):
            pass
        finally:
            self._release_write_lock()

    def read_thinking_log(self) -> str:
        if not os.path.exists(self.log_file_path):
            return ""
        try:
            with open(self.log_file_path, "r", encoding="utf-8") as f:
                return f.read()
        except IOError:
            return ""