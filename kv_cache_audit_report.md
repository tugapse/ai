# LLM Architecture Audit for KV Cache Persistence

This report details the architecture of the LLM and agent systems with a focus on implementing session-level KV cache persistence.

---

## 1. Class Hierarchy & Existing Interfaces

The core LLM logic is defined by an abstract base class and implemented in a specific GGUF wrapper.

**Files Inspected:**
- `src/ai/core/llms/base_llm.py`
- `src/ai/core/llms/gguf_model.py`

### `BaseModel` (`base_llm.py`)

This abstract class defines the high-level interface for all LLM implementations.

- **Text Generation & Streaming:** The primary method is `chat()`, an abstract method intended for implementation by subclasses.
  ```python
  def chat(
      self,
      messages: list,
      images: list = [],
      stream: bool = True,
      options: object = {},
  ):
      """Abstract interface endpoint intended to process conversations and deliver textual streams."""
      raise NotImplementedError
  ```

- **Tokenization / Prompt Formatting:** The `_prepare_input()` method handles the conversion of message dictionaries into a format suitable for the model, using the associated `tokenizer`. It can use `tokenizer.apply_chat_template` if available.

- **State Resetting & Context Clearing:**
    - `clean_cache()`: A concrete method that flushes GPU memory (`torch.cuda.empty_cache()`) and calls the garbage collector (`gc.collect()`). It does **not** clear the KV cache state within the model itself.
    - `unload()`: An abstract method intended for subclasses to completely purge the model from memory.
    - `request_shutdown()`: A concrete method that orchestrates a graceful shutdown by stopping generation threads and calling `clean_cache()`.

- **Context Windows & Cache Settings:**
    - The `BaseModel` and its `TokenCountInfo` inner class track token counts and context window size (`max_context_window`).
    - The `ModelParams` class standardizes configuration, including `num_ctx` (which maps to `n_ctx` in the GGUF model).
    - There are **no existing methods or parameters** in `BaseModel` for saving or loading the KV cache state from disk.

### `GGUFImageLLM` (`gguf_model.py`)

This class inherits from `BaseModel` and implements the GGUF-based LLM using `llama-cpp-python`.

- **Statelessness:** The `chat()` method is fundamentally **stateless**. It receives the entire message history from the caller on every invocation. It does not maintain an internal conversation state or KV cache between calls. The previous turn's context is entirely rebuilt by the caller.

---

## 2. Underlying Inference Engine & Bindings

The GGUF wrapper uses the `llama-cpp-python` library directly.

**File Inspected:**
- `src/ai/core/llms/gguf_model.py`

- **Mechanism:** The `GGUFImageLLM` class uses `llama-cpp-python` as its inference backend. This is evident from the imports and the instantiation of the `Llama` object.
  ```python
  from llama_cpp import Llama, llama_log_set
  ...
  self.llama_model = Llama(
      model_path=model_path,
      n_ctx=self._n_ctx,
      verbose=False,
      **kwargs
  )
  ```

- **`Llama` Instance Management:**
    - **Instantiation:** The `Llama` instance is created within the `_load_llm_params` method, which is called from the `GGUFImageLLM` constructor.
    - **Configuration:** The constructor accepts `n_ctx` and a `model_params` dictionary, which can pass through any valid `llama-cpp-python` `Llama` constructor arguments (e.g., `n_gpu_layers`, `cache_type_k`, etc.). The `n_ctx` parameter directly controls the context window size.
    - **Concurrency:** A `threading.Lock` (`_shared_mem_lock`) is used to protect access to the shared `llama_model` instance, indicating it's designed to be used in a multi-threaded environment but only by one thread at a time.

- **Endpoints/Flags:** Since it uses the Python library directly, there are no HTTP endpoints or CLI arguments involved in the inference process itself.

---

## 3. Agent Invocation & Context Flow

The agent system orchestrates calls to the LLM through a series of abstractions, passing the full context on each turn.

**Files Inspected:**
- `src/ai/agents/message_orchestrator.py`
- `src/ai/agents/llm_connector.py`

- **Invocation Chain:**
    1.  **`MessageOrchestrator`**: This is the main control loop. In its `run_loop` method, it prepares a `payload` dictionary containing the full context for the current agent (objective, past messages, tool outcomes, etc.).
    2.  It then calls `self.connector.send_request(payload, ...)`.
    3.  **`LLMConnector`**: The `send_request` method receives the payload, formats it into a `messages` list (with a system prompt), and passes it to a private `_execute_llm_call`.
    4.  The `_execute_llm_call` method calls a utility function `ask()` from `ai.direct`.
    5.  The `ask()` utility (not fully shown but inferred from `llm_connector.py`) is the final piece that invokes `self.llm.chat(messages, ...)`, where `self.llm` is the `GGUFImageLLM` instance.

