## 1. Architectural Role

**Functional Mission**
The **TerminalUI** class serves as the high-fidelity presentation layer for the agentic system, specifically designed to manage terminal-based user interfaces. Its primary mission is to abstract complex ANSI escape sequences, theme management, and glyph rendering into a clean, semantic API, ensuring that agent activities, status updates, and authorization requests are visually distinct and professional.

**System Context & Integration**
This component acts as the visual output driver for the agentic workflow. It is utilized by agents to communicate their internal states (via `status` and `log_step`) and to present structured data to the user (via `header` and `auth_request`). It integrates closely with [functions](/docs/functions.md) for standard output operations and relies on [color](/docs/color.md) for semantic text styling. By centralizing theme resolution through environment variables and local configuration files, it ensures a consistent aesthetic across the entire CLI execution environment.

## 2. Environment & Configuration

**Environment Lookups:**
- `THEME_PRIMARY` (via `_get_var`)  Primary brand color for headers and icons.
- `THEME_SECONDARY` (via `_get_var`)  Secondary color for dividers and subtitles.
- `THEME_ACCENT` (via `_get_var`)  Accent color for agent names and highlights.
- `THEME_TEXT` (via `_get_var`)  Standard text color for body content.
- `THEME_OK` (via `_get_var`)  Color for successful operation indicators.
- `THEME_WARN` (via `_get_var`)  Color for warning/task descriptions.
- `THEME_FAIL` (via `_get_var`)  Color for error/failure indicators.
- `ICON_PROMPT` (via class attribute)  Glyph used to represent the agent.
- `ICON_SECTION` (via class attribute)  Glyph used for section headers.
- `ICON_SUCCESS` (via class attribute)  Glyph for successful steps.
- `ICON_ERROR` (via class attribute)  Glyph for failed steps.
- `GLYPH_H_LINE` (via class attribute)  Character used for horizontal dividers.

**Hardcoded Constants:**
- `PRIMARY` (Default: `\033[38;5;214m`)  Fallback primary color.
- `SECONDARY` (Default: `\033[38;5;94m`)  Fallback secondary color.
- `ACCENT` (Default: `\033[38;5;202m`)  Fallback accent color.
- `TEXT` (Default: `\033[38;5;223m`)  Fallback text color.
- `OK` (Default: `\033[38;5;106m`)  Fallback success color.
- `WARN` (Default: `\033[38;5;226m`)  Fallback warning color.
- `FAIL` (Default: `\033[38;5;124m`)  Fallback failure color.
- `RESET` (Default: `\033[0m`)  ANSI reset sequence.
- `ICON_AGENT` (Default: ``)  Fallback agent icon.
- `ICON_ROCKET` (Default: ``)  Fallback section icon.
- `ICON_SUCCESS` (Default: ``)  Fallback success icon.
- `ICON_ERROR` (Default: ``)  Fallback error icon.
- `H_LINE` (Default: ``)  Fallback horizontal line glyph.
- `DIVIDER` (Default: `` * 60)  Pre-calculated horizontal divider string.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `_get_var` | Static Method | Resolves theme variables by checking environment, then `~/.source/colors.bashrc`, then specific theme files in `~/.source/themes/`. |
| `header` | Static Method | Renders a stylized header with a title, optional subtitle, and horizontal dividers. |
| `status` | Static Method | Displays a dynamic, single-line status update for an agent's current task, supporting in-place updates via carriage return. |
| `auth_request` | Static Method | Renders a structured, boxed UI component requesting user authorization for a specific tool or command. |
| `message` | Static Method | Prints a clean, color-coded message from an agent to the terminal. |
| `log_step` | Static Method | Renders a single-line log entry indicating the success or failure of a specific step with appropriate icons. |
| `clear_line` | Static Method | Uses ANSI escape sequences to clear the current terminal line. |

## 4. Execution Logic & Flow

- **Initialization**: 
    - Upon class definition, `_get_var` is invoked for all theme constants.
    - `_get_var` performs a hierarchical lookup: 
        1. `os.getenv` check.
        2. Parsing `~/.source/colors.bashrc` for `COLOR_THEME`.
        3. Parsing the resulting theme file in `~/.source/themes/` for the specific variable.
        4. Falling back to hardcoded ANSI defaults.
    - All retrieved strings undergo `unicode_escape` decoding and `\e` to `\033` replacement to ensure valid ANSI escape sequences.
- **Data Path**:
    - **Input**: Semantic strings (titles, agent names, tasks, commands) and color identifiers.
    - **Processing**: String interpolation with ANSI escape sequences and icon glyphs.
    - **Output**: Formatted text sent to standard output via `func.out`.
- **Conditional Branching**:
    - `_get_var`: Branches based on the existence of environment variables, the existence of the config file, and the existence of the specific theme file.
    - `status`: Branches on `is_updating` to determine whether to prepend a carriage return/clear line sequence (`\r\033[K`).
    - `log_step`: Branches on the `status` string ("SUCCESS" vs others) to select the appropriate color and icon.

## 5. Resource Dependencies

- **Standard Libraries**: `os`, `re`
- **Internal Modules**: 
    - [functions](/docs/functions.md)
    - [color](/docs/color.md)
- **External Packages**: None identified.