## 1. Architectural Role
Handles high-fidelity terminal formatting, icons, and layout for the Unified Architect system.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `TerminalUI` | Class | Manages terminal UI components such as headers, status updates, authorization requests, messages, and log steps. |
| `header` | Static Method | Prints a major section header with a title and optional subtitle. |
| `status` | Static Method | Displays an agent's current working status. |
| `auth_request` | Static Method | Displays a boxed authorization request. |
| `message` | Static Method | Prints a message from an agent to the user. |
| `log_step` | Static Method | Logs a stage completion with a status icon. |
| `clear_line` | Static Method | Clears the current terminal line. |

## 3. Execution Logic & Flow
- **Initialization**: No initialization logic is present.
- **Data Path**: Input data (e.g., agent name, task, tool name) is processed and output to the terminal.
- **Conditional Branching**: The `status` method uses a conditional to determine whether to overwrite the line or not.

## 4. Resource Dependencies
- **Standard Libraries**: `None`
- **Internal Modules**: `functions as func`, `color as Color`
- **External Packages**: `None`

## 5. Configuration & Environment
- **Hardcoded Constants**: `ICON_AGENT`, `ICON_SUCCESS`, `ICON_ERROR`, `ICON_WAIT`, `ICON_ROCKET`, `ICON_TOOL`, `ICON_LOCK`, `DIVIDER`
- **Environment Lookups**: `None`