## 1. Architectural Role

**Functional Mission**
The **Microphone** class serves as the primary hardware abstraction layer for audio ingestion. Its core mission is to manage the lifecycle of real-time audio recording, capturing raw PCM data from the system's input device and providing mechanisms to either terminate recording via user interrupt or time-based expiration.

**System Context & Integration**
As a subclass of `AsyncExecutor` (defined in [chat/command_executor.md](/docs/chat/command_executor.md)), this component functions as an asynchronous command within the system's execution framework. It acts as the entry point for voice-based interactions, capturing audio frames that are subsequently passed to a callback functiontypically intended for downstream speech-to-text or audio processing modules. It integrates with the UI layer via [color.md](/docs/color.md) to provide real-time recording status updates to the terminal.

## 2. Environment & Configuration

**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
- `FORMAT` (Default: `pyaudio.paInt16`)  Specifies the 16-bit integer audio format.
- `CHANNELS` (Default: `2`)  Sets the recording to stereo.
- `RATE` (Default: `44100`)  Sets the sample rate to 44.1 kHz.
- `CHUNK` (Default: `1024`)  Defines the buffer size for reading audio data.
- `RECORD_SECONDS` (Default: `10`)  The default maximum duration for a recording session.
- `LINE_CLEAR` (Default: `'\x1b[2K'`)  ANSI escape sequence used to clear the terminal line for UI updates.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `Microphone` | Class | Manages audio hardware state, recording threads, and frame buffering. |
| `_check_input` | Method | Internal blocking call to wait for user Enter key to trigger `stop_recording`. |
| `_run_thread` | Method | The core execution loop that reads audio chunks from the stream and updates the UI. |
| `run` | Method | Executes the command within the `AsyncExecutor` framework. |
| `start_recording` | Method | Initiates the recording process and assigns a completion callback. |
| `stop_recording` | Method | Terminates the audio stream, cleans up PyAudio resources, and triggers the callback. |
| `save_as_wave` | Method | Serializes the buffered audio frames into a standard `.wav` file. |
| `is_recording` | Method | Returns the boolean state of the `_is_running` flag. |
| `output_requested` | Method | Interface method to force-stop recording if an external output command is issued. |

## 4. Execution Logic & Flow

- **Initialization**: The `Microphone` instance is initialized with custom text strings for UI feedback and a `max_record_seconds` limit. It registers itself with the command path `"/listen"`.
- **Data Path**: 
    1. **Input**: Raw audio bytes are read from the `pyaudio` stream in `CHUNK` increments.
    2. **Processing**: Bytes are appended to the `self.frames` list. The UI is updated via `print` statements using `LINE_CLEAR` and string replacement for time tracking.
    3. **Output**: Upon completion, the list of frames is passed to `self.finished_callback` or can be written to disk via `save_as_wave`.
- **Conditional Branching**:
    - **Time/Manual Stop**: The loop terminates if `self._is_running` becomes `False` (triggered by `stop_recording`) or if the loop index reaches the calculated maximum frames based on `max_record_seconds`.
    - **Interrupt**: `output_requested` provides a hook to break the recording loop if the system needs to pivot to an output task.

## 5. Resource Dependencies

- **Standard Libraries**: `threading`, `wave`, `time`
- **Internal Modules**: 
    - [chat/command_executor.md](/docs/chat/command_executor.md)
    - [color.md](/docs/color.md)
- **External Packages**: `pyaudio`