from color import Color, pformat_text
import os
from pathlib import Path
import sys
import glob  # Import glob for get_files

from core.context_file import ContextFile
from core.template_injection import TemplateInjection
from colorama import Fore, Style
from config import ProgramConfig, ProgramSetting  # Ensure these are correctly imported

FILE_MODE_APPEND = "a"
FILE_MODE_CREATE = "w"

LOCK_LOG = False  # This variable needs to be accessible globally for logging control
ACTIVE_LOG_FILENAME = "active_log_output.log"
SESSION_LOG_FILENAME = "log_output.log"


def set_console_title(title):
    """
    Sets the console title to the specified string.

    Args:
        title (str): The new title for the console.
    """
    if os.name == "nt":  # For Windows
        os.system(f"title {title}")
    else:  # For Linux/macOS
        sys.stdout.write(f"\x1b]2;{title}\x07")
        sys.stdout.flush()


def clear_console():
    """
    Clears the console by running the "clear" command.
    """
    if sys.platform != "win32":
        os.system("clear")
    else:
        os.system("cls")


def beep_console():
    """
    Beeps the console to get attention.
    """
    print("\007")


def get_files(directory, extension=None) -> list[ContextFile]:
    """
    Returns a list of files with the specified extension from the given directory and its subdirectories.
    Uses pathlib and glob for more robust file searching.

    Args:
        directory (str): The directory to search for files.
        extension (str): The file extension to filter by (e.g., ".txt", "py").

    Returns:
        list[ContextFile]: A list of ContextFile objects for the found files.
    """
    base_path = Path(directory)
    if not base_path.exists():
        log(f"Folder not found: {directory}", level="ERROR")
        # Use out for user-facing errors
        out(f"{Color.RED}Error: Folder not found > {directory}{Color.RESET}")
        sys.exit(1)  # Exit here as per original logic

    file_list = []
    # Adjust search pattern for glob if extension is provided
    search_pattern = (
        f"*.{extension}"
        if extension and not extension.startswith(".")
        else f"*{extension}" if extension else "*"
    )

    # Using glob.glob with recursive=True to find files in subdirectories
    for filepath in base_path.rglob(search_pattern):  # rglob is recursive glob
        if filepath.is_file():
            file_list.append(
                ContextFile(filename=str(filepath.resolve()))
            )  # Ensure absolute path and string

    return file_list


def read_file(filename):
    """
    Reads the contents of a file and returns it as a string.

    Args:
        filename (str): The name of the file to read.

    Returns:
        str: The contents of the specified file.
    """
    file_path = Path(filename)
    if not file_path.exists():  # Check if the file itself exists
        log(f"File not found: {filename}", level="ERROR")
        out(f"{Color.RED}Error: File not found > {filename}{Color.RESET}")
        sys.exit(1)  # Exit here as per original logic

    try:
        return file_path.read_text(
            encoding="utf-8"
        )  # Specify encoding for robust reading
    except Exception as e:
        log(f"Error reading file {filename}: {e}", level="ERROR")
        out(f"{Color.RED}Error reading file {filename}: {e}{Color.RESET}")
        sys.exit(1)  # Exit on read error as per original logic


def write_to_file(filename, content, filemode=FILE_MODE_CREATE, silent=False):
    """
    Writes the given content to a file.

    Args:
        filename (str): The name of the file to write.
        content (str): The content to be written to the file.
        filemode (str): The mode in which to open the file. Defaults to "w" for overwrite.
    """
    file_path = Path(filename).resolve()
    # Use ensure_directory_exists to create parent directories
    ensure_directory_exists(str(file_path.parent),silent=silent)

    try:
        with open(file_path, filemode, encoding="utf-8") as f:  # Specify encoding
            f.write(content)
            f.flush()
    except Exception as e:
        if not silent:
            log(f"Error writing to file {filename}: {e}", level="ERROR")
            out(f"{Color.RED}Error writing to file {filename}: {e}{Color.RESET}")
        sys.exit(1)  # Exit on write error if necessary, or just log and continue


