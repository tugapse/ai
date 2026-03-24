# Agent Execution Framework (Runtime & Logic)

This document outlines the architecture of the AI Agent system, focusing on how reasoning is translated into system-level actions through our specialized Toolset.

---

## 🤖 The Interaction Loop (Reasoning & Feedback)

The system operates on a continuous feedback loop known as **ReAct** (Reason + Act). This ensures that the agent doesn't just "guess" but actually observes the results of its actions.

### 1. State Discovery (Observation)
The loop always begins with the agent orienting itself within the environment.
* **Action**: The agent typically executes `get_root` and `read_dir`.
* **Goal**: To map the file structure and prevent "hallucinations" regarding file paths or project hierarchy.

### 2. The Step-by-Step Cycle
1.  **Thought**: The LLM generates internal reasoning (often wrapped in `<think>` tags). It analyzes the task and decides which tool is required.
2.  **Action**: The orchestrator extracts the structured tool call (JSON) and executes the corresponding Linux/Python function.
3.  **Observation**: The output of the tool (e.g., lines found by `grep` or file content) is fed back into the agent’s prompt as a "System" or "Tool" message.
4.  **Evaluation**: The agent evaluates if the goal was met. If the tool returned a `FAILED` status, the agent adjusts its strategy and tries again.

---

## 🛠️ Specialized Toolset (Linux-Native API)

Our tools are designed to be "LLM-friendly," providing structured outputs that are easy for models to parse and act upon.

### Core Capabilities:

| Tool | Purpose | Key Feature |
| :--- | :--- | :--- |
| `read_dir` | Explores the filesystem. | Returns distinct lists of files and folders. |
| `read_file` | Retrieves code/text content. | **1MB Safety Limit** to prevent context window overflow. |
| `write_file` | Modifies or creates files. | Uses `os.fsync` for **Atomic Persistence** (data is physically synced). |
| `grep_file` | High-speed pattern matching. | Uses **Native Linux Grep** with line numbers and context (`-C`). |
| `delete_item` | Cleanup and refactoring. | Recursive deletion with strict path validation. |

---

## 🔒 Security & Robustness (The "Safety Jail")

To ensure the agent remains helpful and harmless to the host system, multiple layers of protection are active:

* **Logical Chroot**: Every tool uses a `_is_safe_path` filter. The agent is strictly prohibited from accessing, reading, or deleting files outside the defined `PROJECT_ROOT`.
* **Context Protection**: The system automatically detects binary files or oversized text files. Instead of crashing the session, it returns a structured error, forcing the agent to use more efficient tools like `grep_file`.
* **Atomic Operations**: By forcing disk synchronization on every write, we ensure that the file system remains in a consistent state even if the process is interrupted.

---

## 🗺️ Execution Flow Diagram

```mermaid
sequenceDiagram
    participant A as AI Agent (LLM)
    participant O as Orchestrator
    participant T as Toolset (Linux/Python)
    participant D as Disk/OS

    A->>O: Request Action (e.g., grep_file "API_KEY")
    O->>T: Validate Path & Permissions
    T->>D: Execute Native Linux Command
    D-->>T: System Output
    T-->>O: Format as JSON (Status: SUCCESS)
    O-->>A: Provide Observation (Tool Output)
    A->>A: Reason on Output
    Note over A: Goal Reached? If not, repeat loop.