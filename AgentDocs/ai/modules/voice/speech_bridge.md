## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **SpeechBridge** | [src/ai/modules/voice/speech_bridge.py](/src/ai/modules/voice/speech_bridge.py) |

The `SpeechBridge` class serves as a specialized middleware layer between raw textual content processing and the voice synthesis engine. Its primary responsibility is to transform structured or formatted text (such as Markdown, code blocks, and file paths) into natural-sounding speech by cleaning syntax and intelligently chunking text into manageable sentence-based segments.

Within the broader application architecture, this component acts as a pre-processor for the voice module. It ensures that the synthesized output is not interrupted by technical formatting artifacts and provides "contextual announcements" when the system transitions into displaying code, thereby improving the user experience during multimodal interactions.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `SpeechBridge(voice_module: Any, debug: bool = False)` | Class | Initializes the bridge with a target voice module and optional debug logging. |
| `feed(text: str)` | Method | Ingests a string chunk, handles code block detection via triple backticks, and triggers text processing. |
| `flush()` | Method | Forces the remaining content in the internal buffer to be sent to the voice module and clears the buffer. |
| `abort()` | Method | Immediately stops ongoing synthesis via the voice module and resets all internal buffer states. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Text Cleaning:** Uses regular expressions to strip Markdown headers (`#`), bold/italic markers (`*`, `**`), and list markers (numeric or bulleted).
    - **Path Transformation:** Identifies file paths (starting with `/`) and replaces internal slashes with spaces to ensure the TTS engine pronounces them as natural phrases rather than individual characters.
    - **Sentence Chunking:** Maintains an internal buffer and uses a regex-based lookahead (`sentence_regex`) to identify sentence boundaries (`.`, `?`, `!`), ensuring only complete sentences are dispatched to the voice module.
    - **Code Block Handling:** Monitors state via `in_code_block`. When entering a code block, it selects a random announcement from a predefined list to inform the user that visual data is being displayed.
- **Side Effects:** 
    - **Console Output:** If `debug` is enabled, processed text chunks are printed to the console using formatted text.
    - **External State Mutation:** Calls `process_token()` or `abort()` on the provided `voice_module`.
- **Error Handling:** The component performs basic null-checks on the `voice_module` to prevent errors during `feed` or `abort` calls if no voice engine is attached.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `re`, `random`, `typing`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.color](/AgentDocs/ai/color.md)