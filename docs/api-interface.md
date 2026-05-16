# JARVIS Neural Hub API Documentation

This document provides complete details for consuming the JARVIS Neural Hub REST API. It is designed to be used by frontend developers or AI code-assistants to build client-side services without needing access to the backend source code.

---

## Base URL
By default, the server runs on `http://0.0.0.0:8000`. Adjust the host and port depending on your environment.

All API endpoints are prefixed with `/api/v1/` (except for the `/api/health` endpoint).

## Common Behaviors
- **Content-Type**: Requests with a body must use `application/json`.
- **CORS**: Cross-Origin Resource Sharing is enabled for all origins (`*`) and all methods.
- **Errors**: Failed requests return standard HTTP status codes (e.g., `400 Bad Request`, `404 Not Found`, `500 Internal Server Error`). The error response body typically looks like:
  ```json
  {
    "detail": "Error message description"
  }
  ```

---

## Data Models (Schemas)

### `ChatMessage`
Represents a single message in a chat conversation.
- **`role`** *(string)*: The role of the message sender (e.g., `"user"`, `"assistant"`, `"system"`).
- **`content`** *(string)*: The text content of the message.

### `ChatCompletionRequest`
Payload for sending a chat request to the model.
- **`messages`** *(List[ChatMessage])*: The conversation history including the new prompt.
- **`model`** *(string, optional)*: The ID of the model to use.
- **`system_prompt`** *(string, optional)*: The system prompt/instructions for the model.
- **`stream`** *(boolean, optional, default: false)*: Whether to stream the response back.
- **`temperature`** *(float, optional, default: 0.7)*: Creativity/randomness of the response.
- **`session_folder`** *(string, optional)*: Folder to save the session under.
- **`session_id`** *(string, optional)*: Unique identifier for the session.
- **`session_title`** *(string, optional)*: Title for the session.

### `UpdateSessionRequest`
Payload to update an existing session.
- **`session_title`** *(string)*: The title of the session.
- **`session_content`** *(List[ChatMessage], optional)*: The entire conversation history to overwrite the session with.

### `PromptCreateRequest`
Payload to create a new system prompt.
- **`prompt_path`** *(string)*: The relative path/name for the new prompt file.
- **`content`** *(string)*: The text content of the prompt.

### `PromptUpdateRequest`
Payload to update an existing system prompt.
- **`content`** *(string)*: The new text content of the prompt.

---

## Endpoints

### 1. Health Check

#### `GET /api/health`
Check if the API and active model are online.

**Response (200 OK):**
```json
{
  "status": "online",
  "model": "JARVIS"
}
```

---

### 2. Chat Completions

#### `POST /api/v1/chat/completions` (Alias: `POST /api/v1/chat`)
Send a conversation to the active model and receive a response. 

**Request Body:** `ChatCompletionRequest`
```json
{
  "messages": [
    {"role": "user", "content": "Hello, JARVIS!"}
  ],
  "model": "llama-3",
  "system_prompt": "You are a helpful assistant.",
  "stream": false,
  "temperature": 0.7,
  "session_folder": "default",
  "session_id": "session-123",
  "session_title": "My Chat"
}
```

**Response (200 OK):**
Depends on the `stream` parameter.
- If `stream=false`: Returns a JSON object containing the assistant's reply.
- If `stream=true`: Returns an EventStream (Server-Sent Events) chunking the response text.

---

### 3. Session Management

Sessions represent saved chat histories.

#### `GET /api/v1/sessions`
Retrieve a list of saved sessions.

**Query Parameters:**
- `session_folder` *(string, optional)*: Filter the results by a specific sub-folder.

**Response (200 OK):**
```json
{
  "sessions": [
    "default/session-123.json",
    "coding/session-456.json"
  ]
}
```

#### `GET /api/v1/sessions/{session_path}`
Load the content of a specific session.

