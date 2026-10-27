## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | SpeechBridge |
| Source file | speech_bridge.py |

The **SpeechBridge** component serves as a specialized text-to-speech (TTS) preprocessing layer designed to sanitize and transform raw LLM text outputs into a format optimized for natural auditory synthesis. It acts as a buffer and filter between the text generation engine and the voice synthesis module, ensuring that non-verbal elements like Markdown syntax, code blocks, and technical file paths do not disrupt the flow of spoken language.

**Functional Mission**
The primary responsibility of **SpeechBridge** is to intercept raw text streams and perform "auditory cleaning." It solves the problem of "robotic" or "cluttered" speech by stripping Markdown formatting (bold, italics, headers), handling code blocks through verbal announcements rather than literal reading, and transforming technical file paths into human-readable spoken phrases.

**System Context & Integration**
This component sits within the voice module hierarchy, acting as a middleware between the text-producing modules and the `voice_module` (passed during initialization). It processes text in chunks, using sentence-boundary detection to ensure the voice engine receives complete, coherent thoughts rather than fragmented characters. It integrates with [Color](/docs/ai/color.md) for debug logging and [ai.functions](/docs/ai/functions.md) for system output.

- **INTERNAL REFERENCES**: [Color](/docs/ai/color.md), [ai.functions](/docs/ai/functions.md)

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `code_announcements` (Default: `["I've updated the console with the code.", ... ]`)  A list of randomized phrases used to notify the user when a code block is being displayed instead of read aloud.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SpeechBridge` | Class | Orchestrates the buffering, cleaning, and routing of text to the voice module. |
| `feed` | Method | The primary entry point for ingesting raw text strings; handles code block detection. |
| `flush` | Method | Forces the remaining contents of the buffer to be sent to the voice module. |
| `abort` | Method | Clears the buffer and signals the voice module to stop current playback. |
| `_process_text_chunk` | Method | Performs regex-based cleaning (removing Markdown, headers, and list markers) and path transformation. |
| `_replace_path_for_voice` | Method | Converts file paths (e.g., `/usr/bin`) into spoken-friendly formats (e.g., `, usr bin`). |
| `_send_to_voice` | Method | Finalizes the text cleaning (removing backticks) and dispatches to the `voice.process_token` method. |

## 4. Execution Logic & Flow
- **Initialization**: Sets up the `voice` module reference, initializes an empty `buffer`, sets the `in_code_block` state to `False`, and compiles the `sentence_regex` for efficient sentence splitting.
- **Data Path**: 
    1. **Input**: Raw text is passed via `feed()`.
    2. **Code Detection**: If ` ``` ` is detected, the state toggles. If entering a code block, a random announcement is sent to voice. If exiting, processing resumes for non-code text.
    3. **Sanitization**: Text is stripped of `#`, `**`, `*`, and list markers (`1.`, `-`, `*`).
    4. **Path Transformation**: Regex identifies paths starting with `/` and replaces slashes with spaces via `_replace_path_for_voice`.
    5. **Buffering**: Cleaned text is appended to `self.buffer`.
    6. **Sentence Splitting**: The buffer is scanned for sentence terminators (`.`, `?`, `!`). When found, the complete sentence is sliced from the buffer and sent to `_send_to_voice`.
    7. **Output**: `_send_to_voice` removes remaining backticks and calls `self.voice.process_token()`.
- **Conditional Branching**: 
    - If `in_code_block` is `True`, text is not processed for speech but used to toggle state.
    - If `debug` is `True`, cleaned text is routed to `func.out` with `Color.YELLOW`.
    - `flush()` only sends data if `in_code_block` is `False` to prevent reading code as speech.

## 5. Resource Dependencies
- **Standard Libraries**: `re`, `random`, `typing`
- **Internal Modules**: 
    - [ai.functions](/docs/ai/functions.md)
    - [Color](/docs/ai/color.md)
- **External Packages**: None identified.