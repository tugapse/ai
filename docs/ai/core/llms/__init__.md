## 1. Architectural Role
Handles the lazy-loading of specific model classes within the AI core, avoiding CUDA context collisions.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ModelManager` | Class | Manages the lazy-loading of specific model classes, ensuring that only the selected model is loaded and initialized. |

## 3. Execution Logic & Flow
- **Initialization**: The `ModelManager` class is initialized with no internal state set.
- **Data Path**: The primary transformation of data involves determining which model to load based on user selection.
- **Conditional Branching**: The key decision point is whether to load a PyTorch-based model or a GGUF model.

## 4. Resource Dependencies
- **Standard Libraries**: None
- **Internal Modules**: None
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: None
- **Environment Lookups**: None