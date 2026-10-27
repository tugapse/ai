## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | TerminalUI |
| Source file | terminal_ui.py |

The **TerminalUI** component serves as the high-fidelity presentation layer for the agent's command-line interface. It is responsible for translating abstract system states, agent activities, and authorization requirements into visually structured, color-coded terminal output. By abstracting ANSI escape sequences and theme management, it provides a consistent aesthetic experience across different terminal environments.

**Functional Mission**
The primary responsibility of **TerminalUI** is to manage the visual ergonomics of the terminal session. It solves the problem of "information density overload" by using structured headers, status indicators, and color-coded messaging to help users quickly distinguish between agent thoughts, system logs, and critical authorization requests.

**System Context & Integration**
This component acts as a downstream consumer of system events and agent states. It is typically invoked by agents or orchestrators to signal progress or request user intervention. It integrates closely with [Color](/docs/ai/color.md) for low-level ANSI definitions and utilizes [ai.functions](/docs/ai/functions.md) for the actual output stream. It functions as a specialized view in a Model-View-Controller-like pattern, where the agent logic (Model/Controller) triggers specific visual representations (View) through this interface.

- **INTERNAL REFERENCES**: [Color](/docs/ai/color.md), [ai.functions](/docs/ai/functions.md).

## 2. Environment & Configuration
**Environment Lookups:**
- `THEME_PRIMARY` (via `_get_var`)  Primary brand color for headers.
- `THEME_SECONDARY` (via `_get_var`)  Color for dividers and subtitles.
- `THEME_ACCENT` (via `_get_var`)  Color for agent identifiers and highlights.
- `THEME_TEXT` (via `_get_var`)  Standard text color.
- `THEME_OK` (via `_get_var`)  Color for success states.
- `THEME_WARN` (via `_get_var`)  Color for warning/task states.
- `THEME_FAIL` (via `_get_var`)  Color for error states.
- `ICON_PROMPT` (via `os.getenv`)  Glyph used for agent prompts.
- `ICON_SECTION` (via `os.getenv`)  Glyph used for section headers.
- `ICON_SUCCESS` (via `os.getenv`)  Glyph for successful operations.
- `ICON_ERROR` (via `os.getenv`)  Glyph for error states.
- `GLYPH_H_LINE` (via `os.getenv`)  Character used for horizontal dividers.

**Hardcoded Constants:**
- `PRIMARY` (Default: `\033[38;5;214m`)  Fallback primary color.
- `SECONDARY` (Default: `\033[38;5;94m`)  Fallback secondary color.
- `ACCENT` (Default: `\033[38;5;202m`)  Fallback accent color.
- `TEXT` (Default: `\033[38;5;223m`)  Fallback text color.
- `OK` (Default: `\033[38;5;106m`)  Fallback success color.
- `WARN` (Default: `\033[38;5;226m`)  Fallback warning color.
- `FAIL` (Default: `\033[38;5;124m`)  Fallback error color.
- `RESET` (Default: `\033[0m`)  ANSI reset sequence.
- `ICON_AGENT` (Default: ``)  Default agent icon.
- `ICON_ROCKET` (Default: ``)  Default section icon.
- `ICON_SUCCESS` (Default: ``)  Default success icon.
- `ICON_ERROR` (Default: ``)  Default error icon.
- `H_LINE` (Default: ``)  Default divider character.
- `DIVIDER` (Default: `` * 60)  Pre-calculated horizontal line.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `_get_var` | Static Method | Resolves theme variables via environment, `colors.bashrc`, or theme files. |
| `header` | Static Method | Renders a stylized header with a title, subtitle, and dividers. |
| `status` | Static Method | Displays a single-line agent status update (supports in-place updates via `\r`). |
| `auth_request` | Static Method | Renders a boxed UI component for tool/command authorization. |
| `message` | Static Method | Prints a clean, color-coded message from an agent. |
| `log_step` | Static Method | Renders a single-line log entry with a status icon (Success/Fail). |
| `agent_step` | Static Method | Renders a single-line agent progress indicator. |
| `clear_line` | Static Method | Clears the current terminal line using ANSI escape codes. |

## 4. Execution Logic & Flow
- **Initialization**: 
    - The class executes `_get_var` for all theme constants during module load.
    - `_get_var` follows a hierarchical lookup: 1. Environment Variable $\rightarrow$ 2. `~/.source/colors.bashrc` (to find theme name) $\rightarrow$ 3. `~/.source/themes/[theme].bashrc` (to find specific variable) $\rightarrow$ 4. Hardcoded fallback.
    - ANSI escape sequences are processed via `unicode_escape` and `\e` replacement to ensure compatibility.
- **Data Path**: 
    - **Input**: String data (titles, agent names, tasks, commands) and status flags.
    - **Processing**: Strings are wrapped in ANSI color codes and combined with glyphs/icons.
    - **Output**: Formatted strings are passed to `func.out()` for terminal rendering.
- **Conditional Branching**:
    - `_get_var`: Branches based on the existence of environment variables, the existence of the config file, and the existence of the specific theme file.
    - `status`: Uses `is_updating` to decide whether to prepend `\r\033[K` for line overwriting.
    - `log_step`: Selects color and icon based on the `status` string ("SUCCESS" vs others).

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `re`
- **Internal Modules**: 
    - [ai.functions](/docs/ai/functions.md)
    - [Color](/docs/ai/color.md)
- **External Packages**: None identified.