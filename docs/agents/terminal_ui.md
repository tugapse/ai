## 1. Architectural Role
`TerminalUI` serves as the high-fidelity presentation layer for the agentic system, responsible for translating abstract system states, agent activities, and authorization requests into visually structured terminal output. It implements a sophisticated theme-loading mechanism that prioritizes environment variables, falls back to a local `.bashrc` configuration, and finally utilizes hardcoded ANSI escape sequences. The class provides standardized UI components such as headers, status updates, and boxed authorization prompts to ensure a consistent user experience across agent interactions.

## 2. Environment & Configuration
**Environment Lookups:**
- `THEME_PRIMARY` (via `_get_var`)  Primary color for headings and icons.
- `THEME_SECONDARY` (via `_get_var`)  Color for dividers and decorative elements.
- `THEME_ACCENT` (via `_get_var`)  Color for agent status identifiers.
- `THEME_TEXT` (via `_get_var`)  Color for standard descriptive text.
- `THEME_OK` (via `_get_var`)  Color for success indicators.
- `THEME_WARN` (via `_get_var`)  Color for warning/task descriptions.
- `THEME_FAIL` (via `_get_var`)  Color for error indicators.
- `ICON_PROMPT` (via `os.getenv`)  Glyph used for agent identification.
- `ICON_SECTION` (via `os.getenv`)  Glyph used for section headers.
- `ICON_SUCCESS` (via `os.getenv`)  Glyph for successful step completion.
- `ICON_ERROR` (via `os.getenv`)  Glyph for failed step completion.
- `GLYPH_H_LINE` (via `os.getenv`)  Character used for horizontal dividers.

**Hardcoded Constants:**
- `PRIMARY` (Default: `\033[38;5;214m`)  Fallback primary color.
- `SECONDARY` (Default: `\033[38;5;94m`)  Fallback secondary color.
- `ACCENT` (Default: `\033[38;5;202m`)  Fallback accent color.
- `TEXT` (Default: `\033[38;5;223m`)  Fallback text color.
- `OK` (Default: `\033[38;5;106m`)  Fallback success color.
- `WARN` (Default: `\033[38;5;226m`)  Fallback warning color.
- `FAIL` (Default: `\033[38;5;124m`)  Fallback failure color.
- `RESET` (Default: `\033[0m`)  ANSI reset sequence.
- `ICON_AGENT` (Default: ``)  Default agent icon.
- `ICON_ROCKET` (Default: ``)  Default header icon.
- `ICON_SUCCESS` (Default: ``)  Default success icon.
- `ICON_ERROR` (Default: ``)  Default error icon.
- `H_LINE` (Default: ``)  Default divider character.
- `DIVIDER` (Default: `` * 60)  Generated horizontal line.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `TerminalUI` | Class | Static container for all terminal formatting and display logic. |
| `_get_var` | Method | Orchestrates hierarchical theme variable retrieval (Env  Bashrc  Fallback). |
| `header` | Method | Renders a high-visibility title block with dividers and an icon. |
| `status` | Method | Renders a single-line, updatable agent activity notification. |
| `auth_request` | Method | Renders a framed/boxed UI component for tool authorization prompts. |
| `message` | Method | Prints formatted text strings from agents using specific color profiles. |
| `log_step` | Method | Renders a status line (Success/Fail) for specific workflow steps. |
| `clear_line` | Method | Executes an ANSI escape sequence to clear the current terminal line. |

## 4. Execution Logic & Flow
- **Initialization**: 
    - The class performs immediate execution of `_get_var` for all theme constants during module import.
    - `_get_var` executes a 4-stage lookup: 1. Check `os.environ`; 2. Check `~/.source/colors.bashrc` for theme name; 3. Parse theme file in `~/.source/themes/`; 4. Return hardcoded fallback.
    - Strings are processed through `unicode_escape` to handle `\e` to `\033` conversions.
- **Data Path**: 
    - **Input**: String data (titles, agent names, tasks, commands) and status flags.
    - **Processing**: Injection of ANSI color codes from the initialized theme constants and concatenation with glyphs.
    - **Output**: Formatted escape sequences sent to standard output via `func.out`.
- **Conditional Branching**: 
    - `_get_var`: Branches between environment existence, config file existence, theme file existence, and final fallback.
    - `status`: Branches logic based on `is_updating` to determine if a carriage return/clear sequence (`\r\033[K`) is prepended.
    - `log_step`: Branches color and icon selection based on the `status` string.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `re`
- **Internal Modules**: 
    - [functions](functions.md)
    - [color](color.md)
- **External Packages**: None identified.