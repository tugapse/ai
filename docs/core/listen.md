## 1. Architectural Role
The `Microphone` class provides an asynchronous interface for capturing raw audio input from the system hardware, managing the recording lifecycle, and exporting the resulting audio data as byte frames or WAV files.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `Microphone` | Class | Inherits `AsyncExecutor`; manages audio capture, stream lifecycle, and recording state. |
| `__init__` | Method | Initializes recording constraints, UI text templates, and state flags. |
| `_check_input` | Method | Blocks for user input to trigger `stop_recording`. |
| `_run_thread` | Method | Core loop: opens PyAudio stream, reads chunks, updates CLI timer, and collects frames. |
| `run` | Method | Overrides `AsyncExecutor.run` to initiate the recording process. |
| `start_recording` | Method | Triggers the recording sequence and assigns an optional completion callback. |
| `stop_recording` | Method | Terminates the audio stream, closes PyAudio, and triggers the finished callback. |
| `save_as_wave` | Method | Writes collected audio frames to a physical `.wav` file using the `wave` module. |
| `is_recording` | Method | Returns the boolean state of `_is_running`. |
| `output_requested` | Method | Forces `stop_recording` if the microphone is currently active. |

## 3. Execution Logic & Flow
- **Initialization**: Sets `_is_running` to `False`, initializes an empty `frames` list, and configures text templates for CLI feedback.
- **Data Path**: 
    1. `start_recording()` $\rightarrow$ `run()` $\rightarrow$ `_run_thread()`.
    2. `pyaudio.PyAudio().open()` $\rightarrow$ Stream created.
    3. `_stream.read(CHUNK)` $\rightarrow$ Raw bytes captured $\rightarrow$ Appended to `self.frames`.
    4. `wave.open()` $\rightarrow$ `writeframes(b''.join(self.frames))` $\rightarrow$ Disk storage.
- **Conditional Branching**:
    - **Recording Loop**: Continues until either `max_record_seconds` is reached or `_is_running` is set to `False` (via `stop_recording` or `_check_input`).
    - **Output Request**: `output_requested()` checks `is_recording()` to determine if an active stream must be forcibly closed.

## 4. Resource Dependencies
- **Standard Libraries**: `threading`, `wave`, `time`
- **Internal Modules**: `core.command_executor.AsyncExecutor`, `core.command_executor.ExecutorResult`, `color.Color`
- **External Packages**: `pyaudio`

## 5. Configuration & Environment
- **Hardcoded Constants**:
    - `FORMAT`: `pyaudio.paInt16`
    - `CHANNELS`: `2`
    - `RATE`: `44100`
    - `CHUNK`: `1024`
    - `RECORD_SECONDS`: `10`
    - `LINE_CLEAR`: `'\x1b[2K'`