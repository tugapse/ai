## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| SpeechBridge | /ai/modules/voice/speech_bridge.md |

This component serves as the critical intermediary between raw textual input received by the AI system and the actual voice synthesis engine. Its primary responsibility is to preprocess, clean, and segment large blocks of text into discrete, natural-sounding units suitable for sequential speech generation. It handles complex tasks such as stripping markdown formatting, transforming file paths into pronounceable phrases, and intelligently splitting content based on sentence boundaries.

As a service component, `SpeechBridge` operates within the application's communication layer. It consumes text chunks and manages the internal state—specifically tracking whether it is currently inside a code block—before handing off final, polished sentences to the `voice_module` instance. This ensures that the voice output flows logically, respecting structural elements like code snippets.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| SpeechBridge | Class | Manages the interface between textual content processing and the voice synthesis module. |
| feed | Method | Feeds a chunk of text into the bridge for processing. Handles code block detection and initial text processing. |
| flush | Method | Sends any remaining text in the buffer to the voice module and clears the buffer when input concludes. |
| abort | Method | Stops any ongoing speech synthesis and clears the internal buffer state. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component buffers incoming text and uses regular expressions to perform several transformations: removing headers and markdown markers, replacing path separators (`/`) with spaces, and segmenting the accumulated text into complete sentences using `sentence_regex`. Code blocks are detected by checking for `````, temporarily suspending standard text processing until the block ends.
- **Side Effects:** Mutates internal state (`self.buffer`, `self.in_code_block`). Interacts with the external `voice_module` via `self.voice.process_token()` and `self.voice.abort()`. It also performs logging/output if `self.debug` is True via `func.out()`.
- **Error Handling:** The `feed` method includes a guard clause (`if not self.voice: return`) to prevent runtime errors if the `voice_module` dependency is not initialized.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `re`, `random`, `typing`
- **Internal:** [ai.functions](/ai/functions.md), [ai.color](/ai/color.md)