## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| GpuAdvisor | /ai/services/gpu_advisor.md |

This component is responsible for diagnosing and resolving `GpuMemoryError` exceptions that occur when attempting to load a language model that exceeds the available GPU memory. Its primary responsibility is to provide actionable advice to the user or execute an automatic fallback strategy, preventing the application from failing outright. It achieves this by querying the system state to determine which processes are consuming GPU resources and what memory is free.

GpuAdvisor functions as a critical service layer component within the application architecture. It interfaces with external system tools like `nvidia-smi` via `nvidia_snapshot` to gather hardware state, and it communicates with other running instances via `ProcessManager` to identify competing JARVIS processes. It orchestrates the loading of models, potentially partially offloading layers to the CPU using `_partial` before presenting choices via the interactive resolution flow in `resolve`.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| GpuHolder | Class | Represents a single process actively using GPU memory, containing PID, name, and usage metrics. |
| GpuSnapshot | Class | Aggregates the total and free GPU memory alongside a list of `GpuHolder` instances. |
| Choice | Class | A wrapper for a potential action, containing a human-readable label and a callable function to execute the action. |
| GpuAdvisor | Class | The main orchestrator. Resolves memory errors by surveying the GPU state, presenting options, and executing the chosen recovery strategy. |
| model_key | Function | Generates a canonical, standardized string key from a model name or configuration path for consistent identification. |
| nvidia_snapshot | Function | Executes `nvidia-smi` to gather the current state of the GPU memory and active processes, returning a `GpuSnapshot` or `None` on failure. |
| _gb | Function | Utility function to convert megabytes (MB) to gigabytes (GB) for display purposes. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `resolve` method drives the advisory process. It first gathers a `GpuSnapshot` and identifies active JARVIS servers. If interactive, it presents choices derived from the snapshot and server list. If non-interactive, it applies a default policy (preferring an existing model server or falling back to partial loading). The `_partial` method uses a binary search approach to find the maximum number of GPU layers that can be loaded without exceeding the available free memory.
- **Side Effects:**
    - Spawns external processes (`nvidia-smi`) via `subprocess` in `nvidia_snapshot`.
    - Reads filesystem metadata (`os.path.getsize`) in `_upper_bound`.
    - Reads process lists and instances via `ProcessManager` and `DirectoryManager` (which involves filesystem access).
    - Executes external model loading logic via the injected `loader` callable, which interacts with the underlying LLM engine.
- **Error Handling:** Catches `OSError`, `ValueError`, `IndexError`, and `subprocess.SubprocessError` in `nvidia_snapshot`. The `resolve` method catches `GpuMemoryError` during execution, offering fallback options or re-raising if even CPU-only loading fails.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `copy`, `gc`, `os`, `subprocess`, `sys`, `dataclasses`, `typing`.
- **Internal:** [ai.functions](/ai/functions.md), [ai.color](/ai/color.md), [ai.core.llms.load_errors/GpuMemoryError](/ai/core/llms/load_errors.md), [ai.services.process_manager/ProcessManager](/ai/services/process_manager.md), [ai.services.engine_manager/EngineManager](/ai/services/engine_manager.md), [ai.services.model_orchestrator/ModelOrchestrator](/ai/services/model_orchestrator.md).