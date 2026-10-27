## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | OpenAIAPIModel |
| Source file | open_ai.py |

The **OpenAIAPIModel** serves as a high-level, provider-agnostic abstraction layer designed to interface with any LLM provider that adheres to the OpenAI API specification. It acts as a bridge between the JARVIS core logic and various external inference engines, including OpenAI, Azure AI Foundry, Mistral, Ollama, and vLLM.

**Functional Mission**
The primary mission of **OpenAIAPIModel** is to enforce the "Sentinel Protocol" by intercepting raw text streams and converting them into structured tool calls or system actions. It solves the problem of provider-specific tool-calling implementations by flattening tool calls and results into a standardized text-based protocol (` (`____@tool`), ensuring that the reasoning engine remains decoupled from the underlying API's native function-calling mechanics.

**System Context & Integration**
This component is a specialized implementation of [BaseModel](/docs/ai/core/llms/base_llm.md). It integrates deeply with the [ToolRegistry](/docs/ai/tools/tool_registry.md) to parse manual tags from text streams. During execution, it communicates telemetry data (token usage) back to the system and triggers events such as `STREAMING_FINISHED_EVENT` or `tool_detected` to coordinate with the [ModelOrchestrator](/docs/ai/services/model_orchestrator.md) and other downstream consumers.

- **INTERNAL REFERENCES**: [BaseModel](/docs/ai/core/llms/base_llm.md), [ToolRegistry](/docs/ai/tools/tool_registry.md), [Color](/docs/ai/color.md).

## 2. Environment & Configuration
**Environment Lookups:**
- `AI_MODEL_NAME` (via `__init__`)  Defines the target model or Azure deployment name.
- `AI_API_KEY` (via `__init__`)  The authentication credential for the provider.
- `AI_API_VERSION` (via `__init__`)  The specific Azure API version to utilize.
- `AI_AZURE_ENDPOINT` (via `__init__`)  The base URL for Azure-hosted OpenAI services.

**Hardcoded Constants:**
- `gpt-4o` (Default: `model_name`)  Fallback model name if no environment variable is set.
- `2024-05-01-preview` (Default: `api_version`)  Fallback Azure API version.
- `2048` (Default: `max_new_tokens`)  Default token limit for generation.
- `0.5` (Default: `temperature`)  Default sampling temperature for non-reasoning models.
- `0.95` (Default: `top_p`)  Default nucleus sampling parameter.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `OpenAIAPIModel` | Class | Main interface for OpenAI-compatible LLM interaction. |
| `_load_llm_params` | Method | Initializes telemetry counters and context window limits. |
| `_convert_messages` | Method | Transforms internal message history into the Sentinel-compliant text protocol. |
| `chat` | Method | Entry point for synchronous or streaming chat completions. |
| `_run_streaming_chat` | Method | Manages the generator loop for real-time token streaming and Sentinel interception. |
| `_update_token_metrics` | Method | Synchronizes API usage data with internal telemetry objects. |
| `clean_cache` | Method | Triggers manual garbage collection to manage memory. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Resolves model name, API key, and endpoint from arguments or environment.
    2. Instantiates either `OpenAI` or `AzureOpenAI` client based on the presence of `azure_endpoint`.
    3. Detects "reasoning" models (e.g., `o1`) to switch from `max_tokens` to `max_completion_tokens`.
    4. Configures sampling parameters (`temperature`, `top_p`, etc.) for standard models.
- **Data Path**: 
    1. **Input**: A list of message dictionaries and optional tool definitions.
    2. **Processing**: `_convert_messages` flattens tool calls into `____@tool` strings and tool results into `[SYSTEM RESULT...]` blocks.
    3. **API Call**: Sends the formatted payload to the provider via `client.chat.completions.create`.
    4. **Interception**: In streaming mode, `handle_sentinel` monitors the buffer for the `@tool` pattern.
    5. **Output**: Returns either a raw string (text), a dictionary (detected tool call), or a Generator (streaming tokens).
- **Conditional Branching**:
    - **Azure vs. Standard**: Routes client instantiation based on `azure_endpoint`.
    - **Reasoning vs. Standard**: Adjusts parameter keys (`max_completion_tokens` vs `max_tokens`).
    - **Stream vs. Sync**: Diverts `chat()` execution to either `_run_streaming_chat` or a direct blocking call.
    - **Sentinel Detection**: If a tool pattern is detected in the stream, the generator yields the tool object and terminates early.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `threading`, `gc`, `json`, `typing`
- **Internal Modules**: 
    - [ai.functions](/docs/ai/functions.md)
    - [ToolRegistry](/docs/ai/tools/tool_registry.md)
    - [BaseModel](/docs/ai/core/llms/base_llm.md)
    - [Color](/docs/ai/color.md)
- **External Packages**: `openai`