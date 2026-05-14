## 1. Architectural Role

**Functional Mission**
The **MIMETypeFixerMiddleware** is a specialized ASGI middleware component designed to ensure correct HTTP response headers for static assets. Its primary mission is to intercept incoming HTTP requests for specific file extensions (such as `.js`, `.css`, and images) and inject the appropriate `Content-Type` header into the ASGI scope if it is missing, preventing browser rendering issues caused by incorrect or absent MIME types.

**System Context & Integration**
This component sits within the server's request-response pipeline, acting as a decorator for the core application. It intercepts the `scope` before it reaches the primary application logic, specifically targeting static resource paths. By modifying the `scope['headers']` list, it ensures that downstream handlers or static file servers receive a request context that already contains the necessary metadata for correct content delivery. It relies on [functions](/docs/functions.md) for telemetry and debugging during the interception process.

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
- `'.js', '.css', '.png', '.jpg', '.svg'` (Default: tuple of extensions)  Target file extensions for MIME type enforcement.
- `'application/javascript'` (Default: string)  MIME type for `.js` files.
- `'text/css'` (Default: string)  MIME type for `.css` files.
- `'image/png'` (Default: string)  MIME type for `.png` files.
- `'image/jpeg'` (Default: string)  MIME type for `.jpg`/`.jpeg` files.
- `'image/svg+xml'` (Default: string)  MIME type for `.svg` files.
- `'application/octet-stream'` (Default: string)  Fallback MIME type for unrecognized extensions.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `MIMETypeFixerMiddleware` | Class | ASGI middleware wrapper that manages MIME type injection. |
| `__init__` | Method | Initializes the middleware with the target ASGI `app`. |
| `__call__` | Async Method | The primary entry point for ASGI lifecycle; intercepts `scope`, `receive`, and `send`. |
| `_determine_mime_type` | Method | Internal logic to map file extensions to valid MIME type strings. |

## 4. Execution Logic & Flow
- **Initialization**: The class is instantiated with an `app` instance, which is stored as `self.app` to facilitate the delegation of the request. A debug log is emitted via `func.debug`.
- **Data Path**: 
    1. **Input**: Receives ASGI `scope`, `receive`, and `send` parameters.
    2. **Filtering**: Checks if `scope['type']` is `'http'` and if `scope['path']` ends with a recognized static extension.
    3. **Processing**: If a match is found, `_determine_mime_type` is called to resolve the string.
    4. **Header Injection**: The middleware inspects `scope['headers']`. If `b'content-type'` is absent, it appends the new header.
    5. **Output**: The modified (or original) `scope` is passed to `await self.app(scope, receive, send)`.
- **Conditional Branching**:
    - **Path Match**: If the path does not match the static extension list, the middleware immediately delegates to `self.app` without modification.
    - **Header Existence**: If `content-type` is already present in the headers, the middleware skips injection to prevent duplicate headers and proceeds to the app.
    - **MIME Resolution**: If an extension is recognized, the specific type is returned; otherwise, it falls back to `application/octet-stream`.

## 5. Resource Dependencies
- **Standard Libraries**: `typing.List`, `typing.Tuple`
- **Internal Modules**: 
    - [functions](/docs/functions.md)
- **External Packages**: None identified.