## 1. Architectural Role
| Name | Source file |
| :--- | :--- |
| **MessageOrchestrator** | [/src/ai/agents/message_orchestrator.py](/src/ai/agents/message_orchestrator.py) |

The MessageOrchestrator serves as the central conductor of the multi-agent execution framework. It coordinates routing decisions, maintains session state, and enforces context protection and persistence across iterations. By integrating memory management, sentinel-based context control, and specialized agents (e.g., SpecialistManager, ContextSentinel, SessionVault), it steers the lifecycle of a run from hydration of a persisted session to the orderly progression of agent turns, tool invocation, and response handling. This component is essential for maintaining coherent, stateful conversations that span multiple agents and iterations, while ensuring that long-term and short-term context remain consistent and recoverable.

In the broader system, the **MessageOrchestrator** interfaces with several subsystems to drive execution. It relies on:
- [Specialist Manager](/docs/ai/agents/specialist_manager.md) for domain-specific tools and content generation.
- [Memory Manager](/docs/ai/agents/memory_manager.md) to track per-agent state, messages, notes, and history.
- [Context Sentinel](/docs/ai/agents/context_sentinel.md) to enforce context limits and distill meaningful context.
- [Session Vault](/docs/ai/agents/session_vault.md) to persist and hydrate session state across runs.
- [Events](/docs/ai/core/events.md) as the eventing backbone for pre/post LLM request hooks.
- Tool and module registries to discover and execute tools safely, with optional gating via the [ToolRegistry](/docs/ai/tools/tool_registry.md) and [ModuleRegistry](/docs/ai/services/module_registry.md).
- [Vector Memory](/docs/ai/modules/memory/vector_memory.md) for long-term memory retrieval when appropriate.

These interactions ensure that data and state transition smoothly between stages (input gathering, payload preparation, LLM interaction, and response processing) while preserving the ability to recover or resume sessions.

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
- **MAX_ITERATIONS** (Default: 100)  Caps the main execution loop to bound runtime and prevent runaway cycles.
- **MANAGER_AGENT_ROLE** (Default: "management")  Distinguishes the manager/lead agent role within tool access and orchestration.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `MessageOrchestrator` | Class | Orchestrates multi-agent execution, session hydration/persistence, context management, and inter-agent communication flow. |

External/internal references and interactions:
- Coordinates with [Specialist Manager](/docs/ai/agents/specialist_manager.md) for specialized tool usage.
- Interfaces with [Memory Manager](/docs/ai/agents/memory_manager.md) to manage per-agent messages, notes, and history.
- Uses [Context Sentinel](/docs/ai/agents/context_sentinel.md) to enforce context limits and distill relevant context.
- Persists and hydrates state via [Session Vault](/docs/ai/agents/session_vault.md).
- Triggers lifecycle events related to LLM requests via [Events](/docs/ai/core/events.md).
- Accesses and registers tools through [ToolRegistry](/docs/ai/tools/tool_registry.md) and [ModuleRegistry](/docs/ai/services/module_registry.md).
- Adopts long-term memory strategies via [VectorMemory](/docs/ai/modules/memory/vector_memory.md).

## 4. Code Example
# Example: instantiate and run a simple orchestration
from ai.agents.message_orchestrator import MessageOrchestrator

```python
# Assume connector, registry, module_registry, and config provided by the system
connector = ...  # Integrated LLM connector
registry = ...  # Tool registry instance
module_registry = ...  # Module registry instance
pipeline_config = {
    "agents": {
        "MASTER": {"tools": ["write_file", "execute_command"]},
    },
    "entry_point": "MASTER",
}
session_id = "sess-001"

mo = MessageOrchestrator(connector, registry, pipeline_config, module_registry)
mo.run_loop("Define and pursue objective: optimize data pipeline logging.", session_id)
```

## 5. Execution Logic & Flow
- Initialization
  - Create and attach Specialized Managers (SpecialistManager, ContextSentinel) and memory/session components (MemoryManager, SessionVault).
  - Initialize or hydrate session state via _start_hidration_state, applying persisted state if available.
  - Resolve the starting agent and starting iteration count.
- Data Path
  - For each iteration, validate the current_agent from memory.
  - Update the agents current task from recent messages.
  - Assemble the agents tooling set via _assemble_agent_tools and enrich the payload with agent notes, history, plan, and context.
  - Apply context-sentinel limits to the payload; possibly compress context and emit a sentinel notice.
  - Emit before_llm_request event, send request to the LLM, then emit after_llm_request with the response.
  - Handle response: format errors, process agent response to determine next_agent, and persist state via SessionVault.
- Conditional Branching
  - If the response status is "FAILED" and format error threshold is reached, halt; otherwise, attempt recovery and retry.
  - If next_agent resolves to "DONE", clear agent memory and switch to the next agent (MASTER) for continuity.
  - Gatekeeper prompts for sensitive tools (e.g., execute_command) with potential auto-authorization (all) via _gatekeeper.
  - Validate target transitions; if invalid, route to a safe default (the current agent) and log as needed.

## 6. Resource Dependencies
- **Standard Libraries**: os, copy, json, typing
- **Internal Modules**: 
  - [MessageOrchestrator](/docs/ai/agents/message_orchestrator.md) (Referenced by the code itself as the orchestrator)
  - [Events](/docs/ai/core/events.md)
  - [TerminalUI](/docs/ai/agents/terminal_ui.md)
  - [Specialist Manager](/docs/ai/agents/specialist_manager.md)
  - [Memory Manager](/docs/ai/agents/memory_manager.md)
  - [Context Sentinel](/docs/ai/agents/context_sentinel.md)
  - [Session Vault](/docs/ai/agents/session_vault.md)
  - [Vector Memory](/docs/ai/modules/memory/vector_memory.md)
  - [Color](/docs/ai/color.md)
  - [Tool Registry](/docs/ai/tools/tool_registry.md)
  - [Module Registry](/docs/ai/services/module_registry.md)
- **External Packages**: None explicitly required beyond the project's own modules

Note: All internal cross-links reference repository-absolute paths as mandated by the manifest.