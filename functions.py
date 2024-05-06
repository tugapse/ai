import os
from pathlib import Path
import pathlib
FILE_MODE_APPEND = "a"
FILE_MODE_CREATE = "w"

from color import Color, pformat_text

def set_console_title(title):
    print("\033]0;{}\007".format(title))

def clear_console():
    os.system("clear")

def beep_console():
    print("\007")

def getchar():
   #Returns a single character from standard input
   import tty, termios, sys
   fd = sys.stdin.fileno()
   old_settings = termios.tcgetattr(fd)
   try:
      tty.setraw(sys.stdin.fileno())
      ch = sys.stdin.read(1)
   finally:
      termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
   return ch

def get_files(directory, extension):
    """
    Returns a list of files with the specified extension from the given directory
    and its subdirectories.
    """
    if not os.path.exists(directory):
        pformat_text("Folder not found > " + directory,Color.RED)
        exit(1)
    elif not extension:
        pformat_text("Additional argument required for load-files: extension", Color.RED)
        pformat_text("→ Missing file extension to look for in folder (eg: --extension '.txt')", Color.YELLOW)
        exit(1)
    else:
        file_list = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(extension):
                    filename = os.path.join(root, file)
                    file_list.append({'filename': filename,'content':Path(filename).read_text()})
        return file_list

def read_file(filename)->str:
    if not os.path.exists(filename):
        pformat_text("File not found > " + filename,Color.RED)
        exit(1)
    return Path(filename).read_text()

def write_to_file(filename,content,file_mode=FILE_MODE_CREATE):
    with open(pathlib.Path(filename), file_mode) as f:
        f.write(content)
        f.flush()