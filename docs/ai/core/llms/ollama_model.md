

## 1. Architectural Role  
Provides an LLM interface for Ollama, managing model interactions, streaming, and model lifecycle operations.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `OllamaModel` | Class | Wraps Ollama's LLM functionalities for chat, model listing, and pulling. |  
| `__init__` | Method | Initializes model connection, pulls required models, and configures parameters. |  
| `chat` | Method | Generates responses via Ollama, supporting streaming and non-streaming modes. |  
| `list` | Method | Retrieves list of available Ollama models. |  
| `pull` | Method | Pulls specified Ollama model, handling versioning and existing model checks. |  
| `join_generation_thread` | Method | Clears stop event for synchronous Ollama generation. |  

## 3. Execution Logic & Flow  
- **Initialization**:  
  - Sets server IP, initializes Ollama client, pulls model via `pull()`, configures model parameters.  
- **Data Path**:  
  - `chat()`  Processes messages, appends images, streams/non-streams via Ollama's `chat()`  Yields content chunks or returns final content.  
- **Conditional Branching**:  
  - `stream` flag determines synchronous vs. streaming output.  
  - `stop_generation_event` interrupts streaming via `KeyboardInterrupt` or explicit event set.  
  - Error handling for Ollama exceptions and traceback logging.  

## 4. Resource Dependencies  
- **Standard Libraries**: `tqdm`, `sys`, `threading`.  
- **Internal Modules**: `core.events`, `core.llms.base_llm`, `functions`.  
- **External Packages**: `ollama`.  

## 5. Configuration & Environment  
- **Hardcoded Constants**: `"127.0.0.1"` (default server IP), `":latest"` (default model version).  
- **Environment Lookups**: None.