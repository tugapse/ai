## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **JarvisServerModule** | [src/ai/modules/server/server_module.py](/src/ai/modules/server/server_module.py) |

The `JarvisServerModule` serves as a high-level wrapper for the JARVIS Brain Server, providing a standardized interface that adheres to the system's module lifecycle. Its primary responsibility is to manage the instantiation, execution, and graceful termination of a FastAPI-based web server that exposes the AI's capabilities via a network interface.

Within the broader architecture, this component acts as a controller for the server subsystem. It bridges the gap between the core model orchestration logic and the network layer by wrapping a [BrainHub](/AgentDocs/ai/modules/server/brain_hub.md) and an application instance created via [create_app](/AgentDocs/ai/modules/server/app.md). It ensures that the API runs in a non-blocking background thread, allowing the main program to continue its execution while the "Neural Link" remains active.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `JarvisServerModule(host, port, **kwargs)` | Class | The main module class. Initializes server configuration including binding IP and port. |
| `initialize(config, orchestrator, history_manager)` | Method | Prepares the [BrainHub](/AgentDocs/ai/modules/server/brain_hub.md), links the orchestrator, and sets up the `uvicorn` server configuration. |
| `start()` | Method | Spawns a daemon thread to run the `uvicorn` server, preventing the main process from blocking. |
| `get_instance()` | Method | Returns the active `BrainHub` instance currently managed by the module. |
| `shutdown()` | Method | Triggers a graceful exit for the `uvicorn` server and calls `unload_brain()` on the `BrainHub` to release VRAM. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The module follows a strict lifecycle: `__init__` (config) $\rightarrow$ `initialize` (dependency injection and app creation) $\rightarrow$ `start` (threading) $\rightarrow$ `shutdown` (cleanup). It utilizes `uvicorn.Server` to manage the ASGI lifecycle, specifically using the `should_exit` flag for controlled shutdowns.
- **Side Effects:** 
    - **Network:** Binds to a specified host and port to listen for incoming HTTP requests.
    - **Concurrency:** Spawns a new `threading.Thread` to run the server.
    - **Resource Management:** Directly impacts GPU/System memory by triggering model unloading via the `BrainHub` during shutdown.
- **Error Handling:** 
    - Logs a warning if `initialize` is called on an already initialized module.
    - Logs an error if `start` is attempted before `initialize` has successfully configured the server.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `host` (str)  The IP address to bind the server to (defaults to `"0.0.0.0"`).
- `port` (int)  The network port for the API (defaults to `8000`).

**Module Dependencies:**
- **Standard/External:** `threading`, `typing`, `uvicorn`, `fastapi`.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.services.history_manager](/AgentDocs/ai/services/history_manager.md)
    - [ai.modules.base_module](/AgentDocs/ai/modules/base_module.md)
    - [ai.modules.server.brain_hub](/AgentDocs/ai/modules/server/brain_hub.md)
    - [ai.modules.server.app](/AgentDocs/ai/modules/server/app.md)