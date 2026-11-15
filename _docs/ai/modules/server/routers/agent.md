## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| Agent | /ai/modules/server/routers/agent.md |

This component defines the API endpoints for managing and running agent pipelines, tasks, and sessions via a web client interface. It acts as the primary interface layer, routing requests related to agent execution—such as starting a run, listing available tools, or saving pipeline configurations—to the appropriate service logic.

As a router, it sits within the controller layer of the application architecture. It depends heavily on the authentication and device management provided by [routers/auth.md] and delegates core operational tasks (like starting runs or reading configurations) to the business logic contained within [services/agent_runs.md] and [services/pipelines.md].

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `AgentRunRequest` | Class | Defines the parameters required to start an agent run (prompt, pipeline, task, etc.). |
| `PermissionAnswer` | Class | Defines the response structure for answering permission requests during a run. |
| `pipelines` | Function | Retrieves a list of available pipelines. |
| `tools` | Function | Retrieves a list of tools available to agent pipelines. |
| `pipeline` | Function | Reads the content of a specific pipeline by name. |
| `save_pipeline` | Function | Validates and overwrites an existing pipeline configuration. |
| `create_pipeline` | Function | Validates and creates a new pipeline in the user's folder. |
| `delete_pipeline` | Function | Deletes a pipeline, checking if it is currently in use. |
| `tasks` | Function | Retrieves a list of available task templates. |
| `task` | Function | Reads the content of a specific task template by name. |
| `sessions` | Function | Retrieves a list of saved run sessions, optionally filtered by current working directory (`cwd`). |
| `session` | Function | Retrieves the transcript for a specific saved session ID. |
| `workspace` | Function | Returns information about the agent's workspace structure. |
| `fs_list` | Function | Lists the contents (files and folders) of a specified path within the filesystem. |
| `fs_mkdir` | Function | Creates a new absolute folder, including any necessary parent directories. |
| `workspace_list` | Function | Lists folders and files within the workspace, relative to the workspace root. |
| `workspace_mkdir` | Function | Creates a new folder within the defined workspace area. |
| `start_run` | Function | Initiates a new agent run, returning a streaming response of events. |
| `run_events` | Function | Replays or streams the events of a specific run ID, allowing for reattachment. |
| `current_run` | Function | Provides status information about the currently active or most recently finished run. |
| `permission` | Function | Allows the user to respond to a permission request during an active run. |
| `cancel` | Function | Sends a signal to stop a running agent process at the next safe point. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The router handles HTTP request parsing and validation using Pydantic models. It acts as a dispatcher, calling internal service methods (e.g., `service.start` or `pipelines.read`) based on the endpoint. For streaming endpoints (`/runs`), it utilizes an `asyncio` loop to continuously poll the underlying service for new events, yielding them as Server-Sent Events (SSE).
- **Side Effects:** Extensive interaction with the filesystem (reading/writing pipelines, tasks, sessions, and creating directories via `_service(request).list_folder`, `pipelines.save`, `fs_mkdir`, etc.). It also interacts with external state managed by the `AgentRunService` (e.g., starting/canceling runs, auditing).
- **Error Handling:** It wraps service calls using `_call` and `_pipeline_call` to catch specific application exceptions (`AgentApiError`, `PipelineError`) and translates them into standard HTTP exceptions (`HTTPException`) with appropriate status codes. It also handles the rate-limiting context when processing permission responses by interacting with the authentication state.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `asyncio`, `json`, `typing`, `fastapi`, `pydantic`.
- **Internal:** [routers/auth.md] (via `require_device`), [services/agent_runs.md], [services/pipelines.md], [ai.agents.agent_orchestrator.md] (via `get_hil_tools`).