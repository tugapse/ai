import os
import re

import ai.functions as func
from ai.color import Color

class TerminalUI:
    """
    Handles high-fidelity terminal formatting.
    Loads theme variables from Bash environment or directly from theme files.
    """
    
    @staticmethod
    def _get_var(env_name, fallback):
        """
        Retrieves variable from environment or parses the theme file directly.

        Args:
            env_name (str): The name of the environment variable to look for.
            fallback (str): The default value to use if the variable is not found.

        Returns:
            str: The resolved variable value, correctly escaped for terminal use.
        """
        # 1. Check if already exported in environment
        val = os.getenv(env_name)
        if val:
            return val.encode().decode('unicode_escape').replace('\\e', '\033')
            
        # 2. Check if a theme is saved in colors.bashrc
        config_path = os.path.expanduser("~/.source/colors.bashrc")
        theme_dir = os.path.expanduser("~/.source/themes")
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                match = re.search(r'COLOR_THEME=["\'](.+?)["\']', f.read())
                if match:
                    theme_file = os.path.join(theme_dir, f"{match.group(1)}.bashrc")
                    # 3. Read the specific theme file if it exists
                    if os.path.exists(theme_file):
                        with open(theme_file, 'r') as tf:
                            for line in tf:
                                if env_name in line and "=" in line:
                                    content = re.search(r'=["\'](.+?)["\']', line)
                                    if content:
                                        return content.group(1).encode().decode('unicode_escape').replace('\\e', '\033')
        
        # 4. Final Hardcoded Fallback
        return fallback.encode().decode('unicode_escape').replace('\\e', '\033')

    # Theme Colors
    PRIMARY = _get_var("THEME_PRIMARY", "\033[38;5;214m")
    SECONDARY = _get_var("THEME_SECONDARY", "\033[38;5;94m")
    ACCENT = _get_var("THEME_ACCENT", "\033[38;5;202m")
    TEXT = _get_var("THEME_TEXT", "\033[38;5;223m")
    
    OK = _get_var("THEME_OK", "\033[38;5;106m")
    WARN = _get_var("THEME_WARN", "\033[38;5;226m")
    FAIL = _get_var("THEME_FAIL", "\033[38;5;124m")
    RESET = "\033[0m"

    # Icons & Glyphs
    ICON_AGENT = os.getenv("ICON_PROMPT", "")
    ICON_ROCKET = os.getenv("ICON_SECTION", "")
    ICON_SUCCESS = os.getenv("ICON_SUCCESS", "")
    ICON_ERROR = os.getenv("ICON_ERROR", "")
    
    H_LINE = os.getenv("GLYPH_H_LINE", "")
    DIVIDER = H_LINE * 60

    @staticmethod
    def header(title: str, subtitle: str = ""):
        """
        Displays a formatted header section for the UI.

        Args:
            title (str): The main title to display.
            subtitle (str, optional): A secondary subtitle. Defaults to "".
        """
        func.out(f"\n{TerminalUI.SECONDARY}{TerminalUI.DIVIDER}{TerminalUI.RESET}")
        func.out(f"{TerminalUI.PRIMARY}{TerminalUI.ICON_ROCKET} {title.upper()}{TerminalUI.RESET}")
        if subtitle:
            func.out(f"{TerminalUI.TEXT}   {subtitle}{TerminalUI.RESET}")
        func.out(f"{TerminalUI.SECONDARY}{TerminalUI.DIVIDER}{TerminalUI.RESET}")

    @staticmethod
    def status(agent_name: str, task: str, is_updating: bool = True):
        """
        Displays the current working status of an agent.

        Args:
            agent_name (str): The name of the agent performing the task.
            task (str): The description of the task being performed.
            is_updating (bool, optional): If True, prepends carriage return and clear line for in-place updates. Defaults to True.
        """
        prefix = "\r\033[K" if is_updating else ""
        func.out(
            f"{prefix}\n{TerminalUI.ACCENT}{TerminalUI.ICON_AGENT} {Color.BOLD}{agent_name}{TerminalUI.RESET} "
            f"{TerminalUI.TEXT}is working on: {TerminalUI.WARN}{task}{TerminalUI.RESET}", 
            flush=True
        )

    @staticmethod
    def auth_request(tool_name: str, target: str, command: str = ""): 
        """
        Displays a boxed authorization request prompt to the user.

        Args:
            tool_name (str): The name of the tool requiring authorization.
            target (str): The target entity or resource.
            command (str, optional): The specific command being requested. Defaults to "".
        """
        func.out(f"\n{Color.BLUE} {Color.BG_YELLOW}AUTHORIZATION REQUIRED{Color.BLUE} ")
        func.out(f" {Color.NORMAL_CYAN}TOOL:   {Color.BLUE}{tool_name}")
        if command:
            func.out(f" {Color.NORMAL_CYAN}CMD: {Color.BLUE}{command}")
        func.out(f" {Color.NORMAL_CYAN}TARGET: {Color.BLUE}{target}")
        func.out(f"{Color.RESET}")

    @staticmethod
    def message(agent_name: str, text: str, color: str = Color.GREEN):
        """
        Prints a general message from an agent to the user with specified coloring.

        Args:
            agent_name (str): The name of the agent sending the message.
            text (str): The content of the message.
            color (str, optional): The color code to apply to the message. Defaults to Color.GREEN.
        """
        clean_text = text.strip()
        func.out(f"{color}{clean_text}{Color.RESET}")

    @staticmethod
    def log_step(step_name: str, status: str = "SUCCESS"):
        """
        Logs a specific step completion with a status indicator.

        Args:
            step_name (str): The name of the step that was completed.
            status (str, optional): The status of the step ("SUCCESS" or anything else, defaults to "SUCCESS").
        """
        color = TerminalUI.OK if status == "SUCCESS" else TerminalUI.FAIL
        icon = TerminalUI.ICON_SUCCESS if status == "SUCCESS" else TerminalUI.ICON_AGENT
        func.out(f"\n{color}{icon} {step_name}{TerminalUI.RESET}")

    @staticmethod
    def agent_step(status: str = "SUCCESS"):
        """
        Logs a general agent activity step.

        Args:
            status (str, optional): The status of the agent step. Defaults to "SUCCESS".
        """
        color = TerminalUI.OK 
        icon = TerminalUI.ICON_AGENT
        func.out(f"\n{color}{icon} {status}{TerminalUI.RESET}")

    @staticmethod
    def clear_line():
        """
        Clears the current line in the terminal output.
        """
        func.out("\r\033[K", end="", flush=True)