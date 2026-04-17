## 1. Architectural Role
Provides a centralized repository of ANSI escape sequences and utility functions for applying terminal text styling and colorization.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `Color` | Class | Static container for ANSI escape codes (Foreground, Background, and Text Effects). |
| `format_text` | Func | Concatenates style codes with text and appends a reset sequence to return a formatted string. |
| `pformat_text` | Func | Wraps `format_text` logic to directly print the styled output to the console. |

## 3. Execution Logic & Flow
- **Initialization**: The `Color` class is loaded into memory, initializing a set of static string constants representing ANSI escape codes.
- **Data Path**: 
    1. **Input**: A string (`text`) and a variable number of style constants (`*colors_and_effects`) are passed to `format_text` or `pformat_text`.
    2. **Processing**: The `colors_and_effects` tuple is joined into a single prefix string.
    3. **Output**: The prefix, the original text, and `Color.RESET` are concatenated into a final ANSI-encoded string.
- **Conditional Branching**: No conditional branching logic is implemented; the flow is linear and deterministic.

## 4. Resource Dependencies
- **Standard Libraries**: None.
- **Internal Modules**: None.
- **External Packages**: None.

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - Foreground colors (e.g., `RED = '\033[91m'`, `NORMAL_BLUE = '\033[34m'`).
    - Background colors (e.g., `BG_BLACK = '\033[40m'`, `BG_BRIGHT_WHITE = '\033[107m'`).
    - Text effects (e.g., `BOLD = '\033[1m'`, `UNDERLINE = '\033[4m'`).
    - Reset code (`RESET = '\033[0m'`).
- **Environment Lookups**: None.