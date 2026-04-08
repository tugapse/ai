## 1. Architectural Role
Handles the recording and processing of audio input using the microphone.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `Microphone` | Class | Manages the recording process, including starting, stopping, and saving audio recordings. |
| `start_recording` | Method | Initiates the recording process. |
| `stop_recording` | Method | Stops the recording process and returns the recorded frames. |
| `save_as_wave` | Method | Saves the recorded frames as a wave file. |
| `is_recording` | Method | Checks if the microphone is currently recording. |
| `output_requested` | Method | Handles output request, stopping recording if active. |

## 3. Execution Logic & Flow
- **Initialization**: The `Microphone` class is initialized with default parameters for recording settings and text messages. The `audio` object is set to `None` and `frames` is initialized as an empty list.
- **Data Path**: 
  1. The `start_recording` method is called, which prints the start recording text and then calls the `run` method.
  2. The `run` method starts a new thread that calls `_run_thread`, which initializes the audio stream and starts recording.
  3. In `_run_thread`, audio data is read in chunks and appended to the `frames` list. The recording text is updated to show the elapsed time and the maximum recording time.
  4. If the user inputs something (e.g., pressing Enter), the `_check_input` method is called, which stops the recording.
  5. The recording is stopped by calling `stop_recording`, which closes the audio stream and terminates the audio object.
- **Conditional Branching**: 
  - The recording loop continues until the maximum recording time is reached or the user stops the recording.
  - The `_check_input` method stops the recording if user input is detected.

## 4. Resource Dependencies
- **Standard Libraries**: `threading`, `pyaudio`, `wave`, `time`
- **Internal Modules**: `core.command_executor`, `color`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: 
  - `FORMAT`, `CHANNELS`, `RATE`, `CHUNK`, `RECORD_SECONDS`
  - `LINE_CLEAR`
- **Environment Lookups**: None