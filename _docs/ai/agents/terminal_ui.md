## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| TerminalUI | ai/agents/terminal_ui.md |

This component is responsible for providing high-fidelity, formatted output to the terminal, ensuring that the user interface is visually distinct and highly readable. Its primary function is to abstract away the complexity of terminal control sequences (like colors and cursor movement) by centralizing theme loading and standardized logging/display methods.

The `TerminalUI` class acts as a dedicated UI utility layer within the application architecture. It consumes configuration variables, either from the operating system's environment or from custom theme files located in user directories, to define its visual palette. It interacts with the broader application by providing structured feedback (headers, status updates, messages) to the main execution flow.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| TerminalUI.header | Static Method | Displays a formatted header section, taking a primary title and an optional subtitle. |
| TerminalUI.status | Static Method | Displays the current working status of an agent, supporting in-place updates using carriage returns. |
| TerminalUI.auth_request | Static Method | Prints a boxed prompt to the user requesting explicit authorization for a specific tool or command. |
| TerminalUI.message | Static Method | Prints a general, colored message from an agent to the user. |
| TerminalUI.log_step | Static Method | Logs a specific step completion, indicating success or failure via appropriate icons and colors. |
| TerminalUI.agent_step | Static Method | Logs a general activity step taken by an agent. |
| TerminalUI.clear_line | Static Method | Clears the current line in the terminal output, useful for status updates. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The class relies heavily on the private `_get_var` static method to resolve configuration values. This method first checks environment variables, then searches a user-specific `.source/colors.bashrc` file for a theme selection, and finally falls back to hardcoded defaults. All output methods use pre-defined color constants (like `PRIMARY`, `ACCENT`) to ensure visual consistency.
- **Side Effects:** Reads from the filesystem (specifically `~/.source/colors.bashrc` and theme files within `~/.source/themes`), interacts with the standard output stream (`func.out`), and uses terminal control codes (e.g., `\r\033[K`) to manipulate the terminal display.
- **Error Handling:** The `_get_var` method implements a multi-stage fallback mechanism: environment variable $\rightarrow$ theme file parsing $\rightarrow$ hardcoded default. No explicit exception handling for file I/O errors is shown, relying on standard Python file operations.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `THEME_PRIMARY` — Defines the primary color for titles and key elements. Defaults to a specific foreground color.
- `THEME_SECONDARY` — Defines the secondary color, often used for borders or separators. Defaults to a specific foreground color.
- `THEME_ACCENT` — Defines the accent color used for status indicators. Defaults to a specific foreground color.
- `THEME_TEXT` — Defines the main body text color. Defaults to a specific foreground color.
- `THEME_OK` — Defines the color used to signify successful operations. Defaults to a specific foreground color.
- `THEME_WARN` — Defines the color used for warnings or ongoing tasks. Defaults to a specific foreground color.
- `THEME_FAIL` — Defines the color used to signify failures. Defaults to a specific foreground color.
- `ICON_PROMPT` — Custom glyph or icon to be displayed next to the agent's name in the prompt. Defaults to an empty string.
- `ICON_SECTION` — Custom glyph or icon used to mark sections, like the rocket icon. Defaults to an empty string.
- `ICON_SUCCESS` — Custom glyph or icon used to mark successful steps. Defaults to an empty string.
- `ICON_ERROR` — Custom glyph or icon used to mark errors. Defaults to an empty string.
- `GLYPH_H_LINE` — Defines the character used to construct the horizontal divider line. Defaults to an empty string.

**Module Dependencies:**
- **Standard/External:** `os`, `re`
- **Internal:** [ai.functions](/ai/functions.md), [ai.color](/ai/color.md)