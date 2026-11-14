## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| VibeVoiceModule | /ai/modules/voice/vibe_module.md |

This component is responsible for integrating and managing the VibeVoice-Realtime-0.5B text-to-speech model. Its primary function is to handle the entire lifecycle of the TTS generation, from detecting available hardware (CUDA/CPU) to loading specific voice embeddings and executing the inference pipeline to produce raw audio waveforms from input text.

This module acts as a specialized service layer within the broader voice generation system. It relies on the base functionality provided by [BaseVoiceModule](/ai/modules/voice/base_module.md) for audio playback setup, while orchestrating external dependencies like the `vibevoice` package for model execution. It is crucial for translating textual input into audible output within the application's voice pipeline.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| VibeVoiceModule | Class | Implements the VibeVoice TTS functionality. Initialized with model ID and voice profile name. |
| preload | Method | Triggers the complete loading sequence for the model, processor, and voice embeddings. |
| _run_inference | Method | Converts a given text string into a synthesized audio waveform (NumPy array) using the loaded model. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The initialization process first detects the execution device and data type. It then searches the filesystem to locate the specified voice profile `.pt` file, loading its embeddings. Subsequently, it initializes the `VibeVoiceStreamingProcessor` and the main model. Inference is performed by passing processed text inputs and the cached voice embeddings to the model's `generate` method, utilizing PyTorch's `autocast` for optimized execution.
- **Side Effects:** Reads from the local filesystem to locate and load voice profile files. Interacts with external libraries (`torch`, `vibevoice`) which may involve network calls during model loading (though weights are loaded locally post-download). It mutates the internal state (`self.model`, `self.processor`, `self.voice_embeddings`) upon `preload`.
- **Error Handling:** Includes fallback logic when the preferred voice file is not found, attempting to load the first available `.pt` file in the `assets/voices` directory. It returns an array of zeros if the model is not initialized or the input text is empty in `_run_inference`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `torch`, `copy`, `numpy`, `pathlib`
- **Internal:** [BaseVoiceModule](/ai/modules/voice/base_module.md), [ai.functions](/ai/functions.md)