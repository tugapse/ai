## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **auth** | [auth](/ai/modules/server/services/auth.md) |

This component is responsible for managing device pairing, authenticating requests to protected server routes, and enforcing security policies like network trust and rate limiting. Its primary responsibility is to ensure that only verified, trusted devices can interact with sensitive server functionality, managing the lifecycle from initial pairing to session validation.

This service functions as a core security layer within the server architecture. It utilizes the [DirectoryManager](/ai/services/directory_manager.md) for directory access and interacts with [TotpGuard](/ai/modules/server/services/totp.md) for time-based authentication checks. It manages state persistence via the [DeviceStore](/ai/modules/server/services/auth.md) for paired devices and logs all security events to an audit file.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `AuthError` | Class | Custom exception raised when an authentication or authorization attempt fails, carrying an HTTP status code. |
| `_hash` | Function | Calculates the SHA-256 hash of a given token string. |
| `DeviceStore` | Class | Manages the loading, saving, and retrieval of paired device data from a JSON file, ensuring thread safety. |
| `AuthService` | Class | The main service orchestrator for handling pairing, network checks, rate limiting, and request authentication. |
| `AuthService.check_network` | Method | Validates if the provided IP address belongs to one of the configured trusted network ranges. |
| `AuthService.check_rate` | Method | Checks the request history for a given IP to enforce rate limiting against repeated failures. |
| `AuthService.fail` | Method | Logs a failure event and raises a standardized `AuthError` for rate or authentication issues. |
| `AuthService.start_pairing` | Method | Initiates the pairing process, generating a unique ID and a 6-digit code visible only on the server terminal. |
| `AuthService.finish_pairing` | Method | Finalizes the pairing by validating the code and issuing a unique, secure session token for the device. |
| `AuthService.authenticate` | Method | The primary entry point for protected routes; validates the token from headers or cookies, checks network trust, and verifies the `X-Jarvis-Client` header for state-changing requests. |
| `AuthService.list_devices` | Method | Retrieves a list of all currently paired devices, optionally highlighting the current active device. |
| `AuthService.revoke` | Method | Removes a specific device from the store, optionally logging the revocation actor and source IP. |
| `AuthService.audit` | Method | Writes a timestamped, structured log entry for any security event to the designated audit file. |

## 3. Implementation Details & Side Effects
- **Core Logic:** Authentication relies on a multi-stage process: network validation (checking against CIDR blocks), rate limiting (tracking failures per IP within a sliding window), token validation (using HMAC comparison against stored hashes), and cookie/header verification to prevent CSRF-like attacks on stateful endpoints. Device tokens are time-bound, and session renewal is throttled.
- **Side Effects:** Reads and writes to the filesystem (for device storage and audit logs), prints messages to standard output via `func.out` during pairing requests, and modifies internal state dictionaries (`self.pairings`, `self._failures`).
- **Error Handling:** Explicitly raises `AuthError` for all failure modes (e.g., 401 Unauthorized, 403 Forbidden, 429 Too Many Requests, 404 Not Found). Internal file I/O errors are caught and reported via `func.error`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `ProgramSetting.SERVER_TRUSTED_NETWORKS` — Defines the list of IP address ranges allowed to access protected routes. Defaults to a set of local and private LAN ranges.

**Module Dependencies:**
- **Standard/External:** `hashlib`, `hmac`, `ipaddress`, `json`, `os`, `secrets`, `threading`, `time`, `uuid`, `collections`
- **Internal:** [ai.functions](/ai/functions.md), [ai.config](/ai/config.md), [ai.services.directory_manager](/ai/services/directory_manager.md), [ai.modules.server.services.totp.TotpGuard](/ai/modules/server/services/totp.md)