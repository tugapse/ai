import functions as func
from color import Color

class TerminalUI:
    """
    Handles high-fidelity terminal formatting, icons, and 
    layout for the Unified Architect system.
    """
    
    # Icons & Constants
    ICON_AGENT = "◈"
    ICON_SUCCESS = "✓"
    ICON_ERROR = "⚠"
    ICON_WAIT = "⏳"
    ICON_ROCKET = "🚀"
    ICON_TOOL = "🔧"
    ICON_LOCK = "🔒"
    
    DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    @staticmethod
    def header(title: str, subtitle: str = None):
        """Prints a major section header."""
        func.out(f"\n{Color.BLUE}{TerminalUI.DIVIDER}{Color.RESET}")
        func.out(f"{Color.NORMAL_CYAN}{TerminalUI.ICON_ROCKET} {title.upper()}{Color.RESET}")
        if subtitle:
            func.out(f"{Color.NORMAL_CYAN}{subtitle}{Color.RESET}")
        func.out(f"{Color.BLUE}{TerminalUI.DIVIDER}{Color.RESET}")

    @staticmethod
    def status(agent_name: str, task: str, is_updating: bool = True):
        """
        Prints an agent's current working status.
        If is_updating=True, it uses \r to overwrite animations.
        """
        prefix = "\r\033[K" if is_updating else ""
        func.out(
            f"{prefix}Agent {Color.RESET} "
            f"is working on: {Color.YELLOW}{task}{Color.RESET}", 
            flush=True
        )

    @staticmethod
    def auth_request(tool_name: str, target: str, command:str = ""): 
        
        """Displays a boxed authorization request."""
        func.out(f"{Color.BLUE}╭── {Color.BG_YELLOW}{Color.NORMAL_BLACK} AUTHORIZATION REQUIRED {Color.RESET}{Color.BLUE} ───")
        func.out(f"│ {Color.NORMAL_CYAN}TOOL:   {Color.RESET}{tool_name}")
        if command:
            func.out(f"│ {Color.NORMAL_CYAN}COMMA.: {Color.RESET}{command}")
        func.out(f"│ {Color.NORMAL_CYAN}TARGET: {Color.RESET}{target}")
        func.out(f"╰───────────────────────────────────────────────────{Color.RESET}")

    @staticmethod
    def message(agent_name: str, text: str, color: str = Color.GREEN):
        """Prints a message from an agent to the user."""
        func.out(f"\n{Color.BOLD}{color}[{agent_name}]{Color.RESET} {text}")

    @staticmethod
    def log_step(step_name: str, status: str = "SUCCESS"):
        """Logs a stage completion (Stage 1, Stage 2, etc)."""
        color = Color.GREEN if status == "SUCCESS" else Color.RED
        icon = TerminalUI.ICON_SUCCESS if status == "SUCCESS" else TerminalUI.ICON_ERROR
        func.out(f"{color}{icon} {step_name}{Color.RESET}")

    @staticmethod
    def clear_line():
        """Clears the current terminal line."""
        func.out("\r\033[K", end="", flush=True)