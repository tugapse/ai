## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | StreamOrchestrator |
| Source file | stream_orchestrator.py |

The **StreamOrchestrator** serves as the central synchronization engine for real-time LLM response processing. It is responsible for consuming asynchronous token streams and orchestrating their simultaneous distribution to the user interface, the voice synthesis engine, and the internal tool execution logic.

**Functional Mission**
The primary mission of the **StreamOrchestrator** is to transform a raw, fragmented stream of tokens into a coherent, multi-modal experience. It solves the problem of "split-brain" execution where text output, voice output, and tool calls must remain synchronized and contextually valid. It ensures that tool calls are captured for history without being inappropriately displayed to the user, while simultaneously managing the "speech-to-text-to-voice" pipeline.

**System Context & Integration**
This component sits at the intersection of the LLM output and the system's output modules. It receives data from a `stream_generator` (typically provided by an LLM connector) and utilizes the [OutputPrinter](/docs/ai/extras/output_printer.md) for visual rendering and the [SpeechBridge](/docs/ai/modules/voice/speech_bridge.md) for auditory delivery. It relies on the [HandlerManager](/docs/ai/extras/handler_manager.md) to parse tokens into actionable content or tool calls. By accumulating all processed text into a `StreamResult`, it provides the necessary state for the [SessionManager](/docs/ai/services/session_manager.md) or history modules to maintain a valid conversation context.

- **INTERNAL REFERENCES**: [OutputPrinter](/docs/ai/extras/output_printer.md), [SpeechBridge](/docs/ai/modules/voice/speech_bridge.md), [HandlerManager](/docs/ai/extras/handler_manager.md).

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `StreamResult` | Dataclass | Encapsulates the final state of a stream, including accumulated text, interruption status, and captured tool calls. |
| `StreamOrchestrator` | Class | The main controller for managing token stream lifecycle and multi-modal dispatch. |
| `run` | Method | The primary execution loop that iterates through the generator, sanitizes tokens, and triggers handlers. |
| `_sanitize` | Method | Performs Unicode normalization (NFKC) and strips non-printable ASCII characters. |
| `_display_and_relay` | Method | Synchronizes the visual output via the printer and the auditory output via the speech bridge. |

## 4. Execution Logic & Flow
- **Initialization**: Sets up references to the printer, handler, processor, and speech bridge. Initializes state variables `accumulated_text`, `tool_calls`, and `started_response` to empty/false.
- **Data Path**: 
    1. **Input**: Receives a `stream_generator` yielding raw tokens (strings or dicts).
    2. **Sanitization**: Strings are normalized and stripped of non-standard characters via `_sanitize`.
    3. **Token Processing**: The [OutputPrinter](/docs/ai/extras/output_printer.md) processes the token for display.
    4. **Chain Processing**: The [HandlerManager](/docs/ai/extras/handler_manager.md) determines if the token is UI content or a tool call.
    5. **Branching**:
        - **If Tool Call (Dict)**: Appended to `tool_calls` and `accumulated_text`; triggers `on_tool_call` callback.
        - **If Tool Call (Content)**: Appended to `tool_calls` and `accumulated_text`; triggers `on_tool_call` callback; *not* sent to display.
        - **If UI Content**: Sent to `_display_and_relay` for simultaneous printing and voice feeding.
    6. **Output**: Returns a `StreamResult` containing the full text and tool call list.
- **Conditional Branching**:
    - **KeyboardInterrupt**: Triggers `speech_bridge.abort()` and returns a result marked as `interrupted=True`.
    - **Buffer Flush**: After the generator exhausts, the orchestrator attempts to flush the `printer` to capture any trailing fragments.
    - **Exception Handling**: Catches general exceptions, flushes the speech bridge, and re-raises the error.

## 5. Resource Dependencies
- **Standard Libraries**: `re`, `unicodedata`, `typing`, `dataclasses`
- **Internal Modules**: 
    - [Color](/docs/ai/color.md)
    - [Functions](/docs/ai/functions.md)
    - [SpeechBridge](/docs/ai/modules/voice/speech_bridge.md)
    - [OutputPrinter](/docs/ai/extras/output_printer.md)
- **External Packages**: None identified.