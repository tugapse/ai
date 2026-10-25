## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | Color |
| Source file | color.py |

The **Color** component serves as a centralized utility for managing ANSI escape sequences used to manipulate terminal text appearance. It provides a structured mapping of color constants, background colors, and text effects, ensuring consistent visual styling across the entire CLI-based ecosystem.

**Functional Mission**
The primary responsibility of **Color** is to abstract the complexity of ANSI escape codes into a human-readable class interface. It solves the problem of hardcoded, error-prone escape sequences by providing named constants for foreground colors, background colors, and text decorations (like bold or underline), facilitating a unified aesthetic for terminal output.

**System Context & Integration**
This component acts as a low-level presentation utility. It is designed to be consumed by higher-level output modules, such as [Output Printer](/docs/ai/extras/output_printer.md) or [Terminal UI](/docs/ai/agents/terminal_ui.md), to enhance the readability of logs, status updates, and user interfaces. By providing `format_text` and `pformat_text` functions, it allows other modules to wrap raw strings with styling without needing to manage the `RESET` state manually.

- **INTERNAL REFERENCES**: [Output Printer](/docs/ai/extras/output_printer.md), [Terminal UI](/docs/ai/agents/terminal_ui.md).

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `RESET` (Default: `'\033[0m'`)  Resets all text formatting to default.
- `RED` (Default: `'\033[91m'`)  Bright red foreground.
- `GREEN` (Default: `'\033[92m'`)  Bright green foreground.
- `YELLOW` (Default: `'\033[93m'`)  Bright yellow foreground.
- `BLUE` (Default: `'\033[94m'`)  Bright blue foreground.
- `PURPLE` (Default: `'\033[95m'`)  Bright magenta foreground.
- `CYAN` (Default: `'\033[36m'`)  Cyan foreground.
- `WHITE` (Default: `'\033[37m'`)  White foreground.
- `NORMAL_BLACK` (Default: `'\033[30m'`)  Standard black foreground.
- `NORMAL_RED` (Default: `'\033[31m'`)  Standard red foreground.
- `NORMAL_GREEN` (Default: `'\033[32m'`)  Standard green foreground.
- `NORMAL_YELLOW` (Default: `'\033[33m'`)  Standard yellow foreground.
- `NORMAL_BLUE` (Default: `'\033[34m'`)  Standard blue foreground.
- `NORMAL_MAGENTA` (Default: `'\033[35m'`)  Standard magenta foreground.
- `NORMAL_CYAN` (Default: `'\033[36m'`)  Standard cyan foreground.
- `NORMAL_WHITE` (Default: `'\033[37m'`)  Standard white foreground.
- `NORMAL_LIGHT_GRAY` (Default: `'\033[37m'`)  Alias for standard white.
- `BRIGHT_BLACK` (Default: `'\033[90m'`)  Bright black foreground.
- `BRIGHT_CYAN` (Default: `'\033[96m'`)  Bright cyan foreground.
- `BRIGHT_WHITE` (Default: `'\033[97m'`)  Bright white foreground.
- `BG_BLACK` through `BG_WHITE`  Standard background colors.
- `BG_BRIGHT_BLACK` through `BG_BRIGHT_WHITE`  Bright background colors.
- `BOLD` (Default: `'\033[1m'`)  Bold text effect.
- `DIM` (Default: `'\033[2m'`)  Dim text effect.
- `ITALIC` (Default: `'\033[3m'`)  Italic text effect.
- `UNDERLINE` (Default: `'\033[4m'`)  Underline text effect.
- `BLINK` (Default: `'\033[5m'`)  Blinking text effect.
- `REVERSE` (Default: `'\033[7m'`)  Swaps foreground and background.
- `HIDDEN` (Default: `'\033[8m'`)  Hidden text effect.
- `STRIKETHROUGH` (Default: `'\033[9m'`)  Strikethrough text effect.
- `NO_BOLD_OR_DIM` (Default: `'\033[22m'`)  Disables bold/dim.
- `NO_ITALIC` (Default: `'\033[23m'`)  Disables italic.
- `NO_UNDERLINE` (Default: `'\033[24m'`)  Disables underline.
- `NO_BLINK` (Default: `'\033[25m'`)  Disables blink.
- `NO_REVERSE` (Default: `'\033[27m'`)  Disables reverse.
- `NO_HIDDEN` (Default: `'\033[28m'`)  Disables hidden.
- `NO_STRIKETHROUGH` (Default: `'\033[29m'`)  Disables strikethrough.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `Color` | Class | Container for ANSI escape sequence constants. |
| `format_text` | Func | Returns a string wrapped in provided ANSI codes and a reset code. |
| `pformat_text` | Func | Prints a string wrapped in provided ANSI codes and a reset code to stdout. |

## 4. Execution Logic & Flow
- **Initialization**: The `Color` class is initialized as a static container of string constants representing ANSI escape sequences.
- **Data Path**:
    1. **Input**: A raw string (`text`) and a variable number of ANSI constants (`*colors_and_effects`).
    2. **Processing**: The `colors_and_effects` arguments are joined into a single string of escape codes.
    3. **Output**: The function returns (or prints) a concatenated string: `[Applied Codes] + [Text] + [RESET]`.
- **Conditional Branching**: No complex conditional branching is present; the logic is a linear string concatenation.

## 5. Resource Dependencies
- **Standard Libraries**: None.
- **Internal Modules**: None.
- **External Packages**: None.