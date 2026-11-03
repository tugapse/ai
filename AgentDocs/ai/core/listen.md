## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Microphone** | [src/ai/core/listen.py](/AgentDocs/ai/core/listen.md) |

The `Microphone` component is responsible for capturing real-time audio input from the system's default microphone. It provides a mechanism to record audio chunks into memory, allowing for both time-limited recordings and interrupt-driven stops (via user input).

This component functions as an asynchronous executor within the broader AI architecture, specifically serving as a data ingestion layer for voice-based interactions. It transforms physical acoustic input into digital audio frames that can be subsequently processed by speech-to-text or other audio analysis modules.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `Microphone(...)` | Class | Manages audio capture. Inherits from `AsyncExecutor`. Configurable via `max_record_seconds` and various UI text strings. |
| `start_recording(callback=None)` | Method | Initiates the recording process. Can accept an optional callback function to be executed upon completion. |
| `stop_recording()` | Method | Terminates the current audio stream, cleans up PyAudio resources, and returns the list of recorded frames. |
| `save_as_wave(filename)` | Method | Persists the currently held audio frames to a `.wav` file on the filesystem. |
| `is_recording()` | Method | Returns a boolean indicating whether the recording loop is currently active. |
| `output_requested()` | Method | An interface method to force-stop the recording if an external process requests an immediate output. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component utilizes `pyaudio` to open an input stream with a fixed configuration (16-bit integer, stereo, 44.1 kHz). It runs a recording loop that reads data in `CHUNK` sizes, appending them to an internal list. It uses ANSI escape sequences (`LINE_CLEAR`) to provide a live-updating timer in the console during the recording process.
- **Side Effects:** 
    - **Hardware Interaction:** Accesses the system's microphone hardware via `pyaudio`.
    - **Filesystem:** The `save_as_wave` method writes binary audio data to the disk.
    - **Console I/O:** Frequently writes to `stdout` to update the recording progress timer and status messages.
- **Error Handling:** The `save_as_wave` method raises an `AttributeError` if attempted before the `audio` object has been initialized (i.e., before recording has started).

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables are explicitly required by this module, though system-level microphone permissions are necessary.

**Module Dependencies:**
- **Standard/External:** `threading`, `pyaudio`, `wave`, `time`.
- **Internal:** 
    - [AsyncExecutor](/AgentDocs/ai/chat/command_executor.md)
    - [ExecutorResult](/AgentDocs/ai/chat/command_executor.md)
    - [Color](/AgentDocs/ai/color.md)