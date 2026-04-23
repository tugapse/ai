## 1. Architectural Role
Provides an abstract base class that defines the lifecycle, state management, and initialization contract for all pluggable JARVIS system modules.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `BaseModule` | Class | Abstract blueprint for module lifecycle management. |
| `__init__` | Method | Initializes module identity, stores configuration `kwargs`, and sets initial state flags. |
| `initialize` | Method | Orchestrates the setup of the internal engine; prevents double-initialization via `_is_initialized`. |
| `get_instance` | Method | Provides access to the active `_instance` while validating initialization state. |
| `is_active` | Property | Boolean check confirming the module is both initialized and possesses a non-null instance. |
| `shutdown` | Method | Performs cleanup by nullifying the `_instance` and resetting `_is_initialized`. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. `__init__` is called with `module_name` and `kwargs`.
    2. `_instance` is set to `None`.
    3. `_is_initialized` is set to `False`.
- **Data Path**: 
    1. Call to `initialize()` $\rightarrow$ Log event $\rightarrow$ Set `_is_initialized = True`.
    2. Call to `get_instance()` $\rightarrow$ Check `_is_initialized` $\rightarrow$ Return `_instance`.
- **Conditional Branching**:
    - **Initialization Guard**: In `initialize()`, if `_is_initialized` is `True`, a `WARN` log is triggered and the method returns early.
    - **Access Guard**: In `get_instance()`, if `_is_initialized` is `False`, an `ERROR` log is triggered before returning the instance.
    - **Activity Check**: `is_active` returns `True` only if `_is_initialized == True` AND `_instance is not None`.

## 4. Resource Dependencies
- **Standard Libraries**: `typing` (`Any`, `Optional`)
- **Internal Modules**: `functions` (aliased as `func`)
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: None.
- **Environment Lookups**: None.