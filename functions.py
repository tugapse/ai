def set_console_title(title):
    print("\033]0;{}\007".format(title))