## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| stdin_reader | ai/stdin_reader |

This component provides robust utilities for reading input that is piped into the command-line interface (CLI). Its primary responsibility is to prevent the program from indefinitely hanging when reading from standard input (`sys.stdin`) if that input stream is open but never written to by the parent process (e.g., in certain IDE or agent execution environments). It handles different input scenarios—terminal, regular files, and pipes/sockets—with distinct behaviors.

It functions as a low-level I/O utility service within the application's input handling layer. It determines the nature of `sys.stdin` (e.g., whether it's a TTY, a pipe, or a regular file) and delegates the reading process accordingly, often coordinating with other components like [ai.functions](/ai/functions.md) for output signaling when waiting for input.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| read_piped_stdin | Function | Reads input piped into the program. Determines if input should be read immediately, waited for, or ignored based on whether other inputs were provided and the nature of the stream. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The function first checks if the stream is a TTY or closed, returning immediately if so. It then uses `os.fstat` to determine the file descriptor's mode. If the stream is not a FIFO or socket, it reads immediately. If it is a pipe/socket, the logic branches: if no other input is present, it waits for a hint period before reading; if other input is present, it waits for a configurable duration (`AI_STDIN_WAIT`) for the first byte before reading the entire stream or ignoring it if no data arrives.
- **Side Effects:** Reads from standard input (`sys.stdin`), uses `select.select` to monitor file descriptors, and calls functions from [ai.color](/ai/color.md) and [ai.functions](/ai/functions.md) for output.
- **Error Handling:** Catches `ValueError`, `OSError`, and `AttributeError` during file descriptor inspection, returning an empty string upon failure. It also handles `ValueError` during environment variable parsing for `AI_STDIN_WAIT`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- AI_STDIN_WAIT — Specifies the maximum number of seconds to wait for the first byte when reading from a piped stdin when other input is also present. Defaults to 3.0 seconds.

**Module Dependencies:**
- **Standard/External:** `os`, `select`, `stat`, `sys`, `typing`
- **Internal:** [ai.functions](/ai/functions.md), [ai.color](/ai/color.md)