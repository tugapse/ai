## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **JarvisServerModule** | [src/ai/modules/server/server_module.py](/AgentDocs/ai/modules/server/server_module.md) |

The `JarvisServerModule` serves as a high-level wrapper for the JARVIS Brain Server, providing a standardized interface that adheres to the system's module lifecycle. Its primary responsibility is to manage the lifecycle of a FastAPI-based web server, allowing the AI's core intelligence to be exposed via a network interface.

Within the broader architecture, this component acts as a bridge between the internal model orchestration logic and external consumers. It encapsulates the initialization of the `BrainHub`, the creation of the FastAPI application, and the management of the Uvicorn server process running in a background thread.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `JarvisServerModule` | Class | The main module class responsible for managing the Brain Server lifecycle. |
| `__init__(host, port, **kwargs)` | Method | Initializes the server configuration with a specific host and port. |
| `initialize(config, orchestrator, history_manager)` | Method | Sets up the `BrainHub`, creates the FastAPI app via `create_app`, and configures the Uvicorn server. |
| `start()` | Method | Spawns a daemon thread to run the Uvicorn server, preventing it from blocking the main application thread. |
| `get_instance()` | Method | Returns the currently active `BrainHub` instance. |
| `shutdown()` | Method | Signals the Uvicorn server to exit and triggers the unloading of the brain to release VRAM. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The module implements a lifecycle pattern (initialize $\rightarrow$ start $\rightarrow$ shutdown). It uses `BrainHub` to wrap the `ModelOrchestrator` and passes this hub into `create_app` to inject intelligence into the API endpoints. The server itself is executed within a `threading.Thread` marked as `daemon=True` to ensure it does not prevent the main process from exiting.
- **Side Effects:** 
    - **Network:** Binds to a specified IP and port to listen for incoming HTTP requests.
    - **Resource Management:** Explicitly calls `unload_brain()` during shutdown to manage VRAM/memory usage.
    - **Concurrency:** Spawns a new system thread for the Uvicorn event loop.
- **Error Handling:** Logs errors via `func.log` or `func.error` if the server is started without being initialized. It includes checks to prevent double-initialization.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `host` (str)  The IP address to bind the server to (defaults to `0.0.0.0`).
- `port` (int)  The network port for the API (defaults to `8000`).

**Module Dependencies:**
- **Standard/External:** `threading`, `typing`, `uvicorn`, `fastapi`.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.services.history_manager](/AgentDocs/ai/services/history_manager.md)
    - [ai.modules.base_module](/AgentDocs/ai/modules/base_module.md)
    - [ai.modules.server.brain_hub](/AgentDocs/ai/modules/server/brain_hub.md)
    - [ai.modules.server.app](/AgentDocs/ai/modules/server/app.md)