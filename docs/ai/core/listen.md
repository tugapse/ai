## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | Microphone |
| Source file | listen.py |

The **Microphone** component serves as the primary audio ingestion interface for the system. It is responsible for interfacing with hardware via PyAudio to capture real-time acoustic data, managing the lifecycle of audio streams, and providing mechanisms to either stop recording via user interrupt or time-based expiration.

Its strategic position is within the core input layer, acting as a bridge between physical sound waves and digital audio buffers. By inheriting from [AsyncExecutor](/docs/ai/chat/command_executor.md), it integrates into the system's asynchronous command execution framework, allowing audio capture to be treated as a manageable, interruptible task within the broader execution flow.

**Functional Mission**
The primary responsibility of **Microphone** is to provide a robust, thread-safe mechanism for recording high-fidelity audio data. It solves the problem of capturing continuous audio streams while providing real-time visual feedback to the user and ensuring that the recording can be gracefully terminated and converted into standard formats like WAV.

**System Context & Integration**
The component functions as a data producer for downstream voice processing modules. Once a recording is completed, it triggers a callback with the captured frames, which typically feeds into modules like [speech_bridge](/docs/ai/modules/voice/speech_bridge.md) for transcription or analysis. It utilizes [Color](/docs/ai/color.md) for terminal-based UI feedback during the recording process and relies on the [AsyncExecutor](/docs/ai/chat/command_executor.md) pattern to ensure it can be controlled by the system's central command logic.

- **INTERNAL REFERENCES**: [AsyncExecutor](/docs/ai/chat/command_executor.md), [Color](/docs/ai/color.md).

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `FORMAT` (Default: `pyaudio.paInt16`)  Defines the bit depth of the audio data.
- `CHANNELS` (Default: `2`)  Sets the recording to stereo.
- `RATE` (Default: `44100`)  Sets the sampling frequency to 44.1 kHz.
- `CHUNK` (Default: `1024`)  The number of audio frames per buffer read.
- `RECORD_SECONDS` (Default: `10`)  The default maximum duration for a recording session.
- `LINE_CLEAR` (Default: `'\x1b[2K'`)  ANSI escape sequence used to clear the terminal line for UI updates.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `Microphone` | Class | Manages the audio recording lifecycle, threading, and file export. |
| `start_recording` | Method | Initiates the recording process and accepts an optional completion callback. |
| `stop_recording` | Method | Terminates the audio stream, cleans up PyAudio resources, and triggers the callback. |
| `save_as_wave` | Method | Persists the captured audio frames to a `.wav` file on disk. |
| `is_recording` | Method | Returns the current operational state of the microphone. |
| `output_requested` | Method | An override to stop recording if an external output command is issued. |
| `_run_thread` | Method | The internal loop that performs the actual buffer reading and UI updates. |
| `_check_input` | Method | A blocking input listener used to stop recording via user interaction. |

## 4. Execution Logic & Flow
- **Initialization**: The class is instantiated with specific text templates and a maximum duration. It initializes internal state variables (`_is_running`, `frames`, `_stream`) to empty or false values.
- **Data Path**: 
    1. **Input**: Raw audio data is pulled from the hardware via `self._stream.read(CHUNK)`.
    2. **Processing**: Data chunks are appended to the `self.frames` list. Simultaneously, the terminal UI is updated by calculating elapsed time and replacing placeholders in `recording_text`.
    3. **Output**: Upon termination, the list of bytes is either passed to a `finished_callback` or written to a file via `save_as_wave` using the `wave` module.
- **Conditional Branching**:
    - **Termination Check**: Inside the recording loop, the process checks `if self._is_running is False` to allow for external interruption.
    - **Resource Cleanup**: The `stop_recording` method checks for the existence of `_stream` and `audio` objects before attempting to close/terminate them to prevent null pointer errors.

## 5. Resource Dependencies
- **Standard Libraries**: `threading`, `wave`, `time`
- **Internal Modules**: 
    - [AsyncExecutor](/docs/ai/chat/command_executor.md)
    - [Color](/docs/ai/color.md)
- **External Packages**: `pyaudio`