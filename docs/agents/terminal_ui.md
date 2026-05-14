## 1. Architectural Role
Provides a high-fidelity terminal presentation layer by resolving theme-based ANSI escape sequences and rendering structured UI components like headers, status updates, and authorization boxes.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `TerminalUI` | Class | Static container for theme resolution and UI rendering methods. |
| `_get_var` | Method | Resolves color/glyph values via environment, `.bashrc` config, or theme files. |
| `header` | Method | Renders a decorated title block with dividers and icons. |
| `status` | Method | Displays an agent's current task with support for in-place line updates. |
| `auth_request` | Method | Renders a structured visual box for tool/command authorization. |
| `message` | Method | Outputs agent-generated text with specified color formatting. |
| `log_step` | Method | Renders a single-line execution step with success/error icons. |
| `clear_line` | Method | Executes a carriage return and line clear ANSI sequence. |

## 3. Execution Logic & Flow
- **Initialization**: Upon class loading, `_get_var` is invoked for all theme constants (`PRIMARY`, `SECONDARY`, etc.). This triggers a hierarchical lookup: `os.getenv` $\rightarrow$ `~/.source/colors.bashrc` parsing $\rightarrow$ `~/.source/themes/[THEME].bashrc` parsing $\rightarrow$ Hardcoded fallback.
- **Data Path**: 
    1. **Input**: String parameters (titles, tasks, messages) and environment variables.
    2. **Processing**: ANSI escape sequences are decoded via `unicode_escape` and `replace('\\e', '\033')` to ensure valid terminal control characters.
    3. **Output**: Formatted strings are passed to `func.out()` for terminal emission.
- **Conditional Branching**:
    - `_get_var`: Checks environment existence $\rightarrow$ checks config file existence $\rightarrow$ checks theme file existence $\rightarrow$ returns fallback.
    - `status`: Checks `is_updating` boolean to determine if a carriage return (`\r`) and clear sequence (`\033[K`) should be prepended.
    - `log_step`: Evaluates `status == "SUCCESS"` to select specific `OK`/`FAIL` colors and icons.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `re`
- **Internal Modules**: `functions` (as `func`), `color` (as `Color`)
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - Default ANSI colors (e.g., `\033[38;5;214m`)
    - Default icons (``, ``, ``, ``)
    - `DIVIDER` length (60)
    - Config paths (`~/.source/colors.bashrc`, `~/.source/themes`)
- **Environment Lookups**: 
    - `THEME_PRIMARY`, `THEME_SECONDARY`, `THEME_ACCENT`, `THEME_TEXT`
    - `THEME_OK`, `THEME_WARN`, `THEME_FAIL`
    - `ICON_PROMPT`, `ICON_SECTION`, `ICON_SUCCESS`, `ICON_ERROR`
    - `GLYPH_H_LINE`
    - `COLOR_THEME` (via `colors.bashrc` parsing)