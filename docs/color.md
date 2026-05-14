## 1. Architectural Role
Acts as a centralized utility provider for ANSI escape sequence management, facilitating terminal text styling through colorization and text effects. It provides a structured schema of constants for foreground/background colors and text attributes, serving as a low-level aesthetic dependency for higher-level UI components such as [agents/terminal_ui](agents/terminal_ui.md) and [extras/console](extras/console.md).

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
- `Color.RESET` (Default: `'\033[0m'`)  Resets all terminal styling.
- `Color.RED` (Default: `'\033[91m'`)  Bright red foreground.
- `Color.GREEN` (Default: `'\033[92m'`)  Bright green foreground.
- `Color.YELLOW` (Default: `'\033[93m'`)  Bright yellow foreground.
- `Color.BLUE` (Default: `'\033[94m'`)  Bright blue foreground.
- `Color.PURPLE` (Default: `'\033[95m'`)  Bright magenta foreground.
- `Color.CYAN` (Default: `'\033[36m'`)  Cyan foreground.
- `Color.WHITE` (Default: `'\033[37m'`)  White foreground.
- `Color.NORMAL_BLACK` (Default: `'\033[30m'`)  Standard black foreground.
- `Color.NORMAL_RED` (Default: `'\033[31m'`)  Standard red foreground.
- `Color.NORMAL_GREEN` (Default: `'\033[32m'`)  Standard green foreground.
- `Color.NORMAL_YELLOW` (Default: `'\033[33m'`)  Standard yellow foreground.
- `Color.NORMAL_BLUE` (Default: `'\033[34m'`)  Standard blue foreground.
- `Color.NORMAL_MAGENTA` (Default: `'\033[35m'`)  Standard magenta foreground.
- `Color.NORMAL_CYAN` (Default: `'\033[36m'`)  Standard cyan foreground.
- `Color.NORMAL_WHITE` (Default: `'\033[37m'`)  Standard white foreground.
- `Color.NORMAL_LIGHT_GRAY` (Default: `'\033[37m'`)  Alias for `NORMAL_WHITE`.
- `Color.BRIGHT_BLACK` (Default: `'\033[90m'`)  Bright black foreground.
- `Color.BRIGHT_CYAN` (Default: `'\033[96m'`)  Bright cyan foreground.
- `Color.BRIGHT_WHITE` (Default: `'\033[97m'`)  Bright white foreground.
- `Color.BG_BLACK` (Default: `'\033[40m'`)  Black background.
- `Color.BG_RED` (Default: `'\033[41m'`)  Red background.
- `Color.BG_GREEN` (Default: `'\033[42m'`)  Green background.
- `Color.BG_YELLOW` (Default: `'\033[43m'`)  Yellow background.
- `Color.BG_BLUE` (Default: `'\033[44m'`)  Blue background.
- `Color.BG_MAGENTA` (Default: `'\033[45m'`)  Magenta background.
- `Color.BG_CYAN` (Default: `'\033[46m'`)  Cyan background.
- `Color.BG_WHITE` (Default: `'\033[47m'`)  White background.
- `Color.BG_BRIGHT_BLACK` (Default: `'\033[100m'`)  Bright black background.
- `Color.BG_BRIGHT_RED` (Default: `'\033[101m'`)  Bright red background.
- `Color.BG_BRIGHT_GREEN` (Default: `'\033[102m'`)  Bright green background.
- `Color.BG_BRIGHT_YELLOW` (Default: `'\033[103m'`)  Bright yellow background.
- `Color.BG_BRIGHT_BLUE` (Default: `'\033[104m'`)  Bright blue background.
- `Color.BG_BRIGHT_MAGENTA` (Default: `'\033[105m'`)  Bright magenta background.
- `Color.BG_BRIGHT_CYAN` (Default: `'\033[106m'`)  Bright cyan background.
- `Color.BG_BRIGHT_WHITE` (Default: `'\033[107m'`)  Bright white background.
- `Color.BOLD` (Default: `'\033[1m'`)  Bold text effect.
- `Color.DIM` (Default: `'\033[2m'`)  Dim text effect.
- `Color.ITALIC` (Default: `'\033[3m'`)  Italic text effect.
- `Color.UNDERLINE` (Default: `'\033[4m'`)  Underline text effect.
- `Color.BLINK` (Default: `'\033[5m'`)  Blinking text effect.
- `Color.REVERSE` (Default: `'\033[7m'`)  Swaps foreground/background.
- `Color.HIDDEN` (Default: `'\033[8m'`)  Hidden text effect.
- `Color.STRIKETHROUGH` (Default: `'\033[9m'`)  Strikethrough text effect.
- `Color.NO_BOLD_OR_DIM` (Default: `'\033[22m'`)  Disables bold/dim.
- `Color.NO_ITALIC` (Default: `'\033[23m'`)  Disables italic.
- `Color.NO_UNDERLINE` (Default: `'\033[24m'`)  Disables underline.
- `Color.NO_BLINK` (Default: `'\033[25m'`)  Disables blink.
- `Color.NO_REV_ERSE` (Default: `'\033[27m'`)  Disables reverse.
- `Color.NO_HIDDEN` (Default: `'\033[28m'`)  Disables hidden.
- `Color.NO_STRIKETHROUGH` (Default: `'\033[29m'`)  Disables strikethrough.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `Color` | Class | Container for ANSI escape sequence constants (colors and effects). |
| `format_text` | Func | Returns a string wrapped in the provided ANSI codes and a reset sequence. |
| `pformat_text` | Func | Prints a string to stdout wrapped in the provided ANSI codes and a reset sequence. |

## 4. Execution Logic & Flow
- **Initialization**: The `Color` class is loaded into memory with static string attributes representing ANSI codes.
- **Data Path**:
    1. **Input**: Receives `text` (str) and variable positional arguments `*colors_and_effects` (ANSI strings).
    2. **Processing**: Concatenates the `colors_and_effects` into a single `applied_codes` string via `"".join()`.
    3. **Transformation**: Wraps the input text between `applied_codes` and `Color.RESET`.
    4. **Output**: `format_text` returns the transformed string; `pformat_text` sends the transformed string to `print()`.
- **Conditional Branching**: No internal logical branching; execution is linear.

## 5. Resource Dependencies
- **Standard Libraries**: None.
- **Internal Modules**: None.
- **External Packages**: None.