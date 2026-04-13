

## 1. Architectural Role  
Manages audio recording and processing with asynchronous execution and user input handling.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `Microphone` | Class | Handles audio recording, user input detection, and asynchronous execution. |  
| `start_recording` | Method | Initiates audio recording in a separate thread. |  
| `stop_recording` | Method | Terminates recording, saves frames, and triggers callbacks. |  
| `save_as_wave` | Method | Exports recorded audio frames to a WAV file. |  
| `is_recording` | Method | Checks if the microphone is actively recording. |  
| `output_requested` | Method | Stops recording if active via user input. |  
| `run` | Method | Executes the recording thread and handles user input. |  
| `__init__` | Method | Initializes audio parameters and state variables. |  
| `_run_thread` | Method | Core logic for capturing audio data in chunks. |  
| `_check_input` | Method | Waits for user input to terminate recording. |  

## 3. Execution Logic & Flow  
- **Initialization**: Sets `max_record_seconds`, `start_recording_text`, `recording_text`, and `end_recording_text` via constructor. Initializes `pyaudio`, `frames`, `_stream`, and `_is_running` state.  
- **Data Path**: Input (audio stream)  `_stream.read(CHUNK)`  `frames.append(data)`  `save_as_wave` (output).  
- **Conditional Branching**:  
  - `if self._is_running is False`: Breaks the recording loop.  
  - `if self.is_recording()`: Triggers `stop_recording()` on input.  

## 4. Resource Dependencies  
- **Standard Libraries**: `threading`, `pyaudio`, `wave`, `time`.  
- **Internal Modules**: `core.command_executor` (AsyncExecutor), `color` (ANSI color codes).  
- **External Packages**: `pyaudio`, `wave`.  

## 5. Configuration & Environment  
- **Hardcoded Constants**: `FORMAT`, `CHANNELS`, `RATE`, `CHUNK`, `RECORD_SECONDS`.  
- **Environment Lookups**: None.