

## 1. Architectural Role  
Voice processing pipeline orchestrator for text-to-speech generation and playback with buffer drain logic to prevent audio truncation.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `BaseVoiceModule` | Class | Abstract base class for voice modules managing text-to-speech generation and audio playback |  
| `_run_inference` | Abstract Method | Interface for text-to-audio conversion logic |  
| `process_token` | Method | Enqueues text for inference processing |  
| `abort` | Method | Clears queues and signals threads to terminate |  
| `collect_audio` | Method | Waits for all audio to play via hardware buffer drain |  
| `shutdown` | Method | Gracefully stops threads, releases audio resources |  
| `_init_audio_hardware` | Method | Initializes PyAudio stream with fallback sample rates |  
| `_silence_stderr` | Context Manager | Suppresses ALSA/JACK/PortAudio noise |  
| `_generation_loop` | Thread Target | Processes text queue into audio chunks |  
| `_playback_loop` | Thread Target | Plays audio chunks via PyAudio stream |  

## 3. Execution Logic & Flow  
- **Initialization**:  
  - Initializes sample rate, device index, queues, PyAudio instance, threads, and sets `_is_running` to True.  
  - Starts `_gen_thread` and `_play_thread` daemons.  
- **Data Path**:  
  - `process_token(text)`  `_text_queue.put(text)`  `_generation_loop` processes text via `_run_inference(text)`  `_audio_queue.put(audio)`  `_playback_loop` retrieves audio, resamples if needed, and writes to stream.  
- **Conditional Branching**:  
  - `_generation_loop`: Checks `_abort_signal` before processing text; skips empty queue entries.  
  - `_playback_loop`: Checks `self.stream` existence, resamples audio if sample rate mismatch, and handles stream write errors.  
  - `collect_audio()`: Waits for `_text_queue.join()`, `_audio_queue.join()`, and hardware buffer drain via `time.sleep(2)`.  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `time`, `threading`, `queue`, `numpy`, `pyaudio`, `contextlib`, `sys`, `abc`, `typing`  
- **Internal Modules**: `functions`  
- **External Packages**: `pyaudio`  

## 5. Configuration & Environment  
- **Hardcoded Constants**: `sample_rate=24000`, `rates=[24000, 44100, 48000]`, `frames_per_buffer=1024`  
- **Environment Lookups**: None