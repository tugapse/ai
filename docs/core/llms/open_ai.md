## 1. Architectural Role
Provides a standardized, OpenAI-compatible API interface that implements the Sentinel Protocol by flattening tool calls and results into pure text to ensure provider-agnostic reasoning and tool execution.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `OpenAIAPIModel` | Class | Manages connection, request formatting, and stream interception for OpenAI/Azure/Compatible APIs. |
| `__init__` | Method | Initializes client (OpenAI or AzureOpenAI), configures model parameters, and sets telemetry bounds. |
| `_convert_messages` | Method | Transforms internal message history into OpenAI schema, flattening tool/function roles into text-based Sentinel tags. |
| `chat` | Method | Primary entry point for synchronous or streaming chat completions; handles dynamic system prompt injection. |
| `_run_streaming_chat` | Method | Manages the generator loop for streaming responses, including telemetry updates and Sentinel tag interception. |
| `_update_token_metrics` | Method | Synchronizes API usage data (prompt, completion, total tokens) with internal telemetry counters. |
| `clean_cache` | Method | Triggers manual garbage collection to release memory buffers. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Resolves `model_name`, `api_key`, and `system_prompt` from arguments or environment variables.
    2. Instantiates `OpenAI` or `AzureOpenAI` client based on the presence of `azure_endpoint`.
    3. Configures `options` dictionary: uses `max_completion_tokens` for reasoning models (o1/nano) or `max_tokens` + sampling parameters for standard models.
    4. Sets telemetry bounds for `token_info_count`.
- **Data Path**: 
    1. **Input**: `messages` (List[Dict]), `tools` (Optional), `stream` (bool), `options` (Optional).
    2. **Processing**: 
        - `_convert_messages` maps roles: `tool`/`function` $\rightarrow$ `user` (with system prefix); `assistant` (with tool calls) $\rightarrow$ `assistant` (with `____@tool` prefix).
        - `chat` passes formatted messages to `client.chat.completions.create`.
        - If streaming: `_run_streaming_chat` iterates through chunks, accumulating `full_content` and passing fragments to `handle_sentinel`.
    3. **Output**: Returns a `str` (sync), `Dict` (action), or `Generator` (stream).
- **Conditional Branching**:
    - **Client Routing**: `if self.azure_endpoint` selects `AzureOpenAI` vs `OpenAI`.
    - **Model Capability**: `if is_reasoning_model` toggles parameter keys (`max_completion_tokens` vs `max_tokens`).
    - **Execution Mode**: `if stream` routes to `_run_streaming_chat` or executes synchronous completion.
    - **Interception**: `if action` (via `parse_manual_tags` or `handle_sentinel`) triggers tool execution logic instead of returning raw text.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `threading`, `gc`, `json`, `typing`
- **Internal Modules**: `.base_llm` (`BaseModel`), `functions` (`func`), `color` (`Color`)
- **External Packages**: `openai`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `BaseModel.CONTEXT_WINDOW_128K` (Default context size)
    - `BaseModel.STREAMING_FINISHED_EVENT` (Event trigger)
    - `"2024-05-01-preview"` (Default Azure API version)
    - `"____@tool call:"` (Sentinel protocol prefix)
- **Environment Lookups**: 
    - `AI_MODEL_NAME`
    - `AI_API_KEY`
    - `AI_API_VERSION`
    - `AI_AZURE_ENDPOINT`