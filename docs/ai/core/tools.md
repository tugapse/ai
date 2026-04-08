## 1. Architectural Role
`tools.py` is responsible for defining and managing various tools that can be used within the system, including selecting tools based on user requests and implementing specific tool functionalities.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ToolSelector` | Class | Selects the appropriate tool based on the user's request. |
| `BaseTool` | Class | Base class for all tools, providing a structure for tool implementation. |
| `FileLister` | Class | Tool for listing files in a directory. |
| `OpenWeatherAPI` | Class | Tool for interacting with the OpenWeatherMap API. |

## 3. Execution Logic & Flow
- **Initialization**:
  - `ToolSelector`: Initializes with a model, configuration, and optional system prompt. Reads the system prompt from a file.
  - `BaseTool`: Initializes with a tool identifier, name, description, and optional examples.
  - `FileLister`: Inherits from `BaseTool` and initializes with default values.
  - `OpenWeatherAPI`: Inherits from `BaseTool` and initializes with an optional API key, defaulting to an environment variable if not provided.

- **Data Path**:
  - `ToolSelector`: Checks if the input text contains a tool request, processes it, and returns the result.
  - `BaseTool`: Provides a template for tool implementation with a `run` method that must be overridden.
  - `FileLister`: Lists files in a specified directory, optionally filtering by extension.
  - `OpenWeatherAPI`: Fetches current weather and forecast data for a specified city using the OpenWeatherMap API.

- **Conditional Branching**:
  - `ToolSelector`: Checks if the input text contains a tool request using the `check_tool_request` method.
  - `FileLister`: Filters files based on the provided extension.
  - `OpenWeatherAPI`: Fetches weather data based on the provided city and optionally returns a forecast.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `json`, `requests`
- **Internal Modules**: `ollama`, `chat`, `core.llms.ollama_model`, `color`
- **External Packages**: `requests`

## 5. Configuration & Environment
- **Hardcoded Constants**: `system_prompt_folder` (path to prompt templates)
- **Environment Lookups**: `OPENWEATHER_API_KEY` (environment variable for OpenWeatherMap API key)