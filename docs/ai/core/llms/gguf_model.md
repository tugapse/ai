

## 1. Architectural Role  
Manages GGUF model loading, execution, and streaming for CPU-based language model inference with image support.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `GGUFImageLLM` | Class | Encapsulates GGUF model lifecycle, including loading, chat generation, and resource management. |  
| `__init__` | Method | Initializes model parameters, caches, and sets up logging suppression. |  
| `_load_llm_params` | Method | Loads GGUF model from local cache or HuggingFace, applies configuration. |  
| `_generate_in_thread` | Method | Threaded stream generation using llama_cpp's chat API. |  
| `chat` | Method | Orchestrates synchronous/asynchronous chat with image injection and token estimation. |  
| `list` | Method | Exposes model metadata for registry integration. |  
| `_null_log_callback` | Function | Suppresses llama_cpp logging output. |  
| `Color` | Class | Color-coding for terminal output (imported). |  

## 3. Execution Logic & Flow  
- **Initialization**:  
  - Loads model parameters, sets up logging suppression via `llama_log_set`.  
  - Initializes `llama_model` via `_load_llm_params`, which checks local cache/download flow.  
- **Data Path**:  
  - Input: `messages` list  Tokenization  Stream processing via `_generate_in_thread`  Output tokens queued.  
  - Sync mode: Direct completion generation with usage stats extraction.  
- **Conditional Branching**:  
  - Checks `llama_model` existence before chat.  
  - Routes to streaming or sync mode based on `stream` flag.  
  - Aborts generation on `stop_generation_event` set.  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `threading`, `queue`, `gc`, `ctypes`.  
- **Internal Modules**: `core.llms.base_llm`, `functions`, `color`.  
- **External Packages**: `llama_cpp`, `huggingface_hub`.  

## 5. Configuration & Environment  
- **Hardcoded Constants**: `max_new_tokens=2048`, `n_ctx=4000`, `temperature=0.7`, `top_p=0.95`.  
- **Environment Lookups**: None.