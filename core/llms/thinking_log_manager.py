import os
import time
import errno
import datetime
from program import ProgramConfig, ProgramSetting

class ThinkingLogManager:
    """
    Manages a log file for "thinking" content, ensuring exclusive write access
    across processes using a simple lock file mechanism, while allowing concurrent reads.
    The log file directory can be configured via an environment variable.
    """
    
    DEFAULT_LOG_SUBDIR = os.path.join('.ai_assistant', 'logs')
    ENV_VAR_LOG_DIR = 'AI_ASSISTANT_THINKING_LOG_DIR'

    def __init__(self, log_file_name: str = "thinking_process.log", max_lock_wait_time: int = 10, lock_poll_interval: float = 0.1):
        """
        Initializes the ThinkingLogManager.

        Args:
            log_file_name (str): The name of the log file (e.g., "thinking_process.log").
                                 It will be sanitized (spaces and colons replaced with '_',
                                 ensures '.log' extension).
            max_lock_wait_time (int): Maximum time (in seconds) to wait for a write lock.
            lock_poll_interval (float): How often (in seconds) to check for the lock's availability.
        """
        self.max_lock_wait_time = max_lock_wait_time
        self.lock_poll_interval = lock_poll_interval
        self._lock_fd = None

        sanitized_file_name = log_file_name.replace(' ', '_').replace(':', '_')
        if not sanitized_file_name.endswith('.log'):
            sanitized_file_name += '.log'
        
        self.log_file_name = sanitized_file_name

        base_log_dir = ProgramConfig.current.get(ProgramSetting.PATHS_LOGS)
        if base_log_dir:
            self.log_dir = base_log_dir
        else:
            self.log_dir = os.path.join(os.path.expanduser('~'), self.DEFAULT_LOG_SUBDIR)
        
        os.makedirs(self.log_dir, exist_ok=True)

        self.log_file_path = os.path.join(self.log_dir, self.log_file_name)
        self.lock_file_path = f"{self.log_file_path}.lock"

        try:
            self._acquire_write_lock()
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"--- Log Start: {self.log_file_name} - {timestamp} ---\n\n")
        except TimeoutError as e:
            print(f"Error initializing log file (header write): {e}")
        except IOError as e:
            print(f"IO Error initializing log file (header write) for {self.log_file_path}: {e}")
        finally:
            self._release_write_lock()


    def _acquire_write_lock(self):
        """
        Attempts to acquire an exclusive write lock using a lock file.
        Waits for a specified duration if the lock is already held.
        Raises TimeoutError if the lock cannot be acquired within max_lock_wait_time.
        """
        start_time = time.time()
        while True:
            try:
                self._lock_fd = os.open(self.lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(self._lock_fd)
                self._lock_fd = None
                return True
            except OSError as e:
                if e.errno == errno.EEXIST:
                    if time.time() - start_time > self.max_lock_wait_time:
                        raise TimeoutError(f"Could not acquire write lock for {self.log_file_path} after {self.max_lock_wait_time} seconds.")
                    time.sleep(self.lock_poll_interval)
                else:
                    raise IOError(f"Error acquiring lock for {self.log_file_path}: {e}")
            except Exception as e:
                raise IOError(f"An unexpected error occurred while acquiring lock for {self.log_file_path}: {e}")

    def _release_write_lock(self):
        """
        Releases the exclusive write lock by deleting the lock file.
        """
        try:
            os.remove(self.lock_file_path)
        except OSError as e:
            print(f"Warning: Could not remove lock file {self.lock_file_path}: {e}")

    def write_thinking_log(self, content: str):
        """
        Writes content to the thinking log file. Acquires a write lock before writing
        and releases it afterwards to ensure atomicity.

        Args:
            content (str): The string content to append to the log file.
        """
        try:
            self._acquire_write_lock()
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(content)
        except TimeoutError as e:
            print(f"Error: {e}")
        except IOError as e:
            print(f"IO Error writing to {self.log_file_path}: {e}")
        finally:
            self._release_write_lock()

    def write_session_header(self, tags):
        """
        Writes a timestamped header to the log file. This is intended to be called
        once per session when thinking activity begins.
        """
        try:
            self._acquire_write_lock()
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n--- Log Start: {self.log_file_name} - {timestamp} ---\n\n")
        except TimeoutError as e:
            print(f"Error writing session header to {self.log_file_path}: {e}")
        except IOError as e:
            print(f"IO Error writing session header to {self.log_file_path}: {e}")
        finally:
            self._release_write_lock()

    def read_thinking_log(self) -> str:
        """
        Reads the entire content of the thinking log file.
        Waits briefly if a write lock is detected to minimize reading inconsistent data.

        Returns:
            str: The entire content of the log file, or an empty string if the file
                 does not exist or cannot be read.
        """
        start_time = time.time()
        while os.path.exists(self.lock_file_path):
            if time.time() - start_time > self.max_lock_wait_time:
                print(f"Warning: Write lock detected for {self.log_file_path}, proceeding with read "
                      "which might result in inconsistent data as lock could not be released.")
                break
            time.sleep(self.lock_poll_interval)

        if not os.path.exists(self.log_file_path):
            return ""

        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except IOError as e:
            print(f"Error reading from {self.log_file_path}: {e}")
            return ""
