## 1. Architectural Role
Provides a high-fidelity terminal interface layer that manages themed ANSI color formatting, glyph-based status indicators, and structured UI components for agent-to-user communication.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `TerminalUI` | Class | Static container for terminal styling and output methods. |
| `_get_var` | Static Method | Resolves theme variables via environment, `.bashrc` config, or hardcoded fallbacks. |
| `header` | Static Method | Renders a themed section header with a title, optional subtitle, and horizontal dividers. |
| `status` | Static Method | Displays a real-time agent activity line with optional carriage return for updates. |
| `auth_request` | Static Method | Renders a boxed visual alert for tool authorization requests. |
| `message` | Static Method | Prints a cleaned, color-coded message from a specific agent. |
| `log_step` | Static Method | Outputs a success or failure indicator for a specific execution step. |
| `clear_line` | Static Method | Erases the current terminal line using ANSI escape codes. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. The class is loaded, triggering the immediate execution of `_get_var` for all theme constants (`PRIMARY`, `SECONDARY`, `ACCENT`, `TEXT`, `OK`, `WARN`, `FAIL`).
    2. `_get_var` sequence: `os.getenv` $\rightarrow$ `~/.source/colors.bashrc` (to find `COLOR_THEME`) $\rightarrow$ `~/.source/themes/[theme].bashrc` $\rightarrow$ Hardcoded Fallback.
    3. Environment variables for icons (`ICON_PROMPT`, `ICON_SECTION`, etc.) and glyphs (`GLYPH_H_LINE`) are resolved.
- **Data Path**: Input (Strings/Booleans) $\rightarrow$ ANSI Escape Sequence Wrapping $\rightarrow$ `functions.out` $\rightarrow$ Terminal Stdout.
- **Conditional Branching**:
    - **Theme Resolution**: If `os.getenv` is null, the logic branches to file system parsing of `.bashrc` files.
    - **Status Updates**: If `is_updating` is `True`, the `status` method prepends `\r\033[K` to overwrite the current line.
    - **Step Logging**: The `log_step` method branches color and icon selection based on whether `status` equals `"SUCCESS"`.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `re`
- **Internal Modules**: `functions` (aliased as `func`), `color` (imported as `Color`)
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - Default ANSI colors (e.g., `\033[38;5;214m` for `PRIMARY`).
    - Default Icons: ``, ``, ``, ``.
    - Default Divider: `` multiplied by 60.
- **Environment Lookups**: 
    - `THEME_PRIMARY`, `THEME_SECONDARY`, `THEME_ACCENT`, `THEME_TEXT`, `THEME_OK`, `THEME_WARN`, `THEME_FAIL`.
    - `ICON_PROMPT`, `ICON_SECTION`, `ICON_SUCCESS`, `ICON_ERROR`.
    - `GLYPH_H_LINE`.
    - `COLOR_THEME` (parsed from `~/.source/colors.bashrc`).