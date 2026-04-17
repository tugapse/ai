## 1. Architectural Role
Provides a framework for tool definition and selection, enabling the system to identify and execute specific functional capabilities (file listing, weather retrieval) based on LLM-generated requests.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ToolSelector` | Class | Inherits `OllamaModel`; determines if a user request requires a tool and parses the tool identifier. |
| `BaseTool` | Class | Abstract base class defining the schema (`tool`, `name`, `description`, `examples`) and the `run` interface. |
| `FileLister` | Class | Implementation of `BaseTool` for retrieving files from a local directory. |
| `OpenWeatherAPI` | Class | Implementation of `BaseTool` for fetching current weather and forecasts via OpenWeatherMap API. |

## 3. Execution Logic & Flow
- **Initialization**:
    - `ToolSelector`: Loads a system prompt from a file path constructed using `config['SYSTEM_PROMPT_FOLDER']` and `./prompt_templates/tool_selector.md`.
    - `BaseTool` subclasses: Initialize identity metadata (ID, Name, Description, Example JSON) and specific API keys (for `OpenWeatherAPI`).
- **Data Path**:
    - **Tool Selection**: `check_tool_request(text)` $\rightarrow$ String check for `'tool':` $\rightarrow$ `check_system_prompt` $\rightarrow$ `ollama.chat` $\rightarrow$ `json.loads` $\rightarrow$ Boolean result.
    - **Tool Execution**: `run(data)` $\rightarrow$ Specific implementation (e.g., `list_files` or `get_current_weather`) $\rightarrow$ Return data/list.
- **Conditional Branching**:
    - `ToolSelector.check_tool_request`: Branches based on whether the input string contains tool-specific JSON keys.
    - `FileLister.list_files`: Branches based on whether a file extension filter is provided and if the file matches that extension.
    - `OpenWeatherAPI.get_forecast`: Iterates through the API response list, selecting data points every 8th index (24-hour intervals).

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `json`, `requests`
- **Internal Modules**: `ollama`, `chat.ChatRoles`, `core.llms.ollama_model.OllamaModel`, `color.Color`, `color.pformat_text`
- **External Packages**: `requests`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - Prompt path: `./prompt_templates/tool_selector.md`
    - Weather API URL: `http://api.openweathermap.org/data/2.5/`
- **Environment Lookups**: 
    - `config['SYSTEM_PROMPT_FOLDER']`: Directory for prompt templates.
    - `os.environ.get("OPENWEATHER_API_KEY")`: API key for weather services.