## 1. Architectural Role
Acts as an ASGI middleware component that intercepts HTTP requests to inject appropriate `Content-Type` headers for specific static file extensions.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `MIMETypeFixerMiddleware` | Class | Orchestrates the interception of ASGI scopes to manage MIME type assignment. |
| `__init__` | Method | Initializes the middleware with the wrapped application instance and logs status. |
| `__call__` | Method | The asynchronous entry point for ASGI connection handling and header injection logic. |
| `_determine_mime_type` | Method | Maps file path extensions to their corresponding string-based MIME type identifiers. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Receives `app` instance.
    2. Stores `app` in `self.app`.
    3. Executes `func.debug` to log initialization.
- **Data Path**: 
    1. **Input**: ASGI `scope` (containing `type`, `path`, and `headers`), `receive`, and `send`.
    2. **Processing**: 
        - Validate `scope['type'] == 'http'`.
        - Validate `scope['path']` ends with specific extensions (`.js`, `.css`, `.png`, `.jpg`, `.svg`).
        - Call `_determine_mime_type` based on `scope['path']`.
        - Check `scope['headers']` for existing `b'content-type'`.
        - If missing, append `(b'Content-Type', mime_type.encode('utf-8'))` to `scope['headers']`.
    3. **Output**: Modified `scope` passed to `self.app(scope, receive, send)`.
- **Conditional Branching**:
    - **Path/Type Filter**: If the request is not HTTP or does not match the extension whitelist, bypasses all logic and calls `self.app` immediately.
    - **Header Existence Check**: If `b'content-type'` is already present in `scope['headers']`, the middleware skips header injection to prevent duplicates.
    - **MIME Mapping**: Uses extension-based branching; defaults to `application/octet-stream` if the extension is unrecognized.

## 4. Resource Dependencies
- **Standard Libraries**: `typing.List`, `typing.Tuple`
- **Internal Modules**: `functions` (aliased as `func`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - Extension Whitelist: `('.js', '.css', '.png', '.jpg', '.svg')`
    - MIME Mappings: 
        - `.js` $\rightarrow$ `application/javascript`
        - `.css` $\rightarrow$ `text/css`
        - `.png` $\rightarrow$ `image/png`
        - `.jpg`/`.jpeg` $\rightarrow$ `image/jpeg`
        - `.svg` $\rightarrow$ `image/svg+xml`
    - Fallback MIME: `application/octet-stream`
- **Environment Lookups**: None