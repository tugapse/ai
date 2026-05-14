## 1. Architectural Role
This file implements an ASGI middleware layer designed to intercept HTTP traffic and enforce correct `Content-Type` headers for static assets. It acts as a preventative layer within the [modules/server/middleware.md](modules/server/middleware.md) stack to ensure that browsers correctly interpret and execute client-side resources (JavaScript, CSS, images) by injecting missing MIME type metadata into the ASGI scope before the request reaches the core application logic.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `'.js', '.css', '.png', '.jpg', '.svg'` (Default: `tuple`)  Target file extensions for MIME sniffing.
- `'application/javascript'` (Default: `str`)  MIME type for `.js` files.
- `'text/css'` (Default: `str`)  MIME type for `.css` files.
- `'image/png'` (Default: `str`)  MIME type for `.png` files.
- `'image/jpeg'` (Default: `str`)  MIME type for `.jpg`/`.jpeg` files.
- `'image/svg+xml'` (Default: `str`)  MIME type for `.svg` files.
- `'application/octet-stream'` (Default: `str`)  Fallback MIME type for unrecognized extensions.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `MIMETypeFixerMiddleware` | Class | Orchestrates the intercepting of ASGI scopes to inject header metadata. |
| `__init__` | Method | Initializes the middleware with the wrapped application instance. |
| `__call__` | Async Method | The primary entry point for ASGI requests; performs routing logic and header injection. |
| `_determine_mime_type` | Method | Maps file path extensions to their corresponding string-based MIME type identifiers. |

## 4. Execution Logic & Flow
- **Initialization**: The class accepts an `app` instance (the next layer in the ASGI stack) and logs initialization via [functions.md](functions.md).
- **Data Path**: 
    1. **Intercept**: `__call__` receives `scope`, `receive`, and `send`.
    2. **Filter**: Checks if `scope['type']` is `http` and if the `path` ends with a recognized static asset extension.
    3. **Analyze**: If matched, calls `_determine_mime_type` to resolve the correct string identifier.
    4. **Inject**: Checks the `scope['headers']` list for existing `b'content-type'`. If absent, appends the new header.
    5. **Delegate**: Passes the modified (or original) `scope` to `self.app`.
- **Conditional Branching**:
    - **Type Check**: If `scope['type'] != 'http'` or path does not match extension whitelist $\rightarrow$ Pass through immediately.
    - **Header Check**: If `b'content-type'` is already present in `headers` $\rightarrow$ Log skip and pass through to avoid duplicate headers.
    - **Extension Match**: If path matches an extension in `_determine_mime_type` $\rightarrow$ Return specific MIME; else $\rightarrow$ Return `application/octet-stream`.

## 5. Resource Dependencies
- **Standard Libraries**: `typing`
- **Internal Modules**: 
    - [functions.md](functions.md)
- **External Packages**: None identified.