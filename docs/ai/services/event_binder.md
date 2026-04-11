

## 1. Architectural Role  
Central hub for binding chat and LLM event listeners to callback functions.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `EventBinder` | Class | Encapsulates event binding logic for chat and LLM components. |  
| `bind_core_events` | Static Method | Registers event listeners for chat sent, output requested, and LLM stream finished events. |  

## 3. Execution Logic & Flow  
- **Initialization**: No instance-specific initialization; class is loaded with static method definition.  
- **Data Path**: Input (Chat/LLM instances and callbacks)  Event registration via `add_event` method calls  Output (bound event listeners).  
- **Conditional Branching**: Checks if `llm` exists before registering `STREAMING_FINISHED_EVENT` listener.  

## 4. Resource Dependencies  
- **Internal Modules**: `core.llms.base_llm`, `core.chat`  
- **Standard Libraries**: None  
- **External Packages**: None  

## 5. Configuration & Environment  
- **Hardcoded Constants**: None  
- **Environment Lookups**: None