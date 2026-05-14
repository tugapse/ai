## 1. Architectural Role
Manages the real-time lifecycle of streaming LLM responses by synchronizing text sanitization, UI printing, voice synthesis, and tool-call extraction.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `StreamResult` | dataclass | Encapsulates the final state of a stream, including accumulated text, interruption status, and captured tool calls. |
| `StreamOrchestrator` | Class | Orchestrates the flow of tokens from a generator to the printer, speech bridge, and tool handlers. |
| `__init__` | Method | Initializes stateful buffers and injects dependencies for printing, handling, processing, and voice. |
| `_sanitize` | Method | Normalizes Unicode and strips non-printable ASCII characters from incoming tokens. |
| `run` | Method | The primary execution loop that consumes a `stream_generator` and manages the token lifecycle. |
| `_display_and_relay` | Method | Triggers the visual output via the processor and feeds text to the speech bridge. |

## 3. Execution Logic & Flow
- **Initialization**: Sets up internal buffers (`accumulated_text`, `tool_calls`), tracks `started_response` status, and instantiates a `SpeechBridge` using the provided `voice_module`.
- **Data Path**: 
    1. **Input**: Receives a `stream_generator` yielding `raw_token` (either `dict` or `str`).
    2. **Processing**: 
        - If `dict`: Appends to `tool_calls` and `accumulated_text`.
        - If `str`: Passes through `_sanitize` $\rightarrow$ `printer.process_token` $\rightarrow$ `handler.process_token_chain`.
    3. **Output**: 
        - If `is_tool_call`: Updates `tool_calls` and `accumulated_text` (silent).
        - If `display_to_user`: Executes `_display_and_relay` (visual/audio output).
    4. **Finalization**: Flushes `printer` and `speech_bridge`, then returns a `StreamResult`.
- **Conditional Branching**:
    - **Type Check**: Branches between dictionary-based native tool calls and string-based text tokens.
    - **Token Validity**: Skips tokens that are empty after sanitization or return `None` from the printer.
    - **Handler Logic**: Branches based on `is_tool_call` (silent accumulation) vs `display_to_user` (active relay).
    - **Error Handling**: Catches `KeyboardInterrupt` to abort speech or generic `Exception` to flush buffers before re-raising.

## 4. Resource Dependencies
- **Standard Libraries**: `re`, `unicodedata`, `typing`, `dataclasses`
- **Internal Modules**: `color` (`Color`, `format_text`), `functions` (`func`), `modules.voice.speech_bridge` (`SpeechBridge`), `extras.output_printer` (`OutputPrinter`)
- **External Packages**: None explicitly imported (relies on internal abstractions for `voice_module` and `handler_manager`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `\x20-\x7E\n\t`: Regex range for printable ASCII/whitespace sanitization.
    - `NFKC`: Unicode normalization form.
- **Environment Lookups**: None.