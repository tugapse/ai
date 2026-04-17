

## 1. Architectural Role  
Provides terminal UI formatting with color themes, icons, and status indicators, loading configurations from environment variables or theme files.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `TerminalUI` | Class | Central hub for terminal UI formatting, color themes, and status display |  
| `_get_var` | Static Method | Retrieves environment variables or theme file values with fallback logic |  
| `PRIMARY`, `SECONDARY`, `ACCENT`, `TEXT`, `OK`, `WARN`, `FAIL`, `RESET` | Class Variables | Predefined color codes for UI elements |  
| `ICON_AGENT`, `ICON_ROCKET`, `ICON_SUCCESS`, `ICON_ERROR`, `H_LINE`, `DIVIDER` | Class Variables | Predefined icons and glyphs for UI components |  
| `header` | Static Method | Renders a section header with title and subtitle |  
| `status` | Static Method | Displays agent task status with progress updates |  
| `auth_request` | Static Method | Renders a boxed authorization request prompt |  
| `message` | Static Method | Outputs messages from agents to the user |  
| `log_step` | Static Method | Logs step execution status with success/error indicators |  
| `clear_line` | Static Method | Clears the terminal line for dynamic updates |  

## 3. Execution Logic & Flow  
- **Initialization**: Loads `TerminalUI` class with precomputed color codes via `_get_var`, using environment variables or theme files.  
- **Data Path**: Input (environment/config)  `_get_var` processes variable retrieval  color codes and icons are stored as class variables  methods like `header`/`status` use these values for output formatting.  
- **Conditional Branching**:  
  - `_get_var` checks `os.getenv(env_name)` first; if absent, parses `colors.bashrc` for theme file paths.  
  - If theme file exists, searches for `env_name` in its content to extract values.  
  - Falls back to hardcoded color codes if no match is found.  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `re`  
- **Internal Modules**: `functions`, `color`  
- **External Packages**: None  

## 5. Configuration & Environment  
- **Hardcoded Constants**:  
  - `\033[38;5;214m`, `\033[38;5;94m`, `\033[38;5;202m`, `\033[38;5;223m`, `\033[38;5;106m`, `\033[38;5;226m`, `\033[38;5;124m` (fallback color codes)  
- **Environment Lookups**:  
  - `THEME_PRIMARY`, `THEME_SECONDARY`, `THEME_ACCENT`, `THEME_TEXT`, `THEME_OK`, `THEME_WARN`, `THEME_FAIL`  
  - `ICON_PROMPT`, `ICON_SECTION`, `ICON_SUCCESS`, `ICON_ERROR`, `GLYPH_H_LINE`  
  - `~/.source/colors.bashrc`, `~/.source/themes` (theme file paths)