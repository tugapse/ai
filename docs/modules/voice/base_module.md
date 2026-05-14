## 1. Architectural Role
Acts as an abstract base class and multi-threaded orchestrator for managing asynchronous text-to-audio generation and synchronized hardware playback.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `BaseVoiceModule` | Class | Abstract base class providing threading, queue management, and audio hardware interfacing. |
| `_run_inference` | Method | Abstract hook for subclasses to implement specific text-to-audio model logic. |
| `process_token` | Method | Public entry point to inject text strings into the generation pipeline. |
| `abort` | Method | Interrupts current processing by clearing queues and resetting the abort signal. |
| `collect_audio` | Method | Synchronous blocking call that waits for queue depletion and hardware buffer drainage. |
| `shutdown` | Method | Gracefully terminates threads, stops audio streams, and releases hardware resources. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Sets `sample_rate`, `device_index`, and sanitizes `volume`.
    2. Initializes `_text_queue` and `_audio_queue`.
    3. Spawns `_gen_thread` (`_generation_loop`) and `_play_thread` (`_playback_loop`) as daemons.
- **Data Path**: 
    1. `process_token(text)` $\rightarrow$ `_text_queue`.
    2. `_generation_loop` $\rightarrow$ `_run_inference(text)` $\rightarrow$ `audio_chunk` $\rightarrow$ `_audio_queue`.
    3. `_playback_loop` $\rightarrow$ Resampling (if `active_sample_rate` $\neq$ `sample_rate`) $\rightarrow$ Volume scaling $\rightarrow$ `stream.write()`.
- **Conditional Branching**:
    - **Hardware Init**: `_init_audio_hardware` iterates through a priority list of sample rates (`sample_rate`, 44100, 48000) until a successful `pa.open` occurs.
    - **Resampling**: `_playback_loop` checks if `active_sample_rate` matches target `sample_rate` before applying `np.interp`.
    - **Abort Logic**: Both loops check `_abort_signal.is_set()` before processing queue items.
    - **Error Recovery**: `_playback_loop` catches exceptions during `stream.write` and sets `self.stream = None` to trigger re-initialization.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `time`, `threading`, `queue`, `contextlib`, `sys`, `abc`, `typing`.
- **Internal Modules**: `functions` (as `func`).
- **External Packages**: `numpy` (as `np`), `pyaudio`.

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `rates`: `[int(self.sample_rate), 44100, 48000]`
    - `frames_per_buffer`: `1024`
    - `collect_audio` tail sleep: `2` seconds.
- **Environment Lookups**: None.