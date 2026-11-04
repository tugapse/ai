## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **MIMETypeFixerMiddleware** | [src/ai/modules/server/middleware.py](/src/ai/modules/server/middleware.py) |

The `MIMETypeFixerMiddleware` is an ASGI middleware component designed to intercept HTTP requests for static assets and ensure they are served with the correct `Content-Type` header. This component addresses the issue of browsers failing to render assets (like CSS, JavaScript, or images) correctly when the server fails to provide the appropriate MIME type based on file extensions.

Within the broader application architecture, this middleware sits within the server module layer, acting as a pre-processing step in the request/response lifecycle. It ensures that the ASGI `scope` is correctly decorated with the necessary headers before the request is passed to the core application or subsequent middleware in the stack.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `MIMETypeFixerMiddleware(app)` | Class | An ASGI middleware that wraps an application to inject correct MIME types for specific file extensions. |
| `__call__(scope, receive, send)` | Async Method | The entry point for the middleware; inspects the `scope` for static asset paths and modifies headers if necessary. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The middleware inspects the `scope['type']` to ensure it is an `http` request. It then checks the `scope['path']` against a hardcoded list of extensions (`.js`, `.css`, `.png`, `.jpg`, `.svg`). If a match is found, it calls the internal `_determine_mime_type` method to map the extension to a standard MIME string. It then checks the existing `scope['headers']` to prevent duplicate `Content-Type` entries before appending the new header.
- **Side Effects:** This component mutates the ASGI `scope` dictionary by appending or modifying headers. It also performs logging via the `ai.functions` utility.
- **Error Handling:** If a file extension is recognized by the path check but not explicitly mapped in the internal logic, it falls back to `application/octet-stream`. If the request is not an HTTP request or does not match the target extensions, the middleware passes the request through to the next layer unchanged.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `typing` (List, Tuple).
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)