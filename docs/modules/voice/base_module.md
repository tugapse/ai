## 1. Architectural Role
Provides an abstract base class for asynchronous text-to-speech orchestration, managing the pipeline from text queuing and inference to hardware-resampled audio playback.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `BaseVoiceModule` | Class | Abstract base orchestrator for voice generation and playback. |
| `process_token` | Method | Enqueues text strings for asynchronous synthesis. |
| `abort` | Method | Flushes all queues and signals threads to discard current processing. |
| `collect_audio` | Method | Blocks execution until all queued text is processed and hardware buffers drain. |
| `shutdown` | Method | Stops threads and releases PyAudio hardware resources. |
| `_run_inference` | Method | Abstract method to be implemented by subclasses for text-to-audio conversion. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Sets `sample_rate` and `device_index`.
    2. Initializes `_text_queue` and `_audio_queue`.
    3. Spawns and starts two daemon threads: `_gen_thread` (`_generation_loop`) and `_play_thread` (`_playback_loop`).
- **Data Path**: 
    `process_token(text)` $\rightarrow$ `_text_queue` $\rightarrow$ `_generation_loop` $\rightarrow$ `_run_inference()` $\rightarrow$ `_audio_queue` $\rightarrow$ `_playback_loop` $\rightarrow$ `PyAudio` stream $\rightarrow$ Hardware Output.
- **Conditional Branching**:
    - **Hardware Init**: `_init_audio_hardware` iterates through a list of candidate sample rates (`[sample_rate, 44100, 48000]`) until `pa.open` succeeds.
    - **Resampling**: In `_playback_loop`, if `active_sample_rate` $\neq$ `sample_rate`, `np.interp` is used to resample the audio chunk.
    - **Abort Signal**: Both loops check `_abort_signal.is_set()` to skip processing current items in the queue.
    - **Hardware Buffer Drain**: `collect_audio` performs a sequential join of both queues followed by a 2-second `time.sleep` if the stream is active.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `time`, `threading`, `queue`, `contextlib`, `sys`
- **Internal Modules**: `functions` (aliased as `func`)
- **External Packages**: `numpy`, `pyaudio`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `sample_rate`: Default `24000`.
    - `frames_per_buffer`: `1024`.
    - `rates`: `[int(self.sample_rate), 44100, 48000]`.
    - `collect_audio` sleep duration: `2` seconds.
    - Loop timeouts: `0.5` seconds.
- **Environment Lookups**: None.