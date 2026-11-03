## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **TerminalUI** | [src/ai/agents/terminal_ui.py](/AgentDocs/ai/agents/terminal_ui.md)|

The `TerminalUI` class is responsible for managing high-fidelity terminal formatting and visual feedback within the agent interface. It provides a structured way to display headers, agent status updates, authorization requests, and activity logs using ANSI escape sequences for color and glyph rendering.

This component serves as a specialized UI utility within the agent architecture, ensuring that terminal-based interactions are visually distinct and informative. It abstracts the complexity of theme managementresolving colors from environment variables or local Bash configuration filesand provides consistent visual primitives (like dividers and icons) used during agent execution cycles.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `header(title, subtitle="")` | Static Method | Displays a formatted header section with a divider, a rocket icon, and an optional subtitle. |
| `status(agent_name, task, is_updating=True)` | Static Method | Displays the current working status of an agent. Supports in-place updates via carriage returns. |
| `auth_request(tool_name, target, command="")` | Static Method | Renders a high-visibility boxed prompt requesting user authorization for a specific tool or command. |
| `message(agent_name, text, color=Color.GREEN)` | Static Method | Prints a colored message attributed to a specific agent. |
| `log_step(step_name, status="SUCCESS")` | Static Method | Logs the completion of a specific step with a color-coded status icon (OK or FAIL). |
| `agent_step(status="SUCCESS")` | Static Method | Logs a general agent activity step using the agent icon. |
| `clear_line()` | Static Method | Clears the current line in the terminal using ANSI escape codes. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component uses a hierarchical theme resolution strategy in its private `_get_var` method. It first checks for exported environment variables, then attempts to parse a specific theme file defined in `~/.source/colors.bashrc`, and finally falls back to hardcoded ANSI defaults. It uses regex to parse Bash-style variable assignments and handles unicode escape sequences to ensure terminal compatibility.
- **Side Effects:** 
    - **Filesystem Access:** Reads `~/.source/colors.bashrc` and theme files within `~/.source/themes/` to resolve visual styles.
    - **Standard Output:** Directly writes formatted strings to the terminal via `ai.functions.out`.
- **Error Handling:** The `_get_var` method implements a multi-stage fallback mechanism. If environment variables are missing or theme files are unreadable/not found, it gracefully reverts to hardcoded ANSI color constants to prevent UI crashes.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `THEME_PRIMARY`  Primary color for titles and main UI elements.
- `THEME_SECONDARY`  Color for dividers and secondary text.
- `THEME_ACCENT`  Color for highlights and agent names.
- `THEME_TEXT`  Standard text color.
- `THEME_OK`  Color for success indicators.
- `THEME_WARN`  Color for warning/task text.
- `THEME_FAIL`  Color for error indicators.
- `ICON_PROMPT`  Glyph used for agent prompts.
- `ICON_SECTION`  Glyph used for section headers.
- `ICON_SUCCESS`  Glyph used for successful step completion.
- `ICON_ERROR`  Glyph used for error states.
- `GLYPH_H_LINE`  Character used to construct horizontal dividers.

**Module Dependencies:**
- **Standard/External:** `os`, `re`
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.color](/AgentDocs/ai/color.md)