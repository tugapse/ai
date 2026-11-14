## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| MIMETypeFixerMiddleware | /ai/modules/server/middleware.md |

This middleware component is responsible for inspecting incoming HTTP requests to determine if they are requesting a static asset (like `.js`, `.css`, `.png`, etc.). Its primary function is to ensure that the HTTP response headers contain the correct `Content-Type` MIME type for these assets, which is essential for web browsers to render the content correctly.

It operates as an interceptor within the ASGI application stack, sitting between the raw network request and the main application logic. By injecting or verifying the `Content-Type` header, it ensures that static file delivery adheres to web standards before passing control downstream to the next layer in the request processing pipeline.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| MIMETypeFixerMiddleware | Class | Middleware wrapper that processes HTTP scopes to correct MIME types for static assets. |
| __call__ | Method | The ASGI callable entry point. Executes the middleware logic by checking the scope and applying header modifications if necessary before calling the next application layer. |
| _determine_mime_type | Method | Private helper method that maps file extensions found in the path to their corresponding standard MIME type string. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The middleware checks the request scope for HTTP type and a matching static file extension. If a match occurs and the `Content-Type` header is missing, it calls `_determine_mime_type` to get the correct type and then mutates the `scope['headers']` list to include the necessary header before passing the scope to `self.app`.
- **Side Effects:** Mutates the `scope` dictionary passed through the ASGI call chain, specifically by appending to `scope['headers']`.
- **Error Handling:** If the file extension does not match any known types, `_determine_mime_type` defaults to returning `'application/octet-stream'`. The middleware also checks if the header already exists to prevent duplication.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `typing`
- **Internal:** [ai.functions](/ai/functions.md)