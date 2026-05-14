## 1. Architectural Role
[services/stream_orchestrator.py](src/ai/services/stream_orchestratator.py) acts as the central synchronization engine for real-time LLM response streams. It manages the complex lifecycle of incoming tokens, bifurcating data into three distinct channels: UI rendering via [extras/output_printer.py](src/extras/output_printer.py), auditory playback via [modules/voice/speech_bridge.py](src/modules/voice/speech_bridge.py), and logical execution of tool calls. It ensures conversational integrity by accumulating all tokens (including silent tool data) to prevent context window errors, while providing high-level interruption handling via `KeyboardInterrupt`.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `StreamResult` | Dataclass | Data container for the final state of a stream, including accumulated text, interruption status, and captured tool calls. |
| `StreamOrchestrator` | Class | The primary controller for managing token flow, sanitization, and multi-modal output dispatching. |
| `_sanitize` | Method | Normalizes Unicode characters (NFKC) and strips non-printable ASCII characters to ensure clean text processing. |
| `run` | Method | The main execution loop that iterates through a generator, handles token categorization (Dict vs. String), and manages error states. |
| `_display_and_relay` | Method | Orchestrates the simultaneous terminal output, token processing, and feeding of the speech buffer. |

## 4. Execution Logic & Flow
- **Initialization**: Sets up the `SpeechBridge`, `OutputPrinter`, `HandlerManager`, and `TokenProcessor`. Resets internal buffers (`accumulated_text`, `tool_calls`, `started_response`).
- **Data Path**: 
    1. **Input**: Receives a `stream_generator` yielding raw tokens (strings or dicts).
    2. **Categorization**: 
        - If **Dict**: Appended to `tool_calls` and `accumulated_text`; triggers `on_tool_call` callback.
        - If **String**: Passed through `_sanitize` $\rightarrow$ `printer.process_token` $\rightarrow$ `handler.process_token_chain`.
    3. **Routing**: 
        - **Tool Content**: If `is_tool_call` is true, content is added to `tool_calls` and `accumulated_text` but bypassed from UI/Voice.
        - **UI/Voice Content**: If `display_to_user` is true, content is passed to `_display_and_relay` for terminal printing and speech feeding.
    4. **Output**: Returns a `StreamResult` object once the generator exhausts or is interrupted.
- **Conditional Branching**: 
    - **Interrupt Handling**: Catches `KeyboardInterrupt` to abort speech immediately.
    - **Buffer Draining**: Executes a post-loop `flush()` on the printer to capture trailing fragments.
    - **Sanitization Check**: Skips processing if the sanitized token results in an empty string.

## 5. Resource Dependencies
- **Standard Libraries**: `re`, `unicodedata`, `typing`, `dataclasses`
- **Internal Modules**: 
    - [color.md](src/color.md)
    - [functions.md](src/functions.md)
    - [modules/voice/speech_bridge.md](src/modules/voice/speech_bridge.md)
    - [extras/output_printer.md](src/extras/output_printer.md)
    - [extras/handler_manager.md](src/extras/handler_manager.md)
- **External Packages**: None identified.