import os

def set_console_title(title):
    print("\033]0;{}\007".format(title))

def clear_console():
    os.system("clear")

def beep_console():
    print("\007")