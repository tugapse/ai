### Task: Implement and Validate KV Cache State Persistence

Implement session-level KV cache persistence using `llama-cpp-python`'s state methods across `GGUFImageLLM`, `SessionVault`, and `MessageOrchestrator`, followed by full test suite validation.

---

### Phase 1: Core Implementation

1. **Verify State Method Signatures (`src/ai/core/llms/gguf_model.py`):**
   - Confirm the exact signature and behavior of `self.llama_model.save_state()` and `self.llama_model.load_state()` in the installed `llama-cpp-python` version (whether it uses direct file paths or a `LlamaState` object serialized to disk).

2. **Update Base & GGUF LLM Classes:**
   - In `src/ai/core/llms/base_llm.py`:
     - Add `save_state(self, filepath: str) -> bool` and `load_state(self, filepath: str) -> bool` defaulting to `False`.
   - In `src/ai/core/llms/gguf_model.py`:
     - Implement `save_state` and `load_state` wrapped inside `self._shared_mem_lock` with strict error handling and clean logging.

3. **Update Session Persistence & Orchestrator:**
   - In `src/ai/agents/session_vault.py`:
     - Add path resolution for session KV cache state files (e.g., `get_kv_cache_path(session_id)`) using `ai.functions.get_root_directory()`.
     - Add a cleanup helper to remove the `.state` file when a session is cleared or reset.
   - In `src/ai/agents/message_orchestrator.py`:
     - On session start/resume: if a valid state file exists for `session_id`, load it before executing inference.
     - On iteration completion: save the updated cache state to the session path.

---

### Phase 2: Test Suite Inspection & Implementation

1. **Audit Existing Test Suites:**
   - Inspect `run-tests.sh` to understand how tests are executed (environment, flags, test discovery).
   - Inspect the test structure for both unit tests and CLI/integration tests (e.g., under `tests/unit/`, `tests/cli/`, or equivalent).

2. **Create Verification Tests:**
   - Add a dedicated unit test (e.g., under the appropriate unit test directory) verifying:
     - `GGUFImageLLM.save_state` and `GGUFImageLLM.load_state` save to and restore from a temporary file without corruption.
     - `SessionVault` correctly generates and cleans up the KV state path.
   - Add an orchestration/integration test verifying:
     - An agent session saves its state after Turn 1.
     - A resumed session with the same `session_id` successfully restores the state file.

3. **Execution & Verification Gate:**
   - Execute `./run-tests.sh`.
   - Ensure both the existing test suite and the newly created state persistence tests pass with zero regressions.

---

### Constraints:
- Keep code clean, functional, and self-contained.
- Add comments only for non-trivial logic.
- Run tests directly and report the exact results and modified files upon completion.