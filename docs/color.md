## 1. Architectural Role
Provides a centralized registry of ANSI escape sequences and utility functions for applying text formatting and colorization to terminal output.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `Color` | Class | Acts as a static container for ANSI foreground, background, and text effect constants. |
| `format_text` | Func | Returns a string wrapped in provided ANSI codes and terminated with a reset sequence. |
| `pformat_text` | Func | Prints a string wrapped in provided ANSI codes and terminated with a reset sequence to stdout. |

## 3. Execution Logic & Flow
- **Initialization**: The `Color` class is loaded into memory, initializing a static set of string constants representing ANSI escape sequences.
- **Data Path**: 
    1. **Input**: A target string (`text`) and a variable number of ANSI constants (`*colors_and_effects`).
    2. **Processing**: The `*colors_and_effects` tuple is concatenated into a single string (`applied_codes`).
    3. **Output**: The `applied_codes` are prepended to the `text`, followed by the `Color.RESET` constant, returning a formatted string or printing it to the console.
- **Conditional Branching**: No internal conditional logic; execution follows a linear concatenation and return/print path.

## 4. Resource Dependencies
- **Standard Libraries**: None.
- **Internal Modules**: None.
- **External Packages**: None.

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - ANSI Escape Sequences (e.g., `\033[0m`, `\033[91m`, `\033[40m`, etc.).
    - Text Effect codes (e.g., `\033[1m`, `\033[22m`).
- **Environment Lookups**: None.