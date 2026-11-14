## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| Microphone | ai/core/listen |

This component is responsible for capturing raw audio input from a microphone. It manages the initialization of the PyAudio interface, streams audio data in defined chunks, and provides mechanisms to start and stop the recording process. Its primary responsibility is to capture a specified duration of audio frames for subsequent processing by the AI system.

The `Microphone` class acts as a specialized service layer within the application architecture. It inherits from [AsyncExecutor](/ai/chat/command_executor.md) to manage its execution flow, handling the asynchronous nature of audio capture. It relies on external libraries like `pyaudio` to interface with hardware, and it interfaces with [Color](/ai/color.md) for display purposes.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `Microphone` | Class | Manages audio recording, providing methods to start, stop, and retrieve recorded frames. |
| `Microphone.start_recording` | Method | Initiates audio capture, optionally calling a provided callback upon completion. |
| `Microphone.stop_recording` | Method | Halts the active audio stream, cleans up resources, and returns the captured audio frames. |
| `Microphone.save_as_wave` | Method | Writes the currently held audio frames to a specified `.wav` file on the filesystem. |
| `Microphone.is_recording` | Method | Returns a boolean indicating whether the microphone is currently capturing audio. |
| `Microphone.output_requested` | Method | Checks the recording status and stops the process if recording is active. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The recording process runs in an internal thread managed by the `run` method. It initializes PyAudio, opens an input stream, and iteratively reads chunks of audio data into the `self.frames` list for a duration determined by `max_record_seconds`. The display updates are managed by continuously printing and overwriting the line using ANSI escape codes (`LINE_CLEAR`).
- **Side Effects:** Writes to the filesystem when `save_as_wave` is called. Interacts directly with external hardware (microphone) via `pyaudio`. Mutates internal state (`self._is_running`, `self.frames`).
- **Error Handling:** Raises `AttributeError` if `save_as_wave` is called before the audio object (`self.audio`) is initialized. The stream and audio resources are explicitly stopped and closed in `stop_recording`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `threading`, `pyaudio`, `wave`, `time`
- **Internal:** [AsyncExecutor](/ai/chat/command_executor.md), [Color](/ai/color.md)