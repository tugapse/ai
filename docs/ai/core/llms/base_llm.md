

## 1. Architectural Role  
Provides a base class for language model implementations, defining shared utilities for input preparation, event handling, and abstract methods for model-specific operations.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `BaseModel` | Class | Abstract base class for LLM implementations, managing input formatting, event listeners, and device-specific logic. |  
| `ModelParams` | Class | Encapsulates model configuration parameters with default values and conversion to dictionary. |  
| `create_message` | Static Method | Constructs standardized message dictionaries for LLM input. |  
| `init_pytorch_cuda` | Method | Detects CUDA availability and sets inference device to GPU if available. |  
| `_prepare_input` | Method | Formats chat messages into model-ready input using tokenizer-specific logic. |  
| `add_event` | Method | Registers listeners for custom events. |  
| `trigger` | Method | Invokes registered listeners for a given event. |  
| `check_system_prompt` | Method | Ensures system prompt is positioned correctly in message history. |  
| `load_images` | Method | Placeholder for image loading logic in model-specific implementations. |  
| `join_generation_thread` | Method | Waits for background generation threads to complete. |  
| `chat` | Abstract Method | Abstract method for model-specific chat interaction. |  
| `list` | Abstract Method | Abstract method for listing available models. |  
| `pull` | Abstract Method | Abstract method for model pulling/loading. |  
| `is_gpu_available` | Method | Checks GPU availability based on inference backend. |  
| `clean_cache` | Method | Clears CUDA memory and Python garbage collection. |  
| `to_dict` | Method | Converts ModelParams instance to a dictionary of configuration parameters. |  

## 3. Execution Logic & Flow  
- **Initialization**: Sets `model_name`, `system_prompt`, `listeners`, `options`, `tokenizer`, and default `inference_device` to CPU.  
- **Data Path**: Input messages  `check_system_prompt`  `load_images`  `_prepare_input` (tokenizes and formats input)  model-specific processing  output.  
- **Conditional Branching**:  
  - Checks for CUDA availability in `init_pytorch_cuda`.  
  - Determines tokenizer formatting method via `apply_chat_template` presence.  
  - Validates system prompt placement in message history.  

## 4. Resource Dependencies  
- **Standard Libraries**: `gc`, `threading`.  
- **Internal Modules**: `entities.model_enums` (for `InferenceBackend`).  
- **External Packages**: `torch` (for CUDA checks).  

## 5. Configuration & Environment  
- **Hardcoded Constants**: `CONTEXT_WINDOW_*`, `InferenceBackend` enum values.  
- **Environment Lookups**: None.