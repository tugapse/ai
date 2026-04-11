

## 1. Architectural Role  
Orchestrate token streaming, sanitize input, process for display/speech, and manage response accumulation.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `StreamResult` | Class/Func | Stores accumulated text and interruption status |  
| `StreamOrchestrator` | Class/Func | Manages token processing, UI output, and speech synthesis |  
| `__init__` | Method | Initializes dependencies and state |  
| `run` | Method | Processes token stream, handles UI/display, and speech |  
| `_sanitize` | Method | Normalizes and filters token content |  
| `_display_and_relay` | Method | Formats and outputs content to user and speech bridge |  

## 3. Execution Logic & Flow  
- **Initialization**: Loads `printer`, `handler`, `processor`, `speech_bridge`, and sets `accumulated_text` and `started_response` to empty/False.  
- **Data Path**: Raw tokens  sanitize  process_token  handler_chain  display_relay  accumulated_text. Final buffer flush  handler_chain  display_relay.  
- **Conditional Branching**: Skips empty tokens; handles KeyboardInterrupt via `abort()`; catches exceptions and flushes speech bridge.  

## 4. Resource Dependencies  
- **Standard Libraries**: `re`, `unicodedata`, `typing`, `dataclasses`  
- **Internal Modules**: `color`, `functions`, `modules.voice.speech_bridge`  
- **External Packages**: None explicitly listed  

## 5. Configuration & Environment  
- **Hardcoded Constants**: `assistant_prompt` ("Assistant: "), `Color.PURPLE`, `Color.RESET`  
- **Environment Lookups**: None