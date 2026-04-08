## Module Purpose
This module defines the `FileContentHandler` class, which is responsible for detecting, extracting, and saving file content embedded within `<file>...</file>` tags from an LLM's token stream, suppressing the content from direct console output.

## Interface & Exports
*   `FileContentHandler`: A class designed to be instantiated and used to process token streams, managing the state of file content extraction and saving. Its primary public methods are `__init__`, `process_token`, and `save_file`.

## Internal Logic
The `FileContentHandler` class processes incoming tokens, accumulating them in an internal buffer. It uses regular expressions (`FILE_START_PATTERN`, `FILE_END_PATTERN`) to identify the opening and closing `<file>` tags, which can include `name`, `type`, and `ext` attributes. When an opening tag is found, it extracts metadata, sets an internal `_is_active` flag, and begins buffering subsequent tokens as file content. Upon detecting a closing tag, it finalizes the filename (inferring extensions from `name`, `type`, or `ext` attributes and `MIME_TYPE_TO_EXT` mapping), cleans control characters from the buffered content, and then calls its `save_file` method to write the extracted content to a specified `_output_base_dir`. During active file content accumulation, tokens are suppressed from being returned for display.

## Dependencies
*   `re`
*   `os`
*   `functions` (imported as `func`)
*   `extras.thinking_log_manager` (specifically `ThinkingLogManager`)

## Constants & Environment
*   `FILE_START_PATTERN`: A regular expression to match the opening `<file>` tag and capture its attributes.
*   `FILE_END_PATTERN`: A regular expression to match the closing `</file>` tag.
*   `CONTROL_CHARS_PATTERN`: A regular expression to identify and remove control characters from token strings.
*   `MIME_TYPE_TO_EXT`: A dictionary mapping common MIME types to file extensions.
*   `end_file_string`: An instance variable set to `"[FILE_END]"`.
None identified in source.