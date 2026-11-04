## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **BaseVoiceModule** | [src/ai/modules/voice/base_module.py](/src/ai/modules/voice/base_module.py) |

The `BaseVoiceModule` is an abstract base class that serves as the core orchestrator for text-to-speech (TTS) generation and audio playback. It is designed to manage the complexities of asynchronous audio processing, including threading, hardware initialization, and buffer management, to ensure smooth, uninterrupted speech output.

This component acts as a foundational layer within the voice module subsystem. It provides a standardized pipeline where text is queued, converted to audio waveforms via an abstract inference method, and subsequently played through audio hardware. By handling low-level concerns like sample rate resampling and volume scaling, it allows specific TTS implementations to focus solely on model inference.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `BaseVoiceModule(sample_rate=24000, device_index=None, volume=1.0)` | Class | Abstract base class for voice modules. Initializes generation and playback threads. |
| `process_token(text: str)` | Method | Adds a string of text to the internal `_text_queue` for asynchronous TTS processing. |
| `abort()` | Method | Immediately stops all ongoing generation and playback by clearing queues and signaling worker threads. |
| `collect_audio()` | Method | A blocking call that waits for all queued text to be generated and for the hardware buffer to fully drain. |
| `shutdown()` | Method | Gracefully terminates worker threads and releases all PyAudio hardware resources. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The module operates using two dedicated daemon threads:
    - **Generation Loop:** Consumes text from `_text_queue`, executes the subclass-specific `_run_inference` method, and pushes the resulting `numpy` arrays into `_audio_queue`.
    - **Playback Loop:** Consumes audio chunks from `_audio_queue`, performs linear interpolation resampling if the hardware `active_sample_rate` differs from the source `sample_rate`, applies volume scaling, and writes the raw bytes to the PyAudio stream.
- **Side Effects:** 
    - **Hardware Interaction:** Directly initializes and controls audio output devices via `pyaudio`.
    - **Standard Error Redirection:** Temporarily redirects `stderr` to `/dev/null` during hardware initialization to suppress driver-level noise (ALSA/JACK/PortAudio).
    - **Logging:** Utilizes `ai.functions` for system logging.
- **Error Handling:** 
    - If no compatible sample rate (tested against the requested rate, 44100, and 48000) is found during hardware initialization, it logs a critical error via `func.log`.
    - Uses a `_silence_stderr` context manager to prevent driver warnings from polluting the console.
    - Includes a "tail" wait in `collect_audio` (2 seconds) to prevent audio clipping caused by hardware buffer latency.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `time`, `threading`, `queue`, `numpy`, `pyaudio`, `contextlib`, `sys`, `abc`, `typing`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)