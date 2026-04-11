

## 1. Architectural Role  
Provides a unified interface for interacting with Google's Gemini AI models via Vertex AI or GenAI SDK, abstracting authentication, configuration, and response generation.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `GeminiAPIModel` | Class | Encapsulates Gemini LLM interactions, supporting both Vertex AI and GenAI SDK backends. |  
| `__init__` | Method | Initializes model, authenticates via GCP/GenAI API key, and configures generation parameters. |  
| `chat` | Method | Orchestrates asynchronous or synchronous generation of responses, handling message conversion, image loading, and streaming. |  
| `_convert_messages_to_api` | Method | Transforms input messages into API-compatible format for Vertex AI or GenAI SDK. |  
| `load_images` | Method | Processes image inputs into byte arrays for API request, supporting both backends. |  
| `_append_images_to_history` | Method | Attaches image parts to user messages in the conversation history. |  
| `_generate_response_sync` | Method | Executes synchronous generation using Vertex AI or GenAI SDK. |  
| `_stream_generator` | Method | Manages streaming response generation, chunking output and tracking usage metadata. |  
| `_log_usage_metadata` | Method | Logs token consumption metrics from API responses. |  
| `_check_gcp_auth` | Method | Validates Google Cloud credentials via environment variables or ADC. |  

## 3. Execution Logic & Flow  
- **Initialization**: Loads `GeminiAPIModel`, checks for GCP/GenAI authentication, initializes backend-specific modules (Vertex AI or GenAI SDK), and maps model parameters to API-specific config.  
- **Data Path**: Input messages  `_convert_messages_to_api` (formatting)  `chat` (orchestrates generation)  `_generate_response_sync`/_stream_generator (executes generation)  output text with token usage logging.  
- **Conditional Branching**:  
  - `use_vertex` flag determines Vertex AI vs GenAI SDK initialization.  
  - `stream` flag selects synchronous vs streaming response generation.  
  - Dynamic system prompts are injected during initialization.  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `threading`, `io`, `gc`, `time`, `re`, `subprocess`, `warnings`.  
- **Internal Modules**: `base_llm`, `functions`, `color`.  
- **External Packages**: `google-cloud-aiplatform`, `google-genai`.  

## 5. Configuration & Environment  
- **Hardcoded Constants**:  
  - Default project ID: `"project-02da1a39-478c-49eb-a3e"`.  
  - Default location: `"us-central1"`.  
- **Environment Lookups**:  
  - `GOOGLE_CLOUD_PROJECT` for Vertex AI project ID.  
  - `GEMINI_API_KEY`/`GOOGLE_JARVIS_API_KEY` for GenAI API key.  
  - `GOOGLE_APPLICATION_CREDENTIALS` for GCP ADC authentication.