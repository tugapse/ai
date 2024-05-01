
class Color:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'

def format_text(text, color=Color.RESET):
    return f"{color}{text}{Color.RESET}"

def pformat_text(text, color=Color.RESET):
    print (f"{color}{text}{Color.RESET}")