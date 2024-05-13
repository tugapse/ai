import os
from pathlib import Path
import pathlib

from ai.core.context_file import ContextFile

FILE_MODE_APPEND = "a"
FILE_MODE_CREATE = "w"

from ai.color import Color, pformat_text

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


def get_files(directory, extension=None) -> ContextFile:
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

    else:
        file_list = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if extension and not file.endswith(extension):
                    continue
                filename = os.path.join(root, file)
                file_list.append(ContextFile(filename=filename))
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

def write_to_file(filename, content, filemode=FILE_MODE_CREATE):
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
    a_dir = os.path.dirname(filename)
    os.makedirs(a_dir,exist_ok=True)
    
    with open(pathlib.Path(filename), filemode) as f:
        f.write(content)
        f.flush()
        
def format_execution_time(start_time,end_time):
   
    elapsed_seconds = end_time - start_time
    hours = int(elapsed_seconds // 3600)
    minutes = int((elapsed_seconds % 3600) // 60)
    seconds = int(elapsed_seconds % 60)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
