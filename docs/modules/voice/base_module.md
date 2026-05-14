## 1. Architectural Role

**Functional Mission**
The **BaseVoiceModule** serves as the abstract foundational orchestrator for all voice-based operations within the system. Its primary mission is to manage the asynchronous lifecycle of text-to-audio generation and real-time audio playback, solving the synchronization challenges inherent in streaming audio data. By implementing a dual-thread architecture (generation and playback) and a robust buffering mechanism, it ensures that audio output remains continuous and prevents the premature truncation of speech.

**System Context & Integration**
This component acts as the structural blueprint for specialized voice implementations, such as [vibe_module.md](/docs/modules/voice/vibe_module.md). It sits between high-level text generation services and the low-level hardware abstraction layer (PyAudio). It manages the flow of data from text queues to inference engines, and subsequently to audio queues for hardware output. It provides critical synchronization primitives like `collect_audio` to ensure downstream modules can wait for complete auditory delivery before proceeding with state changes.

## 2. Environment & Configuration

**Environment Lookups:**
- `device_index` (via `__init__`)  Specifies the hardware output device for PyAudio.

**Hardcoded Constants:**
- `sample_rate` (Default: `24000`)  The target audio sampling frequency.
- `rates` (Default: `[24000, 44100, 48000]`)  Supported hardware sample rate fallback list.
- `frames_per_buffer` (Default: `1024`)  The size of the audio buffer for the PyAudio stream.
- `tail_sleep_duration` (Default: `2`)  Time in seconds to wait for hardware buffer drainage in `collect_audio`.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `BaseVoiceModule` | Class | Abstract base class providing threading, queuing, and hardware management for voice modules. |
| `_run_inference` | Abstract Method | Forces subclasses to implement the specific logic for converting text to a NumPy audio array. |
| `process_token` | Method | Entry point for injecting text strings into the generation pipeline. |
| `abort` | Method | Clears all pending text and audio queues and resets the abort signal. |
| `collect_audio` | Method | Synchronous block that waits for the completion of generation, playback, and hardware buffer drainage. |
| `shutdown` | Method | Gracefully terminates threads, clears queues, and releases PyAudio hardware resources. |

## 4. Execution Logic & Flow

- **Initialization**: 
    - Initializes `_text_queue` and `_audio_queue`.
    - Spawns `_gen_thread` (targeting `_generation_loop`) and `_play_thread` (targeting `_playback_loop`) as daemon threads.
    - Sets initial volume and sample rate parameters.
- **Data Path**: 
    - **Input**: `process_token(text)` $\rightarrow$ `_text_queue`.
    - **Processing (Gen Thread)**: `_text_queue` $\rightarrow$ `_run_inference(text)` $\rightarrow$ `audio_chunk` (NumPy array) $\rightarrow$ `_audio_queue`.
    - **Processing (Play Thread)**: `_audio_queue` $\rightarrow$ Resampling (if `active_sample_rate` $\neq$ `sample_rate`) $\rightarrow$ Volume Scaling $\rightarrow$ `stream.write()`.
    - **Output**: Hardware audio stream.
- **Conditional Branching**:
    - **Hardware Init**: If `stream` is `None` during playback, `_init_audio_hardware` attempts to open a stream using a prioritized list of sample rates.
    - **Abort Logic**: If `_abort_signal` is set, the generation loop skips inference, and the playback loop skips writing to the stream.
    - **Resampling**: If the hardware's `active_sample_rate` differs from the module's `sample_rate`, linear interpolation is applied via `np.interp`.

## 5. Resource Dependencies

- **Standard Libraries**: `os`, `time`, `threading`, `queue`, `contextlib`, `sys`, `abc`, `typing`
- **Internal Modules**: 
    - [functions](/docs/functions.md)
- **External Packages**: `numpy`, `pyaudio`