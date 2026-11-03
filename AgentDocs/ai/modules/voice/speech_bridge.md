## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **SpeechBridge** | [src/ai/modules/voice/speech_bridge.py](/AgentDocs/ai/modules/voice/speech_bridge.py) |

The `SpeechBridge` class serves as a specialized middleware layer between raw textual content processing and the voice synthesis module. Its primary responsibility is to transform structured or technical text (such as Markdown, code blocks, and file paths) into natural-sounding language suitable for Text-to-Speech (TTS) engines.

Within the broader application architecture, this component acts as a pre-processor for the voice module. It ensures that the auditory experience is not disrupted by technical artifacts like asterisks, hashtags, or complex directory strings, instead providing conversational announcements when technical data is being presented visually.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `SpeechBridge(voice_module: Any, debug: bool = False)` | Class | Initializes the bridge with a target voice module and an optional debug flag. |
| `feed(text: str)` | Method | Ingests a string chunk, detecting code blocks and processing text for natural speech. |
| `flush()` | Method | Forces the processing of any remaining text in the buffer and clears it. |
| `abort()` | Method | Immediately halts ongoing synthesis and resets the internal buffer and code block state. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component utilizes a buffering mechanism to ensure text is only sent to the voice module when a complete sentence (detected via `sentence_regex`) is formed. It performs several regex-based transformations:
    - Strips Markdown headers (`#`), bold/italic markers (`*`, `**`), and list markers.
    - Identifies file paths (starting with `/`) and replaces internal slashes with spaces via `_replace_path_for_voice` to improve TTS pronunciation.
    - Monitors code block delimiters (`` ``` ``) to switch between standard text processing and "announcement mode," where it injects conversational phrases (e.g., "Technical details are on screen") instead of reading the code itself.
- **Side Effects:** 
    - If `debug` is enabled, it outputs processed text to the console using `func.out`.
    - It mutates the state of the provided `voice_module` by calling its `process_token` or `abort` methods.
- **Error Handling:** The class includes safety checks to ensure that if the `voice_module` is not present or becomes unavailable, processing is gracefully skipped.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `re`, `random`, `typing`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.color](/AgentDocs/ai/color.md)