## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| ai/core/llms/api_retry | /ai/core/llms/api_retry.md |

This component provides a robust resilience layer for interacting with remote Large Language Model (LLM) APIs. Its primary responsibility is to automatically manage transient network or service-side failures—such as timeouts, rate limits (429), or server unavailability (503)—by implementing exponential backoff and jittered retries. It distinguishes between these recoverable transient errors and permanent configuration or input errors, which are allowed to fail immediately.

This module functions as a critical utility layer within the service architecture, sitting between the core LLM invocation logic and the external provider SDKs. It wraps API calls using functions like `call_with_retry` and `stream_with_retry`, ensuring that the upstream consumers of the LLM service only receive successful results or clearly defined, non-retryable `LLMAPIError` exceptions, abstracting away the complexities of network instability.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `LLMAPIError` | Class | Represents a failure during an API call that is not due to the model's output. Stores provider, transient status, status code, and attempt count. |
| `status_of` | Function | Attempts to extract the HTTP status code from a given SDK exception, checking standard attributes like `status_code` or `http_status`. |
| `is_transient` | Function | Determines if an exception warrants a retry based on status codes, known error classes, or specific exception text content. |
| `retry_after_seconds` | Function | Checks the exception's response headers for a `Retry-After` directive to determine an explicit wait time. |
| `RetryPolicy` | Class | Defines the parameters for the retry mechanism, including maximum attempts, base delay, and timeouts. |
| `RetryPolicy.from_config` | Class Method | Instantiates a `RetryPolicy` object by reading configuration parameters from one or more dictionary sources. |
| `RetryPolicy.delay` | Class Method | Calculates the appropriate backoff delay for a given attempt, prioritizing explicit `Retry-After` headers. |
| `wrap_error` | Function | Wraps an incoming exception into an `LLMAPIError`, correctly setting transient flags and recording attempt counts. |
| `_wait` | Function | A helper function that sleeps for a specified duration, respecting an optional stop event. |
| `call_with_retry` | Function | Executes a synchronous function (`fn`) with retries enabled for transient errors, returning the result upon success. |
| `stream_with_retry` | Function | Executes a streaming function (`open_stream`) with retries, handling partial success by raising `LLMAPIError(partial=True)` if the failure occurs after the first chunk. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The retry mechanism operates as a loop that executes the provided function (`fn` or `open_stream`). Before each execution, it checks the `RetryPolicy` and the exception type. If the exception is transient and retries remain, it calculates a delay using exponential backoff, potentially overriding it with a `Retry-After` header value, and pauses execution via `_wait`. If the failure occurs during streaming, it tracks whether any data was successfully yielded before deciding whether to treat the error as partial.
- **Side Effects:** Interacts with the network via the functions it wraps (calling external LLM APIs). It uses `threading.Event` for cooperative cancellation during waits.
- **Error Handling:** Raises `LLMAPIError` upon exhaustion of retries or if the initial error is deemed permanent. It catches `GeneratorExit` during streaming to ensure proper cleanup.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `random`, `threading`, `dataclasses`, `typing`
- **Internal:** [ai.functions](/ai/functions.md)