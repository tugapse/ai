## Module Purpose
The `/home/fabio/Code/ai/src/ai/agents/terminal_ui.py` file defines the `TerminalUI` class, which is responsible for handling high-fidelity terminal formatting, icons, and layout for the Unified Architect system by providing static methods to print structured and colored output to the console.

## Interface & Exports
*   `TerminalUI` (class): A class containing static methods for generating various types of formatted terminal output.
    *   `TerminalUI.header(title: str, subtitle: str = None)`
    *   `TerminalUI.status(agent_name: str, task: str, is_updating: bool = True)`
    *   `TerminalUI.auth_request(tool_name: str, target: str, command: str = "")`
    *   `TerminalUI.message(agent_name: str, text: str, color: str = Color.GREEN)`
    *   `TerminalUI.log_step(step_name: str, status: str = "SUCCESS")`
    *   `TerminalUI.clear_line()`

## Internal Logic
The `TerminalUI` class implements static methods that construct and print strings formatted with ANSI escape codes for color, bolding, and special effects. It utilizes predefined icon constants and a `DIVIDER` string to create consistent visual elements. Methods like `status()` and `clear_line()` employ carriage returns (`\r`) and erase-line escape codes (`\033[K`) to enable dynamic, overwriting output on the terminal, suitable for status updates or animations. Output is performed via the `func.out()` utility function, ensuring proper flushing for immediate display.

## Dependencies
*   `functions` (imported as `func`)
*   `color` (specifically the `Color` class)

## Constants & Environment
*   `ICON_AGENT` = `"◈"`
*   `ICON_SUCCESS` = `"✓"`
*   `ICON_ERROR` = `"⚠"`
*   `ICON_WAIT` = `"⏳"`
*   `ICON_ROCKET` = `"🚀"`
*   `ICON_TOOL` = `"🔧"`
*   `ICON_LOCK` = `"🔒"`
*   `DIVIDER` = `"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"`