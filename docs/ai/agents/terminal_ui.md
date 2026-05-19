## 1. Architectural Role
| Name | Source file |
| :--- | :--- |
| TerminalUI | [/src/ai/agents/terminal_ui.py](/src/ai/agents/terminal_ui.py) |

The TerminalUI component acts as the high-fidelity presentation layer for terminal-based interactions within the AI agent ecosystem. 

It centralizes theming, colorization, and consistent formatting of console output. By loading theme variables from environment or fallbacks and providing a suite of static methods for common UI actions (header, status updates, authorization prompts, messages, and step logging), it ensures a unified and visually coherent user experience across agents and tools. As the central hub for output.

In the broader system, TerminalUI serves as the interface through which agents communicate progress, results, and prompts to users. It collaborates with the Color abstraction and the output utility ([functions](/docs/ai/functions.md) as func) to render colored, styled messages, dividers, and banners.

The class-level constants and methods are designed to be globally accessible, allowing downstream modules to call into a consistent UI surface without embedding formatting logic.

## 2. Environment & Configuration
**Environment Lookups:**

| Name | Description |
| :--- | :--- |
| `THEME_PRIMARY` | Primary color for UI accents (via `_get_var`). |
| `THEME_SECONDARY` | Secondary UI color (via `_get_var`). |
| `THEME_ACCENT` | Accent color for emphasis (via `_get_var`). |
| `THEME_TEXT` | Text color within UI elements (via `_get_var`). |
| `THEME_OK` | Color used for success/status OK indicators (via `_get_var`). |
| `THEME_WARN` | Color used for warnings (via `_get_var`). |
| `THEME_FAIL` | Color used for failures (via `_get_var`). |
| `ICON_PROMPT` | Icon used for agent prompts (default: ). |
| `ICON_SECTION` | Icon used for sections (default: ). |
| `ICON_SUCCESS` | Icon used for successful steps (default: ). |
| `ICON_ERROR` | Icon used for errors (default: ). |
| `GLYPH_H_LINE` | Horizontal line glyph (default: ). |

- If none identified, behavior falls back to the provided defaults and hardcoded fallbacks.

**Hardcoded Constants:**
- RESET (Default: `"\033[0m"`)  ANSI reset sequence to revert styling after colored output.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| TerminalUI | Class | Provides static methods for terminal formatting and messaging: header, status, auth_request, message, log_step, clear_line. Centralizes theming, icons, dividers, and consistent output formatting for AI agent interactions. |

## 4. Code Example
- Example usage:
  - TerminalUI.header("Startup","Initializing components")
  - TerminalUI.status("Indexer","Loading data", is_updating=True)
  - TerminalUI.auth_request("Sensitive Tool","Data Vault","sudo access")

```python
# Example usage snippet
from ai.agents.terminal_ui import TerminalUI

TerminalUI.header("Startup","Initializing components")
TerminalUI.status("Indexer","Loading data", is_updating=True ) # is_updating will move cursor to begining of the line 
TerminalUI.auth_request("execute_command","Agent 1","ls -la /tmp")
```

## 5. Execution Logic & Flow
- Initialization
  - On import-time evaluation, class attributes PRIMARY, SECONDARY, ACCENT, TEXT, OK, WARN, FAIL are computed by _get_var, which attempts environment resolution, then theme file parsing, then a hardcoded fallback.
  - ICON_AGENT, ICON_ROCKET, ICON_SUCCESS, ICON_ERROR resolve from environment with specified defaults. H_LINE resolves from GLYPH_H_LINE with a default, and DIVIDER derives from H_LINE.
- Data Path
  - header(title, subtitle) prints a styled divider, a bolded title with an rocket-style icon, optional subtitle, and a trailing divider.
  - status(agent_name, task, is_updating) prints an updating line with agent name and task using accent and warn colors.
  - auth_request(tool_name, target, command="") renders a boxed authorization request with optional command, using a dedicated color composition.
  - message(agent_name, text, color) prints a colored message line.
  - log_step(step_name, status="SUCCESS") outputs a colored step indicator with a corresponding icon.
  - clear_line() clears the current terminal line.
- Conditional Branching
  - _get_var: if environment variable found, uses it; else tries theme file parsing; else falls back to a default string.
  - subtitle handling in header is conditional (only prints if provided).
  - auth_request includes an optional command line; if not provided, only tool/target lines render.

## 6. Resource Dependencies
- **Standard Libraries**:
  - os
  - re
- **Internal Modules**:
  - [ai.functions](/docs/ai/functions.md)  generic utility for output streams (func.out).
  - [Color](/docs/ai/color.md)  color constants and formatting referenced in UI rendering.
- **External Packages**:
  - None