- **History Management:** The `MessageOrchestrator` is responsible for maintaining the conversation history. It uses `MemoryManager` to store messages for each agent. On every turn, it constructs the `payload` with the relevant history (`messages_received`, `conversation_history`) and sends it to the LLM. The `GGUFImageLLM` class itself does **not** retain any history between `chat()` calls.

- **Session Identifiers:** Session management is handled by the `MessageOrchestrator` via the `SessionVault` class. A `session_id` is passed into the `run_loop`. The `SessionVault` uses this ID to save and load the state of the *agent system* (agent memory, current iteration, etc.), but **not** the LLM's KV cache.

---

## 4. Storage & Persistence Conventions

The project has established patterns for session state and path management.

**Files Inspected:**
- `src/ai/agents/session_vault.py`
- `src/ai/agents/message_orchestrator.py`
- `ai/functions.py` (Inferred from usage)

- **Storage Location:** The `SessionVault` class is responsible for persistence. While its implementation is not visible, its usage in `MessageOrchestrator` implies it saves session data. The name suggests a dedicated, session-specific storage location. The `ask` function in `llm_connector.py` also writes temporary logs to `logs/llm_output_active.md`.

- **Path Utilities:** The code frequently uses `ai.functions.get_root_directory()` to resolve absolute paths within the project. This utility should be used to construct the path for saving KV cache files to ensure consistency.

- **Existing Persistence:** The `MessageOrchestrator` uses `SessionVault` to persist the *agent state* between runs:
  ```python
  # In MessageOrchestrator.run_loop
  self.vault.commit(self._capture_state(next_agent, i + 1))
  
  # In MessageOrchestrator._capture_state
  return {
      "current_agent": next_agent,
      "iteration": iteration,
      "memory": self.memory.serialize(),
      ...
  }
  ```
  This confirms that a mechanism for saving and loading session-specific data already exists, but it is currently scoped to agent memory and orchestration state, not the low-level model cache.

---

## 5. Conclusion & Recommendations for Implementation

The current architecture is stateless at the LLM level, making it a prime candidate for KV cache persistence. The `llama-cpp-python` library supports this directly via the `Llama.save_state()` and `Llama.load_state()` methods.

### Technical Constraints & Edge Cases:

1.  **State-History Mismatch:** The loaded KV cache state must perfectly correspond to the prompt history. If you load a cache state and then provide a different history, the model will generate incoherent output. The application must ensure that the history fed to the model during generation is the exact same history that was used to create the saved state.
2.  **Session Management:** The `save_state` and `load_state` logic should be tied to the `session_id`. The `MessageOrchestrator` is the ideal place to manage this.
3.  **Path Management:** Use the existing `ai.functions.get_root_directory()` and `SessionVault`'s path conventions to determine where to store the `.state` files. A good location might be within the session vault's directory for the given `session_id`.
4.  **First Turn vs. Subsequent Turns:** The logic must differentiate between the first turn of a session (or when no state file exists) and subsequent turns.
    - **First turn:** Run inference normally and call `llama_model.save_state("path/to/session.state")` after the prompt is processed.
    - **Subsequent turns:** Before inference, check for a state file. If it exists, call `llama_model.load_state("path/to/session.state")`. Then, when performing inference, only provide the *new* tokens/messages, not the full history. After inference, save the updated state back to the file.

### Proposed Implementation Steps:

1.  **Modify `GGUFImageLLM`:**
    - Add two new methods: `save_kv_cache(path: str)` and `load_kv_cache(path: str)`.
    - These methods will be simple wrappers around `self.llama_model.save_state(path)` and `self.llama_model.load_state(path)`, including error handling.
    - Ensure these methods use the `_shared_mem_lock` to prevent race conditions.

2.  **Modify `MessageOrchestrator`:**
    - In `run_loop`, after initializing `self.vault`, determine the path for the KV cache state file based on the `session_id`.
    - Before the first call to `self.connector.send_request`, attempt to load the KV cache using the new `load_kv_cache` method on the `GGUFImageLLM` instance.
    - **Crucially**, if the load is successful, the `payload` sent to the LLM must be modified to contain **only the new user message**, not the entire history that is already reflected in the loaded cache.
    - After each `send_request` call, save the updated cache using the `save_kv_cache` method.

3.  **Modify `SessionVault`:**
    - Consider adding a method to `SessionVault` to handle the deletion of the KV cache file when a session is explicitly cleared or expires.