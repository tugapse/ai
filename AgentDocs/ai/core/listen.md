## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Microphone** | [src/ai/core/listen.py](/src/ai/core/listen.py) |

The `Microphone` component is responsible for capturing real-time audio input from the system's hardware. It manages the lifecycle of an audio stream, handles the buffering of raw audio frames, and provides mechanisms to either record for a fixed duration or until interrupted by user input.

Within the broader application architecture, this component serves as a low-level hardware interface. It functions as an `AsyncExecutor`, allowing audio capture to run in a non-blocking thread, which is essential for maintaining system responsiveness during voice-driven interactions. It provides the raw data necessary for subsequent speech-to-text or audio processing modules.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `Microphone(...)` | Class | Manages audio recording via `pyaudio`. Supports custom timing, status text, and callback execution upon completion. |
| `start_recording(callback=None)` | Method | Initiates the recording process in a separate thread and sets an optional callback to execute when finished. |
| `stop_recording()` | Method | Terminates the current audio stream, stops the recording loop, and returns the collected list of audio frames. |
| `save_as_wave(filename)` | Method | Writes the currently held audio frames to a `.wav` file on the filesystem using the configured sample rate and channels. |
| `is_recording()` | Method | Returns a boolean indicating whether the recording loop is currently active. |
| `output_requested()` | Method | A command-handler method that triggers `stop_recording()` if an active recording session is in progress. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component utilizes `pyaudio` to open an input stream with a fixed configuration (44.1 kHz, Stereo, 16-bit). It captures audio in chunks of 1024 frames. A loop iterates through the expected number of chunks based on `max_record_seconds`, appending data to an internal list. It uses ANSI escape sequences (`LINE_CLEAR`) to provide a dynamic, single-line terminal UI that updates the elapsed time during recording.
- **Side Effects:** 
    - **Hardware Access:** Directly interfaces with the system's microphone via `pyaudio`.
    - **Filesystem:** The `save_as_wave` method writes binary audio data to the disk.
    - **Terminal I/O:** Performs real-time `print` operations to update the user on recording status.
- **Error Handling:** The `save_as_wave` method raises an `AttributeError` if attempted before the `pyaudio` instance has been initialized.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `threading`, `pyaudio`, `wave`, `time`.
- **Internal:** 
    - [AsyncExecutor, ExecutorResult](/AgentDocs/ai/chat/command_executor.md)
    - [Color](/AgentDocs/ai/color.md)