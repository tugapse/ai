## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | BaseVoiceModule |
| Source file | base_module.py |

The **BaseVoiceModule** serves as the abstract foundational orchestrator for all voice-related operations within the system. It provides a standardized framework for managing the complex lifecycle of text-to-speech (TTS) workflows, specifically handling the asynchronous decoupling of text generation (inference) from audio playback.

By implementing a dual-thread architecture, the component ensures that the system remains responsive; one thread manages the computational load of running inference models, while a second thread manages the real-time requirements of audio hardware streaming. This separation prevents audio stuttering and allows for "buffer draining" logic to ensure sentence integrity.

**Functional Mission**
The primary responsibility of **BaseVoiceModule** is to provide a robust, thread-safe template for voice modules to transform text inputs into audible sound via hardware. It solves the problem of synchronization between variable-speed text generation and fixed-rate audio playback, providing built-in resampling, volume control, and hardware error recovery.

**System Context & Integration**
This component acts as the base class for specialized voice modules (such as those found in `/docs/ai/modules/voice/`). It sits between the high-level logic of the [Agent Orchestrator](/docs/ai/agents/agent_orchestrator.md) and the low-level audio hardware. It consumes text tokens via `process_token` and produces raw audio buffers that are eventually sent to the system's sound card. It utilizes [AI Functions](/docs/ai/functions.md) for centralized logging of critical hardware failures.

- **INTERNAL REFERENCES**: [AI Functions](/docs/ai/functions.md)

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `sample_rate` (Default: `24000`)  The target sampling frequency for audio generation.
- `rates` (Default: `[24000, 44100, 48000]`)  A list of fallback sample rates attempted during hardware initialization.
- `frames_per_buffer` (Default: `1024`)  The size of the audio buffer sent to PyAudio.
- `time.sleep(2)` (Default: `2`)  The "tail" duration used in `collect_audio` to allow the hardware buffer to drain.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `BaseVoiceModule` | Class | Abstract base class defining the voice orchestration lifecycle. |
| `_run_inference` | Abstract Method | Must be implemented by subclasses to convert text to `np.ndarray` audio. |
| `process_token` | Method | Entry point for injecting text into the generation queue. |
| `abort` | Method | Immediate interruption of current generation and playback tasks. |
| `collect_audio` | Method | Synchronous block that waits for all queues to empty and hardware to finish playing. |
| `shutdown` | Method | Graceful termination of threads and release of PyAudio hardware resources. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Sets up internal thread-safe queues (`_text_queue`, `_audio_queue`).
    2. Initializes `_is_running` state and `_abort_signal` event.
    3. Spawns the `_generation_loop` and `_playback_loop` as daemon threads.
- **Data Path**: 
    1. **Input**: `process_token(text)` $\rightarrow$ `_text_queue`.
    2. **Inference**: `_generation_loop` pulls text $\rightarrow$ calls `_run_inference(text)` $\rightarrow$ produces `np.ndarray` $\rightarrow$ `_audio_queue`.
    3. **Processing**: `_playback_loop` pulls audio $\rightarrow$ performs resampling (if `active_sample_rate` $\neq$ `sample_rate`) $\rightarrow$ applies `volume` scaling.
    4. **Output**: `stream.write(audio_chunk.tobytes())` $\rightarrow$ Audio Hardware.
- **Conditional Branching**:
    - **Hardware Init**: If `stream` is `None`, `_init_audio_hardware` iterates through supported rates until a successful `pa.open` occurs.
    - **Resampling**: If the hardware's `active_sample_rate` differs from the module's `sample_rate`, `np.interp` is used to linearly interpolate the audio buffer.
    - **Abort Logic**: If `_abort_signal` is set, the loops skip processing and the queues are cleared.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `time`, `threading`, `queue`, `contextlib`, `sys`, `abc`, `typing`
- **Internal Modules**: 
    - [AI Functions](/docs/ai/functions.md)
- **External Packages**: `numpy`, `pyaudio`