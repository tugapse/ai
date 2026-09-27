## 1. Architectural Role
| Name | Source file |
| :--- | :--- |
| **SessionVault** | [/src/ai/agents/session_vault.py](/src/ai/agents/session_vault.py) |

The SessionVault component is responsible for persisting and rehydrating the per-session orchestrator state for agents. It provides a lightweight, append-only journaling mechanism that stores state snapshots (and optional compressed payloads) in a per-session JSONL-style file. This enables the system to maintain a historical trace of session progress, support recovery after restarts, and aid debugging by exposing a turn-by-turn view of state transitions.

Strategically, SessionVault sits at the boundary between the execution engine and long-term state management. It consumes the in-memory orchestrator state produced by the agent runtime and writes it to durable storage, ensuring a consistent, incremental history that downstream components (e.g., history managers, debuggers, or session loaders) can consume. By providing both commit and hydrate semantics, it enables seamless progression through iterations while offering a straightforward restoration path to a chosen turn/index.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No explicit hardcoded constants identified (the code uses a literal "1.0" for versioning within the payload, but no named constant is defined in the file).

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| SessionVault | Class | Manages persistence for agent sessions by persisting orchestrator state to a per-session JSON journal and hydrating state from that journal. |

## 4. Code Example
- Example usage:
```python
from ai.agents.session_vault import SessionVault

vault = SessionVault("session-123")
vault.commit({"iteration": 1, "current_agent": "AgentA"}, compress=False)

# loads and returns the state at the end of turn 3
state = vault.hydrate(turn_index=3)

# loads and returns the state last turn (turn_index=-1)
state = vault.hydrate()
```

## 5. Execution Logic & Flow
- Initialization:
  - The constructor takes a session_id, computes storage paths based on the repository root, and ensures the storage directory exists.
- Data Path:
  - commit(orchestrator_state, compress=False) creates a payload with timestamp, state, and version, serializes to JSON, optionally compresses as a base64-encoded zlib blob, and appends it to the per-session file.
- Conditional Branching:
  - If compression is requested, the payload is replaced with a compressed, base64-encoded data field and a compressed flag; otherwise, the plain state is written.
  - hydrate(turn_index=-1) reads the per-session file, selects the line corresponding to the index, decompresses if needed, and returns the state for resuming execution. Errors are logged and None is returned on failure.
- Termination/Failure:
  - All exceptions in commit or hydrate are caught and logged; hydration returns None on failure, allowing the caller to decide on fallback behavior.

## 6. Resource Dependencies
- **Standard Libraries**: os, json, zlib, base64, datetime, timezone, typing
- **Internal Modules**: 
  - [ai.functions](/docs/ai/functions.md)
  - [SessionVault Documentation](/docs/ai/agents/session_vault.md)
  - [SessionVault Source](/src/ai/agents/session_vault.py)
- **External Packages**: None