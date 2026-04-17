## 1. Architectural Role
The `StreamOrchestrator` manages the real-time processing, sanitization, and distribution of LLM token streams to the UI printer, a token handler chain, and the voice synthesis bridge.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `StreamResult` | Dataclass | Container for the final `accumulated_text` and an `interrupted` status flag. |
| `StreamOrchestrator` | Class | Orchestrates the lifecycle of a token stream from raw input to multi-channel output. |
| `StreamOrchestrator.__init__` | Method | Initializes dependencies (`voice_module`, `output_printer`, `handler_manager`, `token_processor`) and state. |
| `StreamOrchestrator.run` | Method | The primary execution loop that consumes a `stream_generator` and returns a `StreamResult`. |
| `StreamOrchestrator._sanitize` | Method | Normalizes unicode and strips non-printable characters from tokens. |
| `StreamOrchestrator._display_and_relay` | Method | Handles the visual printing of the assistant prompt and the relay of content to the `speech_bridge`. |

## 3. Execution Logic & Flow
- **Initialization**: 
    - Stores references to `printer`, `handler`, and `processor`.
    - Instantiates `SpeechBridge` using the provided `voice_module`.
    - Initializes `accumulated_text` as an empty string and `started_response` as `False`.
- **Data Path**: 
    - `stream_generator` (Input) $\rightarrow$ `_sanitize()` $\rightarrow$ `printer.process_token()` $\rightarrow$ `handler.process_token_chain()` $\rightarrow$ `_display_and_relay()` $\rightarrow$ `func.out()` / `speech_bridge.feed()` (Output).
- **Conditional Branching**:
    - **Token Validity**: If `_sanitize` returns an empty string or `printer.process_token` returns `None`, the token is skipped.
    - **UI Trigger**: If `handler.process_token_chain` returns `display_to_user=True`, the content is passed to `_display_and_relay`.
    - **First Token**: If `started_response` is `False`, the `assistant_prompt` is printed once before the first content token.
    - **Error Handling**: 
        - `KeyboardInterrupt`: Triggers `speech_bridge.abort()` and returns `interrupted=True`.
        - `Exception`: Triggers `speech_bridge.flush()` before re-raising the error.
    - **Buffer Flush**: After the generator is exhausted, if `printer.flush()` provides a final chunk, it is processed through the handler chain.

## 4. Resource Dependencies
- **Standard Libraries**: `re`, `unicodedata`, `typing` (Optional, Any), `dataclasses`.
- **Internal Modules**: `color` (`Color`, `format_text`), `functions` (as `func`), `modules.voice.speech_bridge` (`SpeechBridge`).
- **External Packages**: None.

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `assistant_prompt`: Defaults to `"Assistant: "`.
    - `Color.PURPLE`: Used for the assistant prompt formatting.
    - `NFKC`: Unicode normalization form used in `_sanitize`.
    - `[^\x20-\x7E\n\t]`: Regex pattern used to strip non-ASCII/non-control characters.
- **Environment Lookups**: None.