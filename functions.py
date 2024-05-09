import os
from pathlib import Path
import pathlib
FILE_MODE_APPEND = "a"
FILE_MODE_CREATE = "w"

from color import Color, pformat_text

def set_console_title(title):
    """
    Sets the console title to the specified string.

    Args:
        title (str): The new title for the console.

    Example:
        >>> set_console_title("My AI Assistant")
    """
    print("\033]0;{}\007".format(title))

def clear_console():
    """
    Clears the console by running the "clear" command.

    Example:
        >>> clear_console()
    """
    os.system("clear")

def beep_console():
    """
    Beeps the console to get attention.

    Example:
        >>> beep_console()
    """
    print("\007")


def get_files(directory, extension=None):
    """
    Returns a list of files with the specified extension from the given directory and its subdirectories.

    Args:
        directory (str): The directory to search for files.
        extension (str): The file extension to filter by.

    Example:
        >>> get_files("/path/to/directory", ".txt")
            # Returns a list of .txt files in the specified directory
    """
    if not os.path.exists(directory):
        pformat_text("Folder not found > " + directory, Color.RED)
        exit(1)

    # elif not extension:
    #     pformat_text("Additional argument required for load-files: extension", Color.RED)
    #     pformat_text("→ Missing file extension to look for in folder (eg: --extension '.txt')", Color.YELLOW)
    #     exit(1)

    else:
        file_list = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if extension and not file.endswith(extension):
                    continue
                filename = os.path.join(root, file)
                file_list.append({'filename': filename,'content':Path(filename).read_text()})
        return file_list

def read_file(filename):
    """
    Reads the contents of a file and returns it as a string.

    Args:
        filename (str): The name of the file to read.

    Example:
        >>> read_file("/path/to/file.txt")
            # Returns the contents of the specified file
    """
    if not os.path.exists(filename):
        pformat_text("File not found > " + filename, Color.RED)
        exit(1)

    return Path(filename).read_text()

def write_to_file(filename, content, file_mode=FILE_MODE_CREATE):
    """
    Writes the given content to a file.

    Args:
        filename (str): The name of the file to write.
        content (str): The content to be written to the file.
        file_mode (str): The mode in which to open the file. Defaults to "w" for overwrite.

    Example:
        >>> write_to_file("/path/to/file.txt", "Hello, World!")
            # Writes "Hello, World!" to the specified file
    """
    with open(pathlib.Path(filename), file_mode) as f:
        f.write(content)
        f.flush()
        
def format_execution_time(start_time,end_time):
    seconds = end_time - start_time
    if seconds < 61: return f"{seconds} seconds"
    if seconds < 3601: return f"{seconds / 60}  minutes and {seconds%60} seconds"
    if seconds >= 216000: return f"{seconds / 60/ 60 }  minutes and {(seconds / 60 / 60) % 60}  minutes and {seconds%60} seconds"