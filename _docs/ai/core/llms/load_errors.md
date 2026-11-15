## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| LoadErrors | /ai/core/llms/load_errors.md |

This component defines custom exception classes specifically for errors encountered during the loading process of a local language model. Its primary responsibility is to encapsulate failure states related to model loading, particularly when hardware constraints, such as insufficient GPU memory, are violated. By providing structured exceptions, it allows higher-level application logic to handle loading failures gracefully and diagnose the root cause effectively.

This module serves as a foundational part of the core LLM handling service. It acts as a dedicated error contract, ensuring that specific loading issues are clearly communicated up the call stack, separate from generic runtime errors. This promotes clean separation of concerns between the model loading mechanics and the application's error handling framework, which relies on these defined exceptions.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| GpuMemoryError | Class | Represents an error where the model could not fit into the available GPU memory. Stores diagnostics like the failing model path, requested layer offload, and engine logs. |

## 3. Implementation Details & Side Effects
- **Core Logic:** Defines a custom exception, `GpuMemoryError`, which inherits from `RuntimeError`. The constructor allows for initialization with detailed diagnostic information pertaining to the loading failure.
- **Side Effects:** None.
- **Error Handling:** It defines the specific exception `GpuMemoryError` which is raised when GPU memory allocation fails during model loading.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `typing`
- **Internal:** None