## 1. Architectural Role
Manages text formatting using ANSI escape codes for colors and effects.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `Color` | Class | Defines constants for various text colors, effects, and backgrounds. |
| `format_text` | Function | Formats text with specified ANSI codes and resets the color. |
| `pformat_text` | Function | Prints formatted text with specified ANSI codes and resets the color. |

## 3. Execution Logic & Flow
- **Initialization**: No initialization required.
- **Data Path**: 
  1. `format_text` takes `text` and `*colors_and_effects`.
  2. Joins `colors_and_effects` into a single string.
  3. Returns the formatted string with `text` and `Color.RESET`.
- **Conditional Branching**: None.

## 4. Resource Dependencies
- **Standard Libraries**: None.
- **Internal Modules**: None.
- **External Packages**: None.

## 5. Configuration & Environment
- **Hardcoded Constants**: 
  - `RESET`: `\033[0m`
  - `RED` to `BRIGHT_WHITE`: Various ANSI escape codes for colors.
  - `BG_BLACK` to `BG_BRIGHT_WHITE`: Various ANSI escape codes for background colors.
  - `BOLD` to `STRIKETHROUGH`: Various ANSI escape codes for text effects.
  - `NO_BOLD_OR_DIM` to `NO_STRIKETHROUGH`: Various ANSI escape codes to disable effects.
- **Environment Lookups**: None.