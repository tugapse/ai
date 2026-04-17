

## 1. Architectural Role  
Provides a framework for tool selection and execution within a system, enabling dynamic interaction with external services and file systems.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `ToolSelector` | Class | Detects and selects tools from user input using an LLM-based system prompt. |  
| `BaseTool` | Class | Abstract base class defining the interface for all tools, including a `run` method and metadata. |  
| `FileLister` | Class | Lists files in a directory, optionally filtered by file extension. |  
| `OpenWeatherAPI` | Class | Fetches weather data via the OpenWeatherMap API for current conditions and forecasts. |  
| `check_tool_request` | Method | Analyzes text to determine if a tool request is present, leveraging an LLM. |  
| `run` | Method | Abstract method for executing tool-specific logic. |  
| `list_files` | Method | Implements directory traversal and file filtering logic. |  
| `get_current_weather` | Method | Retrieves current weather data for a specified city. |  
| `get_forecast` | Method | Generates a 3-hourly weather forecast for a specified city. |  

## 3. Execution Logic & Flow  
- **Initialization**:  
  - `ToolSelector` loads a system prompt from a file during initialization.  
  - `FileLister` and `OpenWeatherAPI` initialize with configuration parameters (e.g., API keys).  
- **Data Path**:  
  - `ToolSelector`: Input text  `check_tool_request` (LLM analysis)  returns tool existence.  
  - `FileLister`: Input directory  `list_files` (filters by extension)  returns filenames.  
  - `OpenWeatherAPI`: Input city  `get_current_weather`/`get_forecast` (HTTP requests)  returns weather data.  
- **Conditional Branching**:  
  - `check_tool_request`: Checks for `"tool":` in text.  
  - `list_files`: Filters files by extension if provided.  
  - `get_forecast`: Samples forecast data every 8 entries (3-hour intervals).  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `json`, `requests`, `json`.  
- **Internal Modules**: `core.llms.ollama_model`, `chat`, `color`, `core.tools`.  
- **External Packages**: `requests` (for HTTP API calls).  

## 5. Configuration & Environment  
- **Hardcoded Constants**:  
  - `SYSTEM_PROMPT_FOLDER` (from config).  
  - File extension filtering logic in `list_files`.  
- **Environment Lookups**:  
  - `OPENWEATHER_API_KEY` (from `os.environ`).