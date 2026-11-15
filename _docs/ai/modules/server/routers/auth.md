## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| auth | /ai/modules/server/routers/auth.md |

This component handles all API endpoints related to device authentication, pairing, and device management. Its primary responsibility is to provide secure endpoints for clients to initiate pairing, complete the handshake using a shared code, and manage their authenticated device session via cookies or tokens.

Architecturally, this router acts as a controller layer within the server application. It relies heavily on the `AuthService` dependency to execute the business logic for authentication flows, while `require_device` acts as a middleware gatekeeper, ensuring that only currently paired and authenticated devices can access protected resources like `/me` or `/devices`.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| PairStart | Class | Pydantic model defining the initial input for starting a device pairing process. |
| PairFinish | Class | Pydantic model defining the necessary inputs (ID and code) to finalize a pairing session. |
| require_device | Function | FastAPI dependency that authenticates the requesting device using cookies, headers, and IP, returning the authenticated device dictionary. |
| pair_start | Function | Endpoint handler that initiates the device pairing process by calling `AuthService.start_pairing`. |
| pair_finish | Function | Endpoint handler that completes the pairing process, setting the session cookie upon success. |
| me | Function | Endpoint handler that returns the public details of the currently authenticated device. |
| logout | Function | Endpoint handler that revokes the current device session and clears the session cookie. |
| devices | Function | Endpoint handler that lists all devices associated with the currently authenticated device ID. |
| revoke | Function | Endpoint handler that explicitly revokes a specified device ID, authenticated by the requesting device. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The routing functions primarily delegate to the injected `AuthService`. The `require_device` dependency encapsulates the core authentication flow: extracting credentials from the request, calling `AuthService.authenticate`, and attaching the resulting device object to the request state for downstream use. Pairing flows involve state transitions managed by `start_pairing` and `finish_pairing`.
- **Side Effects:** The code interacts with the network (via HTTP requests/responses) and mutates external state by setting or deleting HTTP cookies (`response.set_cookie`, `response.delete_cookie`).
- **Error Handling:** It utilizes `try...except AuthError` blocks extensively. Any `AuthError` raised by the `AuthService` is caught and immediately re-raised as an `HTTPException` with the appropriate status code and detail, ensuring standardized API error responses.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `fastapi`, `pydantic`, `typing`
- **Internal:** [ai.modules.server.services.auth.AuthService](/ai/modules/server/services/auth.md)