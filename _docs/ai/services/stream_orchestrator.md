## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| StreamOrchestrator | /ai/services/stream_orchestrator.md |

This component is responsible for managing the end-to-end processing pipeline of a raw token stream received from an AI model. Its primary function is to sanitize incoming tokens, route them through various handlers (such as UI rendering or tool execution), accumulate the complete text output, and manage the state of the interaction, including detecting user interruptions.

The `StreamOrchestrator` acts as a critical service layer, bridging the raw AI output stream with the application's display and control mechanisms. It orchestrates interactions between the [SpeechBridge](/ai/modules/voice/speech_bridge.md), the [OutputPrinter](/ai/extras/output_printer.md), and the [HandlerManager](/ai/modules/handler_manager.md), ensuring that tokens are correctly interpreted as dialogue, tool calls, or system events before being presented or logged.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| StreamResult | Class | Holds the final results after processing a streaming response, including accumulated text and tool calls. |
| StreamOrchestrator | Class | Orchestrates the processing of a token stream from an AI model. |
| StreamOrchestrator.run | Method | Processes the entire token stream generator, returning a StreamResult. |
| StreamOrchestrator._sanitize | Method | Sanitizes a raw token by normalizing Unicode and removing non-printable characters. |
| StreamOrchestrator._display_and_relay | Method | Displays the content to the user and feeds it to the speech bridge, updating internal state. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `run` method iterates over the stream, first checking for native dictionary tokens (tool calls). For string tokens, it sanitizes them, passes them to the `handler` for processing, and routes the output. If the handler identifies a tool call, it is recorded without immediate display; otherwise, it is displayed via `_display_and_relay`, which also feeds the content to the `speech_bridge`.
- **Side Effects:** Interacts heavily with external state via the injected dependencies: it prints output to the console via the [OutputPrinter](/ai/extras/output_printer.md) and feeds content to the [SpeechBridge](/ai/modules/voice/speech_bridge.md).
- **Error Handling:** Catches `KeyboardInterrupt` to cleanly abort the stream and returns a `StreamResult` indicating interruption. General exceptions are caught and re-raised after ensuring the `speech_bridge` is flushed.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `re`, `unicodedata`, `typing`, `dataclasses`.
- **Internal:** [SpeechBridge](/ai/modules/voice/speech_bridge.md), [OutputPrinter](/ai/extras/output_printer.md), [HandlerManager](/ai/modules/handler_manager.md), [ai.functions](/ai/functions.md).