def format_execution_time(start_time, end_time):
    """
    Formats the elapsed time between start_time and end_time into HH:MM:SS format.
    """
    elapsed_seconds = end_time - start_time
    hours = int(elapsed_seconds // 3600)
    minutes = int((elapsed_seconds % 3600) // 60)
    seconds = int(elapsed_seconds % 60)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# --- New/Adapted Utility Functions ---


def get_root_directory() -> str:
    """
    Retrieves the configured root directory from ProgramConfig.
    Provides a fallback to (user home)/Ai if not configured.
    """
    # ProgramConfig.current should be set by ProgramConfig.load() in main.py
    config_instance = ProgramConfig.current

    if config_instance:
        root_path = config_instance.get(ProgramSetting.ROOT_DIRECTORY)
        if root_path:
            return os.path.abspath(root_path)

    # Fallback if config is not loaded or key not found (should be handled by ProgramConfig defaults now)
    fallback_path = os.path.join(os.path.expanduser("~"), "Ai")
    log(
        f"WARNING: '{ProgramSetting.ROOT_DIRECTORY}' not found in config. Using fallback: {fallback_path}",
        level="WARNING",
    )
    return os.path.abspath(fallback_path)


def ensure_directory_exists(path: str,silent=False):
    """
    Ensures that a directory exists, creating it and any necessary parent directories if they don't exist.
    Logs a message upon creation.
    """
    if not os.path.exists(path):
        try:
            os.makedirs(
                path, exist_ok=True
            )  # exist_ok=True prevents error if dir already exists
            if not silent: log(f"Created directory: {path}", level="INFO")
        except OSError as e:
            if not silent:
                log(f"Error creating directory {path}: {e}", level="ERROR")
            out(
                f"{Color.RED}Error: Failed to create directory: {path} - {e}{Color.RESET}"
            )
            sys.exit(1)  # Exit on critical directory creation failure
    else:
        if not silent: log(f"Directory already exists: {path}", level="DEBUG")


# --- Logging/Output Functions (Adapted to use ProgramConfig.current) ---


def log(text, start_line="[ * ]", level="INFO", **kargs):  # Added level for consistency
    """
    Logs an informational message to stderr, respecting PRINT_LOG setting.
    """
    # Ensure ProgramConfig.current is loaded before trying to access settings
    formatted_text = f"{Color.BLUE}{start_line}{Color.RESET} {text}"
    if level == "ERROR":
        formatted_text = f"{Color.RED}{start_line}{Color.RESET} {text}"
    elif level == "WARNING":
        formatted_text = f"{Color.YELLOW}{start_line}{Color.RESET} {text}"
    elif (
        level == "DEBUG"
    ):  # Debug is now handled by its own func, but keeping consistency here
        formatted_text = f"{Color.BRIGHT_CYAN}{start_line}{Color.RESET} {text}"

    write_to_file(ACTIVE_LOG_FILENAME, f"{start_line} {text}\n", FILE_MODE_APPEND,True)
    write_to_file(SESSION_LOG_FILENAME, f"{start_line} {text}\n", FILE_MODE_APPEND,True)

    if not LOCK_LOG:
        print(formatted_text, **kargs)
        sys.stdout.flush()  # Ensure it's flushed immediately


def debug(text, start_line="[ # ]", **kargs):
    """
    Logs a debug message to stderr, respecting PRINT_DEBUG setting.
    """
    formatted_text = f"{Color.PURPLE}{start_line}{Color.RESET} {text}"
    write_to_file(
        ACTIVE_LOG_FILENAME.replace("log_", "debug_"), f"{start_line} {text}\n", FILE_MODE_APPEND,True
    )
    write_to_file(
        SESSION_LOG_FILENAME.replace("log_", "debug_"),
        f"{start_line} {text}\n",
        FILE_MODE_APPEND,
        True
    )
    if not LOCK_LOG:
        print(formatted_text, **kargs)
        sys.stdout.flush()


def out(text, **kargs):
    """
    Prints output message to stdout, respecting PRINT_OUTPUT setting.
    """

    print(text, **kargs)
    sys.stdout.flush()  # Ensure it's flushed immediately
