## 1. Architectural Role
Acts as a text-to-speech intermediary that sanitizes, filters, and segments raw text streams into natural-sounding phonetic chunks while suppressing code block content.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SpeechBridge` | Class | Manages the lifecycle of text processing, buffering, and voice dispatching. |
| `__init__` | Method | Initializes the voice module, debug state, text buffer, and regex patterns. |
| `feed` | Method | Ingests raw text, detects code block boundaries, and triggers processing or announcements. |
| `_replace_path_for_voice` | Method | Transforms file paths (e.g., `/path/to/file`) into spoken-friendly formats (`, path to file`). |
| `_process_text_chunk` | Method | Cleans Markdown/formatting, transforms paths, and buffers text until a sentence boundary is met. |
| `flush` | Method | Forces the immediate dispatch of any remaining text in the buffer to the voice module. |
| `_send_to_voice` | Method | Performs final cleanup of backticks and routes the string to the `voice_module.process_token` method. |
| `abort` | Method | Clears the internal buffer, resets code block state, and signals the voice module to stop. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Assigns `voice_module` and `debug` flag.
    2. Initializes `buffer` as an empty string.
    3. Sets `in_code_block` to `False`.
    4. Pre-compiles `sentence_regex` for punctuation-based splitting.
- **Data Path**: 
    1. **Input**: `feed(text)` receives a raw string.
    2. **Segmentation**: If ` ``` ` is detected, the string is split; text within blocks is ignored for speech, while the transition triggers a `code_announcements` selection.
    3. **Sanitization**: `_process_text_chunk` removes headers (`#`), bold/italic markers (`*`), and list markers (`1.`, `-`).
    4. **Transformation**: `re.sub` identifies paths and uses `_replace_path_for_voice` to swap `/` with spaces.
    5. **Buffering**: Text is appended to `self.buffer` until `sentence_regex` identifies a terminal punctuation mark.
    6. **Output**: `_send_to_voice` strips backticks and calls `self.voice.process_token(cleaned_text)`.
- **Conditional Branching**:
    - `if " ``` " in text`: Determines if the input requires code-block logic or standard processing.
    - `if self.in_code_block`: Decides whether to process text for speech or treat it as technical data to be ignored.
    - `if matches`: Determines if the current buffer contains a complete sentence ready for dispatch.
    - `if self.debug`: Controls whether to output processed text to the console via `func.out`.

## 4. Resource Dependencies
- **Standard Libraries**: `re`, `random`, `typing`
- **Internal Modules**: `color` (Color, format_text), `functions` (func)
- **External Packages**: None explicitly listed (relies on `voice_module` injection)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `code_announcements`: List of strings used to notify the user of code displays.
    - `sentence_regex`: Pattern `[.?!]+["\']*(\s|\n|$)`.
- **Environment Lookups**: None.