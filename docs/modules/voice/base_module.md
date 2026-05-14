## 1. Architectural Role
Acts as the abstract foundational orchestrator for all voice-based modules within the system. It establishes a multi-threaded pipeline designed to decouple text-to-audio inference from real-time audio playback, managing hardware initialization, sample rate resampling, and volume normalization. It provides the lifecycle management (start, abort, collect, shutdown) required by concrete implementations like [vibes_module](modules/voice/vibes_module.md) or [speech_bridge](modules/voice/speech_bridge.md) to ensure seamless, non-blocking audio streaming and buffer drainage.

## 2. Environment & Configuration
**Environment Lookups:**
- `device_index` (via `__init__`)  Specifies the physical audio output device index.

**Hardcoded Constants:**
- `sample_rate` (Default: `24000`)  Target frequency for audio processing.
- `rates` (Default: `[24000, 44100, 48000]`)  Fallback list for hardware sample rate negotiation.
- `frames_per_buffer` (Default: `1024`)  PyAudio buffer size for stream stability.
- `tail_sleep_duration` (Default: `2`)  Time in seconds to wait for hardware buffer drainage during `collect_audio`.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `BaseVoiceModule` | Class | Abstract base class providing threading, queuing, and playback logic. |
| `_run_inference` | Abstract Method | Subclass-specific implementation for converting text to `np.ndarray` audio. |
| `process_token` | Method | Entry point to ingest text strings into the generation queue. |
| `abort` | Method | Immediate clearing of text/audio queues and resetting of the abort signal. |
| `collect_audio` | Method | Synchronous blocking call that waits for queues to empty and hardware buffers to drain. |
| `shutdown` | Method | Graceful termination of threads and release of PortAudio resources. |

## 4. Execution Logic & Flow
- **Initialization**: 
    - Sets up thread-safe `Queue` objects for text and audio.
    - Spawns `_gen_thread` (Inference) and `_play_thread` (Playback) as daemons.
    - Initializes `_abort_signal` (Event) to manage interruptions.
- **Data Path**: 
    1. `process_token(text)` $\rightarrow$ `_text_queue`.
    2. `_generation_loop` $\rightarrow$ calls `_run_inference(text)` $\rightarrow$ produces `np.ndarray` $\rightarrow$ `_audio_queue`.
    3. `_playback_loop` $\rightarrow$ pulls `np.ndarray` $\rightarrow$ performs Resampling $\rightarrow$ applies `volume` scaling $\rightarrow$ `stream.write()`.
- **Conditional Branching**:
    - **Hardware Init**: If `stream` is `None`, attempt to open hardware using a prioritized list of sample rates.
    - **Resampling**: If `active_sample_rate != sample_rate`, use linear interpolation (`np.interp`) to match hardware requirements.
    - **Abort Logic**: If `_abort_signal` is set, skip inference/playback and flush queues.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `time`, `threading`, `queue`, `contextlib`, `sys`, `abc`, `typing`.
- **Internal Modules**: 
    - [functions](functions.md)
- **External Packages**: `numpy`, `pyaudio`