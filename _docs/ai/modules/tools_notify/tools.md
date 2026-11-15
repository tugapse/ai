## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| tools_notify | /ai/modules/tools_notify/tools.md |

This component provides the `send_notification` tool, enabling the agent to display desktop notifications to the user when a significant event occurs or when the user is expected to be waiting for a result. Its primary responsibility is to abstract the platform-specific mechanisms required to trigger these alerts across different operating systems.

It functions as a crucial service layer component within the broader agent architecture. It interfaces with the operating system's native notification APIs (like `notify-send` on Linux or `osascript` on macOS) to provide timely, attention-grabbing feedback to the user, fitting into the agent's execution flow after long-running tasks are complete.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| send_notification | Function | Shows a desktop notification to the user. Accepts `message`, `title`, and `urgency`. Returns a status dictionary indicating success, failure, and the method used. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The function first validates that a message is provided. It then determines the appropriate platform command using `_notify_command`, which checks `sys.platform` to select between Linux (`notify-send`) or macOS (`osascript`). If no platform notifier is found, it defaults to printing a terminal bell character (`\a`). Finally, it executes the chosen command using `subprocess.run` with a timeout.

- **Side Effects:** Spawns external processes (e.g., `notify-send`, `osascript`) depending on the operating system. It also writes to `sys.__stdout__` if no desktop notifier is available.

- **Error Handling:** Catches general exceptions during subprocess execution. If the external command returns a non-zero exit code, it captures and returns the standard error or standard output as the failure reason.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `shutil`, `subprocess`, `sys`, `typing`
- **Internal:** [ai.tools.base/base.md]