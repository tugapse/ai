## 1. Architectural Role
`OpenAIAPIModel` serves as the OpenAI-compatible gateway within the LLM abstraction layer, providing a standardized interface for interacting with OpenAI, Azure AI Foundry, and other provider-agnostic endpoints (e.g., vLLM, Ollama). It is responsible for translating internal conversation histories into the OpenAI message schema, enforcing the "Sentinel Protocol" by intercepting text-based tool calls to bypass native API tool-calling constraints, and managing real-time telemetry for token usage and context window tracking. This implementation inherits core logic from [base_llm](src/ai/core/llms/base_llm.md) to ensure consistent event triggering and prompt formatting across the JARVIS ecosystem.

## 2. Environment & Configuration
**Environment Lookups:**
- `AI_MODEL_NAME`  Determines the target model or Azure deployment name.
- `AI_API_KEY`  Authentication credential for the provider.
- `AI_API_VERSION`  Specifies the API version for Azure-based requests.
- `AI_AZURE_ENDPOINT`  The base URL for Azure AI services.

**Hardcoded Constants:**
- `gpt-4o` (Default: `model_name`)  Default model fallback.
- `2024-05-01-preview` (Default: `api_version`)  Default Azure API version.
- `2048` (Default: `max_new_tokens`)  Default token limit for generation.
- `0.5` (Default: `temperature`)  Default sampling temperature.
- `0.95` (Default: `top_p`)  Default nucleus sampling parameter.
- `0.0` (Default: `presence_penalty`/`frequency_penalty`)  Default penalty settings.
- `BaseModel.CONTEXT_WINDOW_128K` (Default: `n_ctx`)  Default context window fallback.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `OpenAIAPIModel` | Class | Manages OpenAI-compatible API connections and Sentinel protocol interception. |
| `__init__` | Method | Initializes clients (OpenAI/Azure), sets model parameters, and configures telemetry. |
| `_convert_messages` | Method | Transforms internal message dicts into OpenAI-compliant roles, flattening tool calls/results into text. |
| `chat` | Method | Primary entry point for synchronous or asynchronous chat completions. |
| `_run_streaming_chat` | Method | Generator-based method for handling real-time token streaming and Sentinel tag detection. |
| `_update_token_metrics` | Method | Updates internal `token_info_count` object with usage data from API responses. |
| `clean_cache` | Method | Triggers manual garbage collection to release memory buffers. |

## 4. Execution Logic & Flow
- **Initialization**:
    1. Resolve `model_name`, `api_key`, and `azure_endpoint` via arguments or environment variables.
    2. Instantiate either `OpenAI` or `AzureOpenAI` client.
    3. Detect "reasoning" models (e.g., `o1`) to toggle between `max_tokens` and `max_completion_tokens`.
    4. Initialize telemetry tracking for tokens and context.
- **Data Path (Chat Request)**:
    1. **Input**: `messages` (List[Dict]), `tools` (Optional), `stream` (Bool).
    2. **Processing**: `_convert_messages` flattens tool roles into `user` messages and `assistant` tool calls into `____@tool` text strings.
    3. **Execution**:
        - *Sync Path*: Single request via `client.chat.completions.create`, parses for manual tags via `parse_manual_tags`, returns text or action.
        - *Stream Path*: Iterative chunk processing; checks for `stop_generation_event`.
    4. **Interception**: `handle_sentinel` monitors content for the `@tool` protocol; if detected, it yields a structured dictionary and halts text stream.
    5. **Output**: `str` (text content), `Dict` (tool call), or `Generator` (streamed tokens/actions).
- **Conditional Branching**:
    - **Azure vs. Standard**: Routing logic based on presence of `azure_endpoint`.
    - **Reasoning vs. Standard**: Parameter switching (`max_completion_tokens` vs `max_tokens`).
    - **Stream vs. Sync**: Divergent execution paths in the `chat` method.
    - **Sentinel Detection**: Interruption of standard text flow if a tool call protocol is identified in the stream.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `threading`, `gc`, `json`, `typing`
- **Internal Modules**: 
    - [base_llm](src/ai/core/llms/base_llm.md)
    - [functions](functions.md)
    - [color](color.md)
- **External Packages**: `openai`