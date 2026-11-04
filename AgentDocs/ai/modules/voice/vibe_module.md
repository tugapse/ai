## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **VibeVoiceModule** | [src/ai/modules/voice/vibe_module.py](/src/ai/modules/voice/vibe_module.py) |

The `VibeVoiceModule` implements the VibeVoice-Realtime-0.5B text-to-speech (TTS) model. Its primary responsibility is to transform text input into high-quality, real-time audio waveforms using the official Microsoft VibeVoice streaming architecture.

This component functions as a specialized audio generation engine within the voice module subsystem. It integrates with the broader application by extending [BaseVoiceModule](/src/ai/modules/voice/base_module.md), handling hardware acceleration (CUDA/CPU) detection, voice profile management, and the complex orchestration of model weights and processors required for low-latency speech synthesis.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `VibeVoiceModule` | Class | The primary TTS engine. Initializes with a `model_id`, `voice_file`, and `volume`. |
| `preload()` | Method | Triggers the asynchronous loading of model weights, processors, and voice embeddings. |
| `_run_inference(text: str)` | Method | Internal core logic that converts a string into a `np.ndarray` audio waveform. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Hardware Auto-detection:** Automatically selects between `cuda` (using `float16`) and `cpu` (using `float32`) based on availability.
    - **Voice Profile Discovery:** Recursively searches the filesystem for an `assets/voices` directory to locate `.pt` voice embedding files. It includes a fallback mechanism to select the first available voice if the preferred file is missing.
    - **Recursive Casting:** Implements `_recursive_cast` to ensure all tensors within complex nested structures (dicts, lists, or custom objects) are moved to the correct device and data type.
    - **Inference Pipeline:** Uses a `VibeVoiceStreamingProcessor` to process text with cached prompts, followed by a `torch.amp.autocast` context for optimized generation via the `VibeVoiceStreamingForConditionalGenerationInference` model.
- **Side Effects:** 
    - **Filesystem Access:** Reads voice embedding files (`.pt`) from the local disk.
    - **Hardware Utilization:** Allocates significant VRAM/RAM for loading the 0.5B parameter model.
    - **Logging:** Emits status and diagnostic logs (including peak amplitude) via the internal logging utility.
- **Error Handling:** 
    - If the preferred voice file is not found, it attempts to find any valid `.pt` file in the voice directory.
    - If the model or input text is invalid/empty, it returns a zeroed NumPy array to prevent downstream pipeline crashes.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No direct environment variables are required, though hardware capability (CUDA) dictates runtime behavior.

**Module Dependencies:**
- **Standard/External:** `os`, `torch`, `copy`, `numpy`, `pathlib`, `vibevoice` (external package).
- **Internal:** 
    - [ai.modules.voice.base_module](/src/ai/modules/voice/base_module.md)
    - [ai.functions](/src/ai/functions.md)