## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **TerminalUI** | [src/ai/agents/terminal_ui.py](/src/ai/agents/terminal_ui.py) |

The `TerminalUI` component is responsible for managing high-fidelity terminal formatting and visual feedback within the agentic environment. It provides a structured way to display headers, agent status updates, authorization requests, and logs using ANSI escape sequences and customizable themes.

This component acts as a specialized UI utility layer. It sits between the core agent logic and the standard output, ensuring that complex interactionssuch as in-place status updates or color-coded error reportingare presented consistently to the user. It leverages environment variables and local configuration files to allow for dynamic theme switching without code changes.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `header(title, subtitle="")` | Static Method | Displays a formatted header section with a divider, title (uppercase), and optional subtitle. |
| `status(agent_name, task, is_updating=True)` | Static Method | Displays the current working status of an agent. If `is_updating` is True, uses carriage returns to allow in-place updates. |
| `auth_request(tool_name, target, command="")` | Static Method | Renders a visually distinct boxed prompt informing the user that a tool requires authorization for a specific target/command. |
| `message(agent_name, text, color=Color.GREEN)` | Static Method | Prints a clean, colored message from a specific agent. |
| `log_step(step_name, status="SUCCESS")` | Static Method | Logs the completion of a specific step with a success or failure icon/color. |
| `agent_step(status="SUCCESS")` | Static Method | Logs a general agent activity step using the agent icon. |
| `clear_line()` | Static Method | Clears the current terminal line using ANSI escape codes. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The class uses a hierarchical variable resolution strategy via `_get_var`. It first checks the system environment, then attempts to parse a specific theme file defined in `~/.source/colors.bashrc`, and finally falls back to hardcoded ANSI defaults. It handles the conversion of escaped strings (e.g., `\e`) into actual terminal escape characters.
- **Side Effects:** 
    - **Filesystem:** Reads from `~/.source/colors.bashrc` and files within `~/.source/themes/` to resolve color themes.
    - **Standard Output:** Writes extensively to `stdout` using `ai.functions.out` and utilizes ANSI escape sequences to manipulate terminal cursor position and color.
- **Error Handling:** The component implements a multi-stage fallback mechanism. If environment variables are missing or theme files are unreadable/missing, it defaults to predefined safe ANSI color codes to ensure the UI remains functional.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `THEME_PRIMARY`  Primary color for titles/headers.
- `THEME_SECONDARY`  Color for dividers and secondary text.
- `THEME_ACCENT`  Color for agent identifiers.
- `THEME_TEXT`  Standard text color.
- `THEME_OK` / `THEME_WARN` / `THEME_FAIL`  Semantic status colors.
- `ICON_PROMPT`  Glyph used for agent status.
- `ICON_SECTION`  Glyph used for headers.
- `ICON_SUCCESS` / `ICON_ERROR`  Status glyphs.
- `GLYPH_H_LINE`  Character used to construct horizontal dividers.

**Module Dependencies:**
- **Standard/External:** `os`, `re`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.color](/AgentDocs/ai/color.md)