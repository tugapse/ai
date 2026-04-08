## Module Purpose
This file defines classes for reading chat message data from a JSON file and formatting its content with specific color schemes for console output, including special handling for code blocks.

## Interface & Exports
*   Class: `ConsoleChatReader`
*   Class: `ConsoleTokenFormatter`
*   Method: `ConsoleChatReader.load`

## Internal Logic
The `ConsoleChatReader` class initializes with a `filename` and utilizes a `ConsoleTokenFormatter` instance. Its `load` method reads a JSON file, parses it into a list of chat messages, and then iterates through these messages, invoking `_print_chat` for each. The `_print_chat` method filters out `ChatRoles.SYSTEM` messages, determines the appropriate color (`Color.BLUE` for `ChatRoles.USER`, `Color.YELLOW` otherwise) and prefix, then processes the message content using `color_text`. The `color_text` method tokenizes the content by spaces and applies formatting to each token via `ConsoleTokenFormatter.process_token`. The `ConsoleTokenFormatter` manages a `printing_block` state to toggle color (`Color.YELLOW` and `Color.RESET`) when tokens containing '``' are encountered, effectively highlighting blocks of text. The `clear_process_token` method resets the `printing_block` state.

## Dependencies
*   `json`
*   `pathlib.Path`
*   `color`
*   `core.ChatRoles`
*   `functions as func`

## Constants & Environment
*   Hardcoded dictionary key: `printing_block` within `ConsoleTokenFormatter.token_states`.