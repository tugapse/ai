## 1. Architectural Role
Acts as a text-to-speech middleware that filters markdown formatting, handles code-block suppression with auditory notifications, and buffers text into complete sentences for optimized voice synthesis.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SpeechBridge` | Class | Orchestrates the transformation of raw LLM text streams into voice-ready chunks. |
| `feed` | Method | Primary entry point for incoming text; manages code-block state and triggers processing. |
| `flush` | Method | Forces the remaining buffered text to be sent to the voice module. |
| `abort` | Method | Clears buffers, resets state, and signals the voice module to stop playback. |

## 3. Execution Logic & Flow
- **Initialization**: Sets `voice_module` reference, `debug` flag, initializes an empty `buffer` string, sets `in_code_block` to `False`, and compiles `sentence_regex` for punctuation-based splitting.
- **Data Path**: 
    1. `feed(text)` $\rightarrow$ Checks for ``` markers.
    2. If in code block $\rightarrow$ Suppress text; if entering code block $\rightarrow$ Trigger random `code_announcements` via `_send_to_voice`.
    3. If not in code block $\rightarrow$ `_process_text_chunk(text)`.
    4. `_process_text_chunk` $\rightarrow$ Strip headers (`#`), bold/italic (`*`), and list markers $\rightarrow$ Convert file paths via `_replace_path_for_voice`.
    5. Append to `buffer` $\rightarrow$ Scan for `sentence_regex` matches.
    6. If match found $\rightarrow$ Slice buffer at `split_point` $\rightarrow$ `_send_to_voice(chunk)`.
    7. `_send_to_voice` $\rightarrow$ Strip backticks $\rightarrow$ Optional `func.out` debug log $\rightarrow$ `voice.process_token()`.
- **Conditional Branching**:
    - **Code Block Toggle**: If ` ``` ` is detected, `in_code_block` is flipped, diverting text from the voice pipeline to a static announcement.
    - **Sentence Completion**: Text is only dispatched to the voice module once a terminal punctuation mark (`.`, `?`, `!`) is encountered.
    - **Debug Mode**: If `self.debug` is True, the processed voice string is printed to the console via `func.out`.

## 4. Resource Dependencies
- **Standard Libraries**: `re`, `random`, `typing.Any`
- **Internal Modules**: `color.Color`, `color.format_text`, `functions` (aliased as `func`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `code_announcements`: List of 5 strings used to notify the user of on-screen code.
    - `sentence_regex`: `r'[.?!]+["\']*(?=\s|\n|$)'`
    - Path regex: `r'/(?P<path_content>[\w./-]+)'`