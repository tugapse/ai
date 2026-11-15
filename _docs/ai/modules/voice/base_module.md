## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| BaseVoiceModule | [ai/modules/voice/base_module](/ai/modules/voice/base_module.md) |

This component defines the abstract foundation for all voice processing modules. Its primary responsibility is to orchestrate the entire Text-to-Speech (TTS) pipeline, managing the asynchronous flow from text input to final audio output. It handles complex tasks such as threading, hardware initialization via PyAudio, volume scaling, and ensuring smooth audio buffer draining to prevent clipping.

This class serves as a core service layer within the application architecture. It acts as the central coordinator, decoupling the TTS generation logic (implemented by subclasses via `_run_inference`) from the playback mechanism. It relies on internal queues to manage data flow between the generation thread and the playback thread, fitting into the service layer that interfaces with other components like [ai.functions](/ai/functions.md) for logging.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `BaseVoiceModule` | Class | Abstract base class managing TTS pipeline initialization and execution. |
| `process_token(text: str)` | Method | Queues a new piece of text to be processed by the TTS generation thread. |
| `abort()` | Method | Immediately halts all ongoing generation and playback, clearing queues. |
| `collect_audio()` | Method | Blocks execution until all queued text has been processed and the hardware buffer has fully drained. |
| `shutdown()` | Method | Gracefully stops all threads and releases all underlying audio hardware resources. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The module operates using two dedicated daemon threads: one for generation (`_generation_loop`) and one for playback (`_playback_loop`). Text is placed in `_text_queue`, processed by the abstract `_run_inference`, and the resulting audio is placed in `_audio_queue`. The playback loop handles necessary resampling if the inferred sample rate differs from the desired rate, applies volume scaling, and writes data to the active PyAudio stream. `collect_audio` ensures sequential completion by joining both queues and adding a final sleep to drain the hardware buffer.

- **Side Effects:** Interacts heavily with external hardware (PyAudio for audio output), spawns and manages multiple threads, and reads/writes to internal queues. The `_silence_stderr` context manager redirects `sys.stderr` to `/dev/null`.

- **Error Handling:** The `_init_audio_hardware` method iterates over a list of standard rates (`[24000, 44100, 48000]`) and continues upon failure until a stream can be successfully opened. The playback loop includes `try...except` blocks to handle potential stream write errors by setting `self.stream = None`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `time`, `threading`, `queue`, `numpy`, `pyaudio`, `contextlib`, `sys`.
- **Internal:** [ai/functions](/ai/functions.md)