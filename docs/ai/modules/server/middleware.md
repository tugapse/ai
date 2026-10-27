## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | MIMETypeFixerMiddleware |
| Source file | middleware.py |

The **MIMETypeFixerMiddleware** serves as a specialized ASGI middleware component designed to intercept HTTP requests and ensure that static assets are served with the correct `Content-Type` headers. This prevents browser rendering issues that occur when web assets like JavaScript, CSS, or images are served with incorrect or missing MIME types.

**Functional Mission**
The primary responsibility of **MIMETypeFixerMiddleware** is to automate the injection of appropriate MIME types into the ASGI scope for specific file extensions. It solves the problem of inconsistent header delivery in the server layer by inspecting the request path and appending the necessary `Content-Type` header if it is not already present.

**System Context & Integration**
This component sits within the server middleware stack, acting as a gatekeeper for incoming HTTP traffic. It intercepts the `scope` before it reaches the core application logic. By modifying the `scope['headers']` list, it ensures that downstream handlers or static file servers receive a request context that is already enriched with the correct metadata. It relies on [ai.functions](/docs/ai/functions.md) for debug logging during the interception process.

- **INTERNAL REFERENCES**: [ai.functions](/docs/ai/functions.md)

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `'.js'` (Default: `application/javascript`)  MIME type for JavaScript files.
- `'.css'` (Default: `text/css`)  MIME type for Cascading Style Sheets.
- `'.png'` (Default: `image/png`)  MIME type for PNG images.
- `'.jpg'` / `'.jpeg'` (Default: `image/jpeg`)  MIME type for JPEG images.
- `'.svg'` (Default: `image/svg+xml`)  MIME type for SVG images.
- `'application/octet-stream'` (Default: `application/octet-stream`)  Fallback MIME type for unrecognized extensions.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `MIMETypeFixerMiddleware` | Class | ASGI middleware wrapper that manages the lifecycle of request interception. |
| `__init__` | Method | Initializes the middleware with the underlying ASGI `app`. |
| `__call__` | Async Method | The primary entry point for ASGI; intercepts `scope`, `receive`, and `send` to apply header logic. |
| `_determine_mime_type` | Method | Internal helper that maps file extensions to their corresponding MIME type strings. |

## 4. Execution Logic & Flow
- **Initialization**: The middleware is instantiated with the `app` instance, and a debug message is logged via `func.debug`.
- **Data Path**: 
    1. **Input**: ASGI `scope`, `receive`, and `send` objects.
    2. **Processing**: 
        - Check if `scope['type']` is `'http'`.
        - Check if `scope['path']` ends with a registered static extension.
        - If matched, invoke `_determine_mime_type`.
        - Inspect `scope['headers']` for an existing `b'content-type'`.
        - If missing, append `(b'Content-Type', mime_type)` to the headers list.
    3. **Output**: The modified `scope` is passed to `await self.app(scope, receive, send)`.
- **Conditional Branching**:
    - **Path Match**: If the path does not match the target extensions (js, css, png, jpg, svg), the middleware immediately passes the request to the next layer without modification.
    - **Header Presence**: If `content-type` is already present in the headers, the middleware skips the injection to prevent duplicate or conflicting headers.
    - **Extension Fallback**: If a path matches the initial filter but fails the specific extension mapping in `_determine_mime_type`, it defaults to `application/octet-stream`.

## 5. Resource Dependencies
- **Standard Libraries**: `typing.List`, `typing.Tuple`
- **Internal Modules**: 
    - [ai.functions](/docs/ai/functions.md)
- **External Packages**: None identified.