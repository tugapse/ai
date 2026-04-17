## 1. Architectural Role
The `ContextSentinel` manages LLM context window pressure by distilling voluminous tool outputs into technical summaries and pruning conversation history to prevent token overflow.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ContextSentinel` | Class | Orchestrates context monitoring, data distillation, and memory pruning. |
| `__init__` | Method | Initializes the sentinel with a connector, pressure threshold, and token limit. |
| `enforce_limits` | Method | Evaluates context pressure and executes memory surgery (distillation/pruning) if thresholds are exceeded. |
| `_summarize_data` | Method | Performs a blocking LLM request to convert raw data into a dense technical fact sheet. |

## 3. Execution Logic & Flow
- **Initialization**: Sets `self.connector` (LLM interface), `self.threshold` (trigger percentage), and `self.max_tokens` (hardware limit).
- **Data Path**: 
    1. **Pressure Calculation**: `payload` $\rightarrow$ `json.dumps` $\rightarrow$ character count $\div$ 3.2 $\rightarrow$ `est_tokens` $\div$ `max_tokens` $\rightarrow$ `pressure`.
    2. **Evaluation**: If `pressure < self.threshold`, return `payload` unchanged.
    3. **Distillation**: If `pressure \ge self.threshold`, iterate through `agent_memory.messages_received`.
    4. **Filtering**: Identify `SYSTEM` messages containing `result` keys where the JSON string length exceeds 2000 characters.
    5. **Transformation**: `raw_result` $\rightarrow$ `_summarize_data` (LLM call) $\rightarrow$ `distilled` summary.
    6. **Archiving**: If `vector_memory` is present, save `distilled` content as `distilled_observation`.
    7. **Replacement**: Replace raw `result` in `agent_memory` with a summary object containing `status`, `summary`, and `metadata`.
    8. **Pruning**: Slice `agent_memory.history` to retain only the last 3 entries.
    9. **Reconstruction**: Update `payload` with the pruned `recent_outcomes`, `messages_received`, and `conversation_history`.
- **Conditional Branching**:
    - **Pressure Check**: Determines if any memory surgery is required.
    - **Payload Size Check**: Determines if a specific tool output is "heavy" enough to require distillation.
    - **Vector Memory Availability**: Determines if the distilled summary is archived to long-term memory.

## 4. Resource Dependencies
- **Standard Libraries**: `json`, `typing`
- **Internal Modules**: `functions` (as `func`), `color` (as `Color`)
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `3.2`: Token estimation divisor (characters per token).
    - `2000`: Character threshold for triggering distillation of a specific message.
    - `3`: Maximum number of history turns retained after pruning.
- **Environment Lookups**: None