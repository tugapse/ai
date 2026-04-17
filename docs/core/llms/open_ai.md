## 1. Architectural Role
Provides a lazy-loading implementation of the `BaseModel` to interface with the OpenAI API for both synchronous and asynchronous streaming text generation.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `OpenAIAPIModel` | Class | Orchestrates OpenAI API client lifecycle, message formatting, and generation streams. |
| `__init__` | Method | Initializes API client, validates credentials, and sets default generation hyperparameters. |
| `_convert_messages` | Method | Transforms internal message lists into the OpenAI-specific `role`/`content` schema, prepending the system prompt. |
| `chat` | Method | Entry point for generation; branches between synchronous response and threaded streaming. |
| `_run_streaming_chat` | Method | Internal worker thread that iterates over the OpenAI stream and triggers "token" events. |
| `clean_cache` | Method | Forces garbage collection of the instance memory. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Calls `super().__init__`.
    2. Attempts lazy import of `OpenAI` from the `openai` package.
    3. Resolves `api_key` from arguments or `os.environ`.
    4. Instantiates `self.client`.
    5. Maps `kargs` to a `self.options` dictionary (temperature, max_tokens, top_p, presence_penalty, frequency_penalty).
- **Data Path**: 
    `messages` (list) $\rightarrow$ `_convert_messages` $\rightarrow$ `self.client.chat.completions.create` $\rightarrow$ `response.choices[0].message.content` (Sync) OR `self.trigger("token", ...)` (Stream).
- **Conditional Branching**:
    - **Dependency Check**: If `openai` package is missing $\rightarrow$ Raise `ImportError`.
    - **Auth Check**: If `api_key` is null $\rightarrow$ Raise `ValueError`.
    - **Execution Mode**: If `stream` is `True` $\rightarrow$ Spawn `_generation_thread` $\rightarrow$ `_run_streaming_chat`; Else $\rightarrow$ Execute synchronous API call.
    - **Stream Interruption**: Inside `_run_streaming_chat`, if `self.stop_generation_event` is set $\rightarrow$ Break loop.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `threading`, `gc`
- **Internal Modules**: `.base_llm` (`BaseModel`), `functions` (`func`)
- **External Packages**: `openai`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `model_name` default: `"gpt-4o"`
    - `temperature` default: `0.5`
    - `max_tokens` default: `2048`
    - `top_p` default: `0.95`
    - `presence_penalty` default: `0.0`
    - `frequency_penalty` default: `0.0`
- **Environment Lookups**: `OPENAI_API_KEY`