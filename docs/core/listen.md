## 1. Architectural Role
The `Microphone` class acts as the hardware abstraction layer for audio ingestion, providing asynchronous recording capabilities and real-time feedback via the terminal. It extends [chat/command_executor.md](chat/command_executor.md) to integrate audio capture into the command execution lifecycle, facilitating the conversion of analog sound into digital byte frames for downstream processing.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `FORMAT` (Default: `pyaudio.paInt16`)  Bit depth of the audio stream.
- `CHANNELS` (Default: `2`)  Stereo audio configuration.
- `RATE` (Default: `44100`)  Sample rate in Hz.
- `CHUNK` (Default: `1024`)  Buffer size for audio data reads.
- `RECORD_SECONDS` (Default: `10`)  Global maximum recording duration.
- `LINE_CLEAR` (Default: `'\x1b[2K'`)  ANSI escape sequence for UI refreshing.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `Microphone` | Class | Manages PyAudio lifecycle, thread-based recording, and frame buffering. |
| `_check_input` | Method | Internal blocking call to wait for user Enter key to signal stop. |
| `_run_thread` | Method | The core execution loop that reads audio chunks and updates the UI. |
| `run` | Method | Orchestrates the execution via the `AsyncExecutor` superclass. |
| `start_recording` | Method | Entry point for initiating the recording process with an optional callback. |
| `stop_recording` | Method | Terminates the PyAudio stream and triggers the completion callback. |
| `save_as_wave` | Method | Serializes buffered frames into a `.wav` file. |
| `is_recording` | Method | Boolean check of the internal `_is_running` state. |
| `output_requested` | Method | External trigger to interrupt and finalize active recording. |

## 4. Execution Logic & Flow
- **Initialization**: Sets recording constraints (duration, text templates) and initializes `AsyncExecutor` state.
- **Data Path**: 
    - **Input**: `pyaudio` reads raw bytes from the hardware via `_stream.read(CHUNK)`.
    - **Processing**: Bytes are appended to the `self.frames` list; UI text is dynamically updated via string replacement of `{time}` and `{max_seconds}`.
    - **Output**: Captured frames are either held in memory for `_trigger_callback` or written to disk via `save_as_wave`.
- **Conditional Branching**: 
    - `if self._is_running is False`: Breaks the collection loop if an external stop command is issued.
    - `if self.is_recording()`: In `output_requested`, determines if a stop command is necessary.

## 5. Resource Dependencies
- **Standard Libraries**: `threading`, `wave`, `time`
- **Internal Modules**: 
    - [chat/command_executor.md](chat/command_executor.md)
    - [color.md](color.md)
- **External Packages**: `pyaudio`