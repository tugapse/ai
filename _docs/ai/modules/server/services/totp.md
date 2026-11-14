## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| TotpGuard | ai/modules/server/services/totp |

This component implements the logic for Time-based One-Time Password (TOTP) generation and verification, adhering to RFC 6238 standards. Its primary responsibility is to provide a cryptographically secure mechanism to validate time-sensitive access codes, typically used for approving high-privilege agent actions.

This service acts as a security utility layer within the application architecture. It manages the storage and retrieval of the shared secret key via file I/O, allowing it to interface with the application's persistence layer while ensuring that only authorized server processes can access the secret, as defined in [ai/modules/server/services/totp.py].

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `generate_secret()` | Function | Generates a cryptographically secure, random 160-bit secret encoded in Base32 format suitable for authenticator applications. |
| `code_at(secret, counter)` | Function | Calculates the TOTP code for a given secret and time counter. |
| `provisioning_uri(secret, account, issuer)` | Function | Generates the standard `otpauth://` URI string required for an authenticator app to import the secret. |
| `TotpGuard` | Class | Manages the state and verification process for TOTP codes, reading/writing the secret from a specified path. |
| `TotpGuard.enabled` | Property | Returns `True` if a secret has been successfully loaded from the configured path. |
| `TotpGuard.setup()` | Method | Generates a new secret, securely writes it to the configuration path, and returns the new secret. |
| `TotpGuard.verify(code)` | Method | Checks if the provided code matches the expected TOTP code within the allowed clock drift window, ensuring codes are not replayed. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The system relies on HMAC-SHA1 to generate the code, using the time counter (derived from `time.time() // STEP`) as the message input. Verification checks a window of steps (`WINDOW`) around the current time to account for clock drift. The `TotpGuard` uses a lock (`threading.Lock`) to ensure that the `_last_counter` is updated atomically, preventing replay attacks.

- **Side Effects:** Reads and writes to the filesystem via the path provided in `TotpGuard` initialization (reading the secret, writing the secret during `setup`). It also uses `os.chmod` to enforce strict file permissions (`0o600`).

- **Error Handling:** The `_secret` method catches `FileNotFoundError`, `ValueError`, and `OSError` during file reading, returning `None` upon failure, which results in verification failure.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `base64`, `hashlib`, `hmac`, `json`, `os`, `secrets`, `struct`, `threading`, `time`, `urllib.parse`.
- **Internal:** None.