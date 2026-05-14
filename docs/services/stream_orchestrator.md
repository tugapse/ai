## 1. Architectural Role

**Functional Mission**
The **StreamOrchestrator** serves as the central synchronization engine for real-time LLM response streaming. Its primary mission is to ingest raw token streams and orchestrate their simultaneous distribution to three distinct channels: visual output via the UI, auditory output via the speech engine, and logical state updates via tool call detection. It solves the complex problem of "split-stream" processing, where a single stream must be parsed to distinguish between text intended for human consumption and structured data intended for system execution.

**System Context & Integration**
This component acts as a high-level mediator between the raw LLM generator and the user-facing interfaces. It consumes tokens and passes them through a processing pipeline involving [OutputPrinter](/docs/extras/output_printer.md) for formatting and [handler_manager](/docs/extras/handler_manager.md) for semantic parsing. By managing the lifecycle of a response, it ensures that tool calls are captured for the conversation history to prevent API errors, while simultaneously feeding the [SpeechBridge](/docs/modules/voice/speech_bridge.md) to maintain a fluid, low-latency voice interaction.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `StreamResult` | dataclass | Data container for the final state of a stream, including accumulated text, interruption status, and captured tool calls. |
| `StreamOrchestrator` | Class | The primary controller for managing token stream lifecycle, sanitization, and multi-channel relay. |
| `_sanitize` | Method | Performs Unicode normalization (NFKC) and strips non-printable ASCII characters to ensure stream stability. |
| `run` | Method | The main execution loop that iterates over the `stream_generator`, handles branching logic for tool calls vs. text, and manages error/interrupt states. |
| `_display_and_relay` | Method | Orchestrates the simultaneous side-effects of a valid text token: updating internal accumulation, printing to console, and feeding the voice buffer. |

## 4. Execution Logic & Flow
- **Initialization**: Sets up internal state buffers (`accumulated_text`, `tool_calls`, `started_response`) and initializes the [SpeechBridge](/docs/modules/voice/speech_bridge.md) with the provided voice module.
- **Data Path**: 
    1. **Ingestion**: Receives `raw_token` from `stream_generator`.
    2. **Type Check**: If `raw_token` is a `dict`, it is treated as a native tool call, appended to `tool_calls`, and added to `accumulated_text`.
    3. **Sanitization**: Non-dict tokens undergo `_sanitize` (Unicode normalization and regex filtering).
    4. **Processing**: The token is passed to `self.printer.process_token` and then to `self.handler.process_token_chain`.
    5. **Branching**:
        - **If `is_tool_call`**: The content is added to `tool_calls` and `accumulated_text` but bypassed from the display/voice relay.
        - **If `display_to_user`**: The content is passed to `_display_and_relay`, which triggers `func.out` and `self.speech_bridge.feed`.
    6. **Finalization**: Flushes the printer buffer and the speech bridge, returning a `StreamResult`.
- **Conditional Branching**:
    - **KeyboardInterrupt**: Triggers `self.speech_bridge.abort()` and returns a `StreamResult` marked as `interrupted=True`.
    - **Exception Handling**: Flushes the speech bridge before re-raising the exception to prevent hanging audio.

## 5. Resource Dependencies
- **Standard Libraries**: `re`, `unicodedata`, `typing`, `dataclasses`
- **Internal Modules**: 
    - [Color](/docs/color.md)
    - [functions](/docs/functions.md)
    - [SpeechBridge](/docs/modules/voice/speech_bridge.md)
    - [OutputPrinter](/docs/extras/output_printer.md)
- **External Packages**: None identified.