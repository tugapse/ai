## Module Purpose
This file defines a `Color` class containing a comprehensive set of ANSI escape codes for text formatting (foreground and background colors, and text effects) and provides utility functions to apply these codes to strings for terminal output.

## Interface & Exports
*   Class: `Color`
*   Function: `format_text`
*   Function: `pformat_text`

## Internal Logic
The `Color` class is a collection of static string attributes, each representing a specific ANSI escape code for terminal formatting. These attributes cover text reset, standard and bright foreground colors, standard and bright background colors, and various text effects (e.g., bold, underline, italic). The `format_text` function concatenates multiple provided `Color` attributes with the input `text` and appends `Color.RESET` to ensure the terminal state is restored. The `pformat_text` function performs the same formatting but prints the result directly to standard output.

## Dependencies
None identified in source.

## Constants & Environment
*   `Color.RESET`
*   `Color.RED`
*   `Color.GREEN`
*   `Color.YELLOW`
*   `Color.BLUE`
*   `Color.PURPLE`
*   `Color.CYAN`
*   `Color.NORMAL_BLACK`
*   `Color.NORMAL_RED`
*   `Color.NORMAL_GREEN`
*   `Color.NORMAL_YELLOW`
*   `Color.NORMAL_BLUE`
*   `Color.NORMAL_MAGENTA`
*   `Color.NORMAL_CYAN`
*   `Color.NORMAL_WHITE`
*   `Color.NORMAL_LIGHT_GRAY`
*   `Color.BRIGHT_BLACK`
*   `Color.BRIGHT_CYAN`
*   `Color.BRIGHT_WHITE`
*   `Color.BG_BLACK`
*   `Color.BG_RED`
*   `Color.BG_GREEN`
*   `Color.BG_YELLOW`
*   `Color.BG_BLUE`
*   `Color.BG_MAGENTA`
*   `Color.BG_CYAN`
*   `Color.BG_WHITE`
*   `Color.BG_BRIGHT_BLACK`
*   `Color.BG_BRIGHT_RED`
*   `Color.BG_BRIGHT_GREEN`
*   `Color.BG_BRIGHT_YELLOW`
*   `Color.BG_BRIGHT_BLUE`
*   `Color.BG_BRIGHT_MAGENTA`
*   `Color.BG_BRIGHT_CYAN`
*   `Color.BG_BRIGHT_WHITE`
*   `Color.BOLD`
*   `Color.DIM`
*   `Color.ITALIC`
*   `Color.UNDERLINE`
*   `Color.BLINK`
*   `Color.REVERSE`
*   `Color.HIDDEN`
*   `Color.STRIKETHROUGH`
*   `Color.NO_BOLD_OR_DIM`
*   `Color.NO_ITALIC`
*   `Color.NO_UNDERLINE`
*   `Color.NO_BLINK`
*   `Color.NO_REVERSE`
*   `Color.NO_HIDDEN`
*   `Color.NO_STRIKETHROUGH`