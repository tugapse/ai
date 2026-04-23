## 1. Architectural Role
Defines the data transfer objects (DTOs) and validation schemas for the server module's API requests and responses.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ChatRequest` | Class | Validates incoming chat requests, including model selection, message history, and streaming preferences. |
| `ServerStatus` | Class | Defines the structure for reporting server health, active model state, VRAM usage, and token metrics. |
| `ModelListItem` | Class | Standardizes the representation of a single model's identity and display name for listing operations. |

## 3. Execution Logic & Flow
- **Initialization**: Classes are defined as `PydanticBase` subclasses, establishing type constraints and default values (e.g., `stream: bool = True`) upon module import.
- **Data Path**: External Input $\rightarrow$ `PydanticBase` Validation $\rightarrow$ Typed Python Object $\rightarrow$ Server Logic.
- **Conditional Branching**: No internal logic flow; data validation is handled implicitly by the `pydantic` base class during instantiation.

## 4. Resource Dependencies
- **Standard Libraries**: `typing` (`List`, `Optional`, `Dict`, `Any`)
- **Internal Modules**: None
- **External Packages**: `pydantic`

## 5. Configuration & Environment
- **Hardcoded Constants**: `stream` defaults to `True`.
- **Environment Lookups**: None