## 1. Architectural Role
Acts as a package initializer that intentionally avoids eager imports of LLM model classes to prevent CUDA context collisions between PyTorch and GGUF backends.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `__init__.py` | Module | Package marker; contains documentation regarding lazy-loading strategy. |

## 3. Execution Logic & Flow
Direct exports only; no internal logic flow.

## 4. Resource Dependencies
- **Standard Libraries**: None
- **Internal Modules**: None
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: None
- **Environment Lookups**: None