## 1. Architectural Role
Acts as a lifecycle-managed wrapper that encapsulates the `BrainHub` logic and a `FastAPI` application, hosting them within a non-blocking `uvicorn` server thread.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `JarvisServerModule` | Class | Manages the lifecycle (init, start, shutdown) of the neural server component. |
| `__init__` | Method | Sets network parameters (`host`, `port`) and initializes internal state holders. |
| `initialize` | Method | Instantiates `BrainHub`, links the `orchestrator`, and constructs the `FastAPI` app via `create_app`. |
| `start` | Method | Spawns a daemon `threading.Thread` to execute the `uvicorn.Server.run` loop. |
| `get_instance` | Method | Provides access to the active `BrainHub` instance. |
| `shutdown` | Method | Signals the `uvicorn.Server` to exit and triggers `BrainHub.unload_brain()` to release VRAM. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. `__init__` assigns `host` and `port` and sets `_brain_hub`, `_fastapi_app`, `_server_thread`, and `_uvicorn_server` to `None`.
    2. `initialize` performs dependency injection by creating `BrainHub(config)`, assigning the `orchestrator`, and calling `create_app`.
    3. `initialize` configures the `uvicorn.Config` and instantiates the `uvicorn.Server` object.
- **Data Path**: 
    - **Configuration Input** (`config`, `orchestrator`) $\rightarrow$ **Internal State** (`BrainHub`, `FastAPI` app) $\rightarrow$ **Network Interface** (`uvicorn.Server` on `host:port`).
- **Conditional Branching**:
    - `initialize`: If `self._brain_hub` is already present, it logs a warning and aborts.
    - `start`: If `self._uvicorn_server` is not initialized, it logs an error and aborts.
    - `shutdown`: Checks for existence of `_uvicorn_server` and `_brain_hub` before attempting to signal exit or unload resources.

## 4. Resource Dependencies
- **Standard Libraries**: `threading`, `typing`
- **Internal Modules**: `functions` (as `func`), `services.history_manager`, `modules.base_module`, `.brain_hub`, `.app`
- **External Packages**: `uvicorn`, `fastapi`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - Default `host`: `"0.0.0.0"`
    - Default `port`: `8000`
    - `log_level`: `"info"`
- **Environment Lookups**: None (parameters are passed via `__init__` or `initialize`).