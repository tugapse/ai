## 1. Architectural Role
| Name | Source file |
| :--- | :--- |
| ContextSentinel | [src/ai/agents/context_sentinel.py](/src/ai/agents/context_sentinel.py) |

The ContextSentinel component acts as a guard and optimizer for active-context pressure within an agent. It monitors the per-turn context usage and proactively distills and archives high-entropy outputs (such as large results from SYSTEM messages) into Long-Term Memory (LTM). By pruning the immediate conversation history and replacing dense outputs with concise summaries, it preserves essential factual content while freeing contextual space for ongoing reasoning. This helps sustain robust performance in constrained runtime environments and supports reliable recovery of important facts from historical activity.

Strategically, ContextSentinel serves as an architectural sink for technical artifacts (code results, logs) that would otherwise bloat the active context. It integrates with the memory subsystems (memory_manager and vector_memory) to offload critical data, ensuring downstream modules receive a lean but fact-rich payload. It also provides an explicit, auditable path for transforming raw outputs into structured summaries, enabling better traceability and LTM augmentation as part of the systems long-term knowledge management.

Cross-linking in-system references:
- [ai.functions](/docs/ai/functions.md)
- [Color](/docs/ai/color.md)

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| ContextSentinel | Class | Monitors context pressure and performs distilled compression of tool outputs. Archives technical facts to Long-Term Memory (LTM) before pruning state. |

## 4. Code Example
from ai.agents.context_sentinel import ContextSentinel

# Example setup (replace with real implementations)
```python
connector = my_connector  # LLM connector implementing send_raw_request
memory_manager = memory_mgr  # memory manager instance
vector_memory = vector_mem  # optional vector memory instance

sentinel = ContextSentinel(connector=connector, threshold=0.8, max_tokens=20000, buffer=1024)

payload = {
    "recent_outcomes": [],
    "messages_received": [],
    "conversation_history": []
}

updated_payload, changed = sentinel.enforce_limits("agent1", memory_manager, payload, vector_memory)
```

## 5. Execution Logic & Flow
- Initialization
  - ContextSentinel is constructed with a connector, threshold, max_tokens, and a safety buffer.
- Data Path
  - est_tokens = estimated size of payload, using heuristic digits.
  - delta = max_tokens - buffer; pressure = est_tokens / delta.
  - If pressure < threshold: return payload unchanged, False.
  - Otherwise, log a pressure warning and begin archiving steps.
- Processing & Archiving
  - Retrieve agent-specific memory via memory_manager.get_agent_memory(agent_name).
  - For each received SYSTEM message carrying a "result":
    - If the result payload is large (> 2000 chars when serialized), create a distilled summary using _summarize_data.
    - If vector_memory is provided, archive the distilled summary (content) with memory_type "distilled_observation".
    - Update the specific message's "result" with a high-level summary and metadata.
- Pruning & Reassembly
  - Prune agent history to the last 3 turns.
  - Rebuild the outgoing payload to reflect the lean state with updated messages and history.
- Return
  - Return the updated payload and a boolean flag indicating changes (True when pruning occurred).

## 6. Resource Dependencies
- **Standard Libraries**: json
- **Internal Modules**: 
  - [ai.functions](/docs/ai/functions.md)
  - [Color](/docs/ai/color.md)
  - [ContextSentinel](/docs/ai/agents/context_sentinel.md)
- **External Packages**: None

Direct exports or structural definitions only; no internal logic flow.