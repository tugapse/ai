## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| MemoryManager | ai/agents/memory_manager |

This component is responsible for centralized, persistent state management across the entire AI orchestration system. Its primary responsibility is to maintain the memory state for individual agents (including their notes, history, and current tasks) and to manage the global context of the orchestration pipeline, such as tool execution results and the overall plan execution progress.

It acts as the core state service for the entire application, decoupling the execution logic from state persistence. It allows for serialization of the entire system state into a dictionary for saving and subsequent loading, ensuring that agents can resume tasks exactly where they left off by interfacing with [OrchestratorContext](/ai/agents/memory_manager.md) and [AgentMemory](/ai/agents/memory_manager.md).

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| AgentMemory | Class | Data structure holding the state for a single agent, including notes, history, and task status. |
| OrchestratorContext | Class | Data structure holding the global state of the orchestration pipeline, including task plans and tool results. |
| MemoryManager | Class | Manages the collection of agent memories and the global context, providing serialization, loading, and state mutation methods. |
| serialize | Method | Collapses the live memory state into a serializable dictionary format. |
| load_state | Method | Restores the memory state from a provided serialized dictionary. |
| get_agent_memory | Method | Retrieves the specific AgentMemory object associated with a given agent name. |
| add_message_to_agent | Method | Adds a message payload to a target agent's incoming message queue, creating the agent if necessary. |
| record_tool_result | Method | Logs a tool execution result into the global context and notifies the executing agent. |
| update_agent_history_and_notes | Method | Updates an agent's internal state by archiving received messages into history and incorporating new thoughts/notes. |
| check_stagnation | Method | Tracks tool call fingerprints to detect repetitive or looping behavior in the execution plan. |
| clear | Method | Resets the state of a specific agent's memory and clears the global context results. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The manager uses dictionaries keyed by agent names to hold instances of [AgentMemory](/ai/agents/memory_manager.md). State updates are transactional within method calls (e.g., `add_message_to_agent` uses `setdefault` to ensure agent existence before modification). The `check_stagnation` method implements a sliding window history check on tool call fingerprints (`tool_name-json_params`) to detect loops.
- **Side Effects:** Mutates internal state (self.context and self.agents) upon method calls like `record_tool_result`, `add_message_to_agent`, and `update_agent_history_and_notes`. The `serialize` method prepares state for external persistence (I/O operation potential).
- **Error Handling:** `load_state` gracefully handles missing keys by using `.get()` with default empty structures. `get_agent_memory` safely returns `None` if the requested agent name does not exist.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `json`, `dataclasses`, `typing`
- **Internal:** None