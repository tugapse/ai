## 1. Architectural Role
`base_llm.py` defines the base class for language models, providing common functionality and structure for subclasses to implement specific model behaviors.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `BaseModel` | Class | Manages the state and behavior of a language model, including initialization, input preparation, event handling, and resource management. |
| `init_pytorch_cuda` | Method | Checks for PyTorch CUDA availability and sets the inference device accordingly. |
| `_prepare_input` | Method | Formats chat messages into model input, handling both system prompts and custom tokenizers. |
| `add_event` | Method | Adds a listener to an event. |
| `trigger` | Method | Triggers an event and notifies all registered listeners. |
| `create_message` | Static Method | Creates a message dictionary in the format expected by LLMs. |
| `check_system_prompt` | Method | Ensures the system prompt is at the beginning of the messages list. |
| `load_images` | Method | Placeholder for image loading logic. |
| `join_generation_thread` | Method | Placeholder for joining the generation thread. |
| `chat` | Abstract Method | To be implemented by subclasses, defines the chat interaction logic. |
| `list` | Abstract Method | To be implemented by subclasses, defines the list functionality. |
| `pull` | Abstract Method | To be implemented by subclasses, defines the pull functionality. |
| `is_gpu_available` | Method | Checks if the GPU is available based on the current inference device. |
| `clean_cache` | Method | Clears the cache, including CUDA cache if available. |
| `ModelParams` | Class | Holds model parameters and provides a dictionary representation. |

## 3. Execution Logic & Flow
- **Initialization**: The `BaseModel` class is initialized with a `model_name` and an optional `system_prompt`. It sets up default options, listeners, and a stop generation event.
- **Data Path**: The `_prepare_input` method processes chat messages into model input, handling both system prompts and custom tokenizers. The `chat` method is called to perform the actual chat interaction, which is implemented by subclasses.
- **Conditional Branching**: The `init_pytorch_cuda` method checks for PyTorch CUDA availability and sets the inference device accordingly. The `_prepare_input` method handles different scenarios based on the tokenizer's capabilities and the presence of a system prompt.

## 4. Resource Dependencies
- **Standard Libraries**: `gc`, `threading`
- **Internal Modules**: `functions`, `entities.model_enums`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: `CONTEXT_WINDOW_*`, `STREAMING_FINISHED_EVENT`
- **Environment Lookups**: None