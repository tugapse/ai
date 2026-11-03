## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **BaseVoiceModule** | [src/ai/modules/voice/base_module.py](/AgentDocs/ai/modules/voice/base_module.md) |

The `BaseVoiceModule` serves as the core orchestrator for the text-to-speech (TTS) and audio playback pipeline. It provides a standardized framework for managing asynchronous audio generation and hardware-level playback, ensuring that audio streams are processed without clipping or synchronization issues.

This component acts as an abstract foundation within the voice module subsystem. It is responsible for managing high-level concerns such as thread orchestration (generation vs. playback), hardware initialization via PyAudio, volume normalization, and buffer management. Subclasses are expected to implement the specific inference logic required to convert text into raw audio waveforms.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `BaseVoiceModule(sample_rate, device_index, volume)` | Class | Abstract base class for voice modules. Initializes generation and playback threads. |
| `process_token(text: str)` | Method | Adds a string of text to the internal processing queue for subsequent TTS generation. |
| `abort()` | Method | Immediately clears all text and audio queues and signals worker threads to stop current tasks. |
| `collect_audio()` | Method | A blocking call that waits for all queued text to be generated and for the hardware buffer to finish playing. |
| `shutdown()` | Method | Gracefully terminates worker threads and releases all PyAudio hardware resources. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The module utilizes two dedicated daemon threads: a `_generation_loop` that consumes text from a queue and executes `_run_inference`, and a `_playback_loop` that consumes resulting audio chunks, performs linear interpolation resampling if the hardware rate differs from the target rate, applies volume scaling, and writes to the audio stream.
- **Side Effects:** 
    - **Hardware Interaction:** Directly initializes and controls audio output hardware via `pyaudio`.
    - **System I/O:** Temporarily redirects `stderr` to `/dev/null` using low-level file descriptor manipulation (`os.dup2`) to suppress driver-level noise during hardware initialization.
    - **Threading:** Spawns multiple background threads that persist until `shutdown()` is called.
- **Error Handling:** 
    - Includes a fallback mechanism in `_init_audio_hardware` that iterates through common sample rates (target, 44100, 48000) if the primary rate fails.
    - If no compatible sample rate is found, it logs a critical error via `func.log`.
    - Uses a `_silence_stderr` context manager to prevent system-level audio driver warnings from polluting the standard error stream.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `time`, `threading`, `queue`, `numpy`, `pyaudio`, `contextlib`, `sys`, `abc`, `typing`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)