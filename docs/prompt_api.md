# Prompt Management API

This document outlines the API endpoints for managing prompts within the JARVIS Neural Hub. These endpoints allow for listing, retrieving, creating, updating, and deleting prompts.

The base URL for all endpoints is `/api/v1`.

---

## 1. List Prompts

Retrieves a list of saved prompts, optionally filtering by a sub-folder.

- **Method:** `GET`
- **Path:** `/api/v1/prompts`
- **Query Parameters:**
  - `prompt_folder` (optional, string): The sub-folder to search within. If not provided, it lists from the root prompt directory.

**Example Request (cURL):**

```bash
# List all prompts
curl http://{server}:{port}/api/v1/prompts

# List prompts in a specific folder
curl http://{server}:{port}/api/v1/prompts?prompt_folder=agents
```

**Example Success Response (200 OK):**

```json
{
  "prompts": {
    "files": ["system/default.md", "system/task.md"],
    "folders": ["agents", "user"]
  }
}
```

---

## 2. Get Prompt Content

Retrieves the content of a specific prompt file.

- **Method:** `GET`
- **Path:** `/api/v1/prompts/{prompt_path}`
- **Path Parameters:**
  - `prompt_path` (required, string): The full path to the prompt file (e.g., `system/default.md`).

**Example Request (cURL):**

```bash
curl http://{server}:{port}/api/v1/prompts/system/default.md
```

**Example Success Response (200 OK):**

```json
{
  "path": "system/default.md",
  "content": "You are a helpful assistant."
}
```

---

## 3. Create a New Prompt

Creates a new prompt file with the specified content.

- **Method:** `POST`
- **Path:** `/api/v1/prompts`
- **Request Body:**

```json
{
  "prompt_path": "user/new-prompt.md",
  "content": "This is the content of my new prompt."
}
```

**Example Request (cURL):**

```bash
curl -X POST http://{server}:{port}/api/v1/prompts \
-H "Content-Type: application/json" \
-d '{
  "prompt_path": "user/new-prompt.md",
  "content": "This is the content of my new prompt."
}'
```

**Example Success Response (200 OK):**

```json
{
  "status": "success",
  "message": "Prompt 'user/new-prompt.md' created successfully.",
  "path": "user/new-prompt.md"
}
```

---

## 4. Update a Prompt

Updates (overwrites) the content of an existing prompt file.

- **Method:** `PUT`
- **Path:** `/api/v1/prompts/{prompt_path}`
- **Path Parameters:**
  - `prompt_path` (required, string): The full path to the prompt file to update.
- **Request Body:**

```json
{
  "content": "This is the updated content."
}
```

**Example Request (cURL):**

```bash
curl -X PUT http://{server}:{port}/api/v1/prompts/user/new-prompt.md \
-H "Content-Type: application/json" \
-d '{
  "content": "This is the updated content."
}'
```

**Example Success Response (200 OK):**

```json
{
  "status": "success",
  "message": "Prompt 'user/new-prompt.md' updated successfully.",
  "path": "user/new-prompt.md"
}
```

---

## 5. Delete a Prompt

Deletes a specific prompt file.

- **Method:** `DELETE`
- **Path:** `/api/v1/prompts/{prompt_path}`
- **Path Parameters:**
  - `prompt_path` (required, string): The full path to the prompt file to delete.

**Example Request (cURL):**

```bash
curl -X DELETE http://{server}:{port}/api/v1/prompts/user/new-prompt.md
```

**Example Success Response (200 OK):**

```json
{
  "status": "success",
  "message": "Prompt user/new-prompt.md deleted."
}
```