**Path Parameters:**
- `session_path` *(string)*: The path/ID to the session file (e.g., `default/session-123.json`).

**Response (200 OK):**
Returns the JSON content of the session.

#### `PUT /api/v1/sessions/{session_path}`
Overwrite the entire content of a specific session.

**Path Parameters:**
- `session_path` *(string)*: The path to the session file.

**Request Body:** `UpdateSessionRequest`
```json
{
  "session_title": "Updated Title",
  "session_content": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there!"}
  ]
}
```

**Response (200 OK):**
```json
{
  "message": "Session content updated successfully"
}
```

#### `PUT /api/v1/sessions/{session_path}/title`
Update *only* the title of a specific session.

**Path Parameters:**
- `session_path` *(string)*: The path to the session file.

**Request Body:** `UpdateSessionRequest`
*(Note: `session_content` is not required for this endpoint)*
```json
{
  "session_title": "My New Chat Title"
}
```

**Response (200 OK):**
Returns a success result object provided by the `SessionManager`.

#### `DELETE /api/v1/sessions/{session_path}`
Delete a specific session file.

**Path Parameters:**
- `session_path` *(string)*: The path to the session file.

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Session {session_path} deleted."
}
```

---

### 4. Prompt Management

Manage reusable system prompts stored in the server.

#### `GET /api/v1/prompts`
Retrieve a list of saved prompts.

**Query Parameters:**
- `prompt_folder` *(string, optional)*: Filter the results by a specific sub-folder.

**Response (200 OK):**
```json
{
  "prompts": [
    "coding-assistant.txt",
    "creative-writer.txt"
  ]
}
```

#### `GET /api/v1/prompts/{prompt_path}`
Get the text content of a specific prompt file.

**Path Parameters:**
- `prompt_path` *(string)*: The path/name of the prompt file.

**Response (200 OK):**
Returns the content object/string from the `PromptManager`.

#### `POST /api/v1/prompts`
Create a new prompt file.

**Request Body:** `PromptCreateRequest`
```json
{
  "prompt_path": "new-prompt.txt",
  "content": "You are a specialized AI assistant that..."
}
```

**Response (200 OK):**
Returns a success result object provided by the `PromptManager`.

#### `PUT /api/v1/prompts/{prompt_path}`
Update or overwrite an existing prompt file.

**Path Parameters:**
- `prompt_path` *(string)*: The path/name of the prompt file to update.

**Request Body:** `PromptUpdateRequest`
```json
{
  "content": "This is the updated prompt content..."
}
```

**Response (200 OK):**
Returns a success result object provided by the `PromptManager`.

#### `DELETE /api/v1/prompts/{prompt_path}`
Delete a specific prompt file.

**Path Parameters:**
- `prompt_path` *(string)*: The path/name of the prompt file to delete.

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Prompt {prompt_path} deleted."
}
```

---

### 5. Model Configuration

#### `GET /api/v1/model-configs`
Retrieve a list of all available JSON brains (model configurations) scanned from the server's `models` directory.

**Response (200 OK):**
Returns a list of model config objects.
```json
[
  {
    "model_name": "Llama 3 8B",
    "model_file": "llama-3-8b.json"
  },
  {
    "model_name": "Mistral 7B",
    "model_file": "mistral-7b.json"
  }
]
```

---

## Error Handling Reference

The API maps underlying backend exceptions to specific HTTP status codes:

| HTTP Status | Condition |
| :--- | :--- |
| **400 Bad Request** | Request was invalid. Sent if `UpdateSessionRequest` is missing the expected `session_content` payload. Also returned on `InvalidPathError` (e.g., attempt to do path traversal `../../`). |
| **404 Not Found** | The requested Session or Prompt file does not exist (`SessionNotFoundError`, `PromptNotFoundError`). |
| **500 Internal Server Error** | Thrown if an unexpected error occurs, if managers fail to load, or on `SessionAccessError`/`PromptAccessError`. |