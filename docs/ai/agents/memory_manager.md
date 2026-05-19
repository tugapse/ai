## 1. Architectural Role
| Name | Source file |
| :--- | :--- |
| Memory Manager | [/src/ai/agents/memory_manager.py](/src/ai/agents/memory_manager.py)|

The **Memory Manager** component serves as the central memory and state caretaker for the orchestration platform. It encapsulates per-agent memory (AgentMemory) and a global orchestration context (OrchestratorContext), providing a serializable snapshot of the live runtime state and the ability to hydrate state from persisted data. By coupling per-agent histories with a shared contextual state, it enables consistent progress tracking, auditability, and fault-tolerant recovery across multiple agents and steps in the pipeline.

Strategically, Memory Manager sits at the intersection of agent interaction and pipeline orchestration. It aggregates agent histories, manages tool results in a global context, and exposes APIs to update agent thoughts, responses, and task progression. This design supports persistence, replay, and cross-agent coordination, while keeping agent-specific data isolated and easily serializable for storage or transport. Through its lifecycle methods (serialize, hydrate, record_tool_result, update_agent_history_and_notes, etc.), it acts as the backbone for the execution flows state machine and the data path between incoming messages, tool invocations, and agent reflections.

- System-wide state coordination and persistence enable downstream components to reconstruct or inspect the current execution state from a single, canonical representation.
- Agent-specific memory and global context separation ensure modular handling of histories and responses, while enabling consistent transitions between steps and tasks.


## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `MemoryManager` | Class | Manages the state of the orchestrator and all agents with persistence support; provides serialization/hydration, agent message handling, tool result recording, history updates, stagnation checks, and resets. |
| `AgentMemory` | Class | Stores the internal state and history of a single agent. |
| `OrchestratorContext` | Class | Stores the global context for the orchestration pipeline (tool results, current task, plan, step index, etc.). |

## 4. Code Example
```python

from ai.agents.memory_manager import MemoryManager

# Initialize with a set of agent names
mm = MemoryManager(["agent_A", "agent_B"])

# Send a message to an agent
mm.add_message_to_agent("agent_A", {"from": "SYSTEM", "payload": "Hello Agent A"})

# Serialize current memory state
state = mm.serialize()

# Hydrate a fresh manager from the serialized state
mm_restored = MemoryManager(["agent_A", "agent_B"])
mm_restored.hydrate(state)

```

## 5. Execution Logic & Flow
- Initialization
  - MemoryManager is instantiated with a list of agent names. It creates an in-memory AgentMemory per agent and a fresh OrchestratorContext.
- Data Path
  - serialize() collapses current context and all agent memories into a serializable dictionary.
  - hydrate(data) restores context and agent memories from a dictionary, applying values only for keys present on respective objects.
- Conditional Branching
  - check_stagnation(tool_name, params) builds a fingerprint from the tool call and parameters, tracks repeats, and signals potential architectural loops if the same operation recurs (>= 3 times).
- Processing & Updates
  - add_message_to_agent(target_agent, message_payload) queues messages for agents, creating memory on-demand.
  - record_tool_result(...) appends results to the global tool_results and advances current_step_index on success; also notifies the agent with a system message about the tool result.
  - update_agent_history_and_notes(agent_name, response) moves pending messages to history, updates notes and manifest, and records a new SELF-thought/response entry.
- Reset / Maintenance
  - clear(agent) resets per-agent memory and clears the global tool results context.

## 6. Resource Dependencies
- **Standard Libraries**: json, dataclasses (imported via dataclass, field, asdict), typing (Dict, Any, Optional, List)
- **Internal Modules**: None explicitly imported; all functionality is defined within this file (MemoryManager, AgentMemory, OrchestratorContext) and relies on repository documentation for cross-links.
- **External Packages**: None

