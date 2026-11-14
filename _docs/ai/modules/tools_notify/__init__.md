## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| tools_notify | ai/modules/tools_notify/__init__.md |

This component initializes the notification toolset, providing the agent with the capability to send desktop notifications. Its primary responsibility is to expose the necessary tool function (`send_notification`) so that the agent workflow can trigger asynchronous feedback to the user regarding task completion or status changes.

This module acts as the entry point and factory for the `tools_notify` functionality within the application architecture. It leverages the base `ToolModule` from [ai/modules/base_module.md] to register the defined tools, making them discoverable by the core agent system.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `create_module()` | Function | Instantiates and returns the `ToolModule` object for the notification tools. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The module aggregates the `send_notification` function into a list called `TOOLS` and uses `create_module()` to wrap this collection into a structured `ToolModule` instance.
- **Side Effects:** The function `send_notification` itself (imported from [ai/modules/tools_notify/tools.md]) is responsible for the actual side effects, which typically involve OS-level interaction (desktop notification triggering).
- **Error Handling:** No explicit error handling is defined within this initialization file; error handling for the notification mechanism resides within the imported tool implementation.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- TOOLS_NOTIFY_ENABLED — Controls whether the notification tool is active; defaults to true if not explicitly set in config.json.

**Module Dependencies:**
- **Standard/External:** None
- **Internal:** [ai/modules/base_module.md]
- **Internal:** [ai/modules/tools_notify/tools.md]