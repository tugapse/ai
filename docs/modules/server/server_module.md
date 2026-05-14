## 1. Architectural Role
`JarvisServerModule` acts as the lifecycle orchestrator for the JARVIS Brain Server, serving as a bridge between the modular system architecture and a network-accessible FastAPI interface. It encapsulates the instantiation of the [brain_hub](modules/server/brain_hub.md), manages the asynchronous execution of the [uvicorn](https://pypi.org/project/uvicorn/) server in a background thread, and ensures graceful resource deallocation (VRAM release) via the [base_module](modules/base_module.md) lifecycle protocols.

## 2. Environment & Configuration
**Environment Lookups:**
- `host` (via `__init__`)  IP address to bind the server.
- `port` (via `__init__`)  Port for the API listener.

**Hardcoded Constants:**
- `host` (Default: `"0.0.0.0"`)  Default binding address.
- `port` (Default: `8000`)  Default API port.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `JarvisServerModule` | Class | Manages the lifecycle (init, start, shutdown) of the server module. |
| `initialize` | Method | Configures the [brain_hub](modules/server/brain_hub.md), creates the FastAPI app via [app](modules/server/app.md), and prepares the Uvicorn server. |
| `start` | Method | Spawns a daemon thread to execute the Uvicorn server loop. |
| `get_instance` | Method | Exposes the active [brain_hub](modules/server/brain_hub.md) instance to the caller. |
| `shutdown` | Method | Signals the Uvicorn server to exit and triggers `unload_brain` on the [brain_hub](modules/server/brain_hub.md). |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Receives `config`, `orchestrator`, and `history_manager`.
    2. Instantiates `BrainHub` and injects the `orchestrator`.
    3. Calls `create_app` from [app](modules/server/app.md) to build the FastAPI instance.
    4. Wraps the app in a `uvicorn.Config` and `uvicorn.Server` object.
- **Data Path**: 
    1. `start()` is called $\rightarrow$ `threading.Thread` targets `self._uvicorn_server.run` $\rightarrow$ Thread enters `join()` $\rightarrow$ Server listens on `host:port`.
- **Conditional Branching**: 
    - `initialize`: If `self._brain_hub` is already present, logs a warning and aborts.
    - `start`: If `self._uvicorn_server` is not initialized, logs an error and aborts.
    - `shutdown`: Checks for existence of `_uvicorn_server` and `_brain_hub` before attempting teardown.

## 5. Resource Dependencies
- **Standard Libraries**: `threading`, `typing`
- **Internal Modules**: 
    - [functions](functions.md)
    - [services/history_manager.md](services/history_manager.md)
    - [modules/base_module.md](modules/base_module.md)
    - [modules/server/brain_hub.md](modules/server/brain_hub.md)
    - [modules/server/app.md](modules/server/app.md)
- **External Packages**: `uvicorn`, `fastapi`