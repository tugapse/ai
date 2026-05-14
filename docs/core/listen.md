## 1. Architectural Role
Provides an asynchronous command execution interface for capturing, buffering, and persisting real-time audio input via hardware microphone streams.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `Microphone` | Class | Manages the lifecycle of audio recording, thread execution, and wave file serialization. |
| `__init__` | Method | Initializes recording parameters, UI text templates, and inherits from `AsyncExecutor`. |
| `_check_input` | Method | Blocks for user input to trigger an interrupt in the recording loop. |
| `_run_thread` | Method | Executes the PyAudio stream loop, populates frame buffers, and updates the CLI progress display. |
| `run` | Method | Orchestrates the execution of the command via the `AsyncExecutor` superclass. |
| `start_recording` | Method | Initiates the recording process and assigns a completion callback. |
| `stop_recording` | Method | Terminates the PyAudio stream, closes resources, and triggers the `finished_callback`. |
| `save_as_wave` | Method | Serializes the internal `frames` buffer into a `.wav` file using specified audio parameters. |
| `is_recording` | Method | Returns the current boolean state of the `_is_running` flag. |
| `output_requested` | Method | Checks active recording status and invokes `stop_recording` if true. |

## 3. Execution Logic & Flow
- **Initialization**: The `Microphone` instance is instantiated with specific text templates and a `max_record_seconds` limit; it registers itself as an `AsyncExecutor` under the `"/listen"` command path.
- **Data Path**: 
    1. **Input**: Hardware audio stream captured via `pyaudio` in `CHUNK` increments.
    2. **Processing**: Raw byte data is appended to the `self.frames` list; concurrent CLI updates are rendered using `LINE_CLEAR` and string replacement.
    3. **Output**: Captured frames are either passed to `finished_callback` upon termination or written to disk via `save_as_wave`.
- **Conditional Branching**:
    - **Loop Termination**: The recording loop breaks if `self._is_running` becomes `False` (triggered by `stop_recording`) or if the `max_record_seconds` duration is reached.
    - **Output Interruption**: `output_requested` checks `is_recording()` to decide whether to force-stop the stream.

## 4. Resource Dependencies
- **Standard Libraries**: `threading`, `wave`, `time`
- **Internal Modules**: `chat.command_executor.AsyncExecutor`, `chat.command_executor.ExecutorResult`, `color.Color`
- **External Packages**: `pyaudio`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `FORMAT`: `pyaudio.paInt16`
    - `CHANNELS`: `2`
    - `RATE`: `44100`
    - `CHUNK`: `1024`
    - `RECORD_SECONDS`: `10`
    - `LINE_CLEAR`: `'\x1b[2K'`
- **Environment Lookups**: None.