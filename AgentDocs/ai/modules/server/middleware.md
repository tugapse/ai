## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **MIMETypeFixerMiddleware** | [src/ai/modules/server/middleware.py](/AgentDocs/ai/modules/server/middleware.md) |

The `MIMETypeFixerMiddleware` is an ASGI middleware component designed to intercept HTTP requests for static assets and ensure that the appropriate `Content-Type` header is present in the response scope. This solves the common issue where web servers or application frameworks fail to correctly identify file types for assets like JavaScript, CSS, or images, which can lead to broken rendering or security blocks in modern web browsers.

In the broader application architecture, this component sits within the server layer, acting as a decorator for the ASGI application stack. It operates by inspecting the request path for specific file extensions and injecting the correct MIME type into the headers if one has not already been explicitly set by a subsequent layer in the stack.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `MIMETypeFixerMiddleware(app)` | Class | An ASGI middleware that wraps an application to manage static asset MIME types. |
| `__call__(scope, receive, send)` | Async Method | The primary entry point that processes the ASGI scope, checks for static file extensions, and injects `Content-Type` headers. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The middleware inspects the `scope['path']` for specific extensions (`.js`, `.css`, `.png`, `.jpg`, `.svg`). If a match is found, it uses an internal mapping via `_determine_mime_type` to find the corresponding MIME string. It then checks the existing `scope['headers']` to ensure no `content-type` header is already present before appending the new header.
- **Side Effects:** This component mutates the ASGI `scope` dictionary by appending or modifying headers. It also performs logging via the internal `func.debug` utility.
- **Error Handling:** If a file extension is recognized as a static asset but does not match the specific hardcoded mapping, the middleware falls back to `application/octet-stream`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `typing` (List, Tuple).
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)