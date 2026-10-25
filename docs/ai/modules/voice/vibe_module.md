## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | VibeVoiceModule |
| Source file | vibe_module.py |

The **VibeVoiceModule** is a specialized implementation of a text-to-speech (TTS) engine designed for real-time streaming inference. It leverages the Microsoft VibeVoice-Realtime-0.5B model architecture to transform text inputs into high-fidelity audio waveforms, specifically optimized for low-latency conversational applications.

**Functional Mission**
The primary responsibility of **VibeVoiceVoiceModule** is to manage the lifecycle of the VibeVoice generative model, including hardware-aware weight loading, voice profile embedding management, and the execution of the inference pipeline. It solves the problem of converting linguistic tokens into playable audio buffers while maintaining specific vocal characteristics defined by `.pt` embedding files.

**System Context & Integration**
This component functions as a concrete implementation of the [BaseVoiceModule](/docs/ai/modules/voice/base_module.md) interface. It is intended to be managed and triggered by the [ModuleRegistry](/docs/ai/services/module_registry.md) during the system's preloading phase. Once initialized, it receives text strings from the orchestration layer and returns processed NumPy audio arrays, which are then passed to the underlying audio playback hardware managed by the base class. It utilizes [ai.functions](/docs/ai/functions.md) for system-wide logging and diagnostic reporting.

## 2. Environment & Configuration
**Environment Lookups:**
- `device` (via `_initialize_model`)  Detects available hardware (CUDA vs. CPU) to determine optimal tensor placement.
- `model_dtype` (via `_initialize_model`)  Determines precision (float16 for CUDA, float32 for CPU) to balance performance and memory.

**Hardcoded Constants:**
- `sample_rate` (Default: `24000`)  The target audio sampling frequency.
- `model_id` (Default: `"microsoft/VibeVoice-Realtime-0.5B"`)  The HuggingFace repository identifier for the model weights.
- `voice_file` (Default: `"pt-Spk1_man"`)  The identifier for the default voice embedding profile.
- `num_steps` (Default: `5`)  The number of DDPM inference steps configured for the model.
- `cfg_scale` (Default: `1.5`)  The Classifier-Free Guidance scale used during the `generate` call.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `VibeVoiceModule` | Class | Main implementation of the VibeVoice TTS engine. |
| `preload` | Method | Public entry point for the [ModuleRegistry](/docs/ai/services/module_registry.md) to trigger model loading. |
| `_initialize_model` | Method | Internal logic for hardware detection, path discovery, and weight loading. |
| `_recursive_cast` | Method | Utility to move complex nested structures (dicts/lists/tensors) to the correct device and dtype. |
| `_run_inference` | Method | The core execution loop: processes text $\rightarrow$ generates audio tensor $\rightarrow$ returns NumPy array. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Calls `super().__init__` to establish audio queues and playback threads via [BaseVoiceModule](/docs/ai/modules/voice/base_module.md).
    2. Sets initial state for model, processor, and embeddings to `None`.
- **Data Path**: 
    1. **Input**: Receives a `text` string via `_run_inference`.
    2. **Processing**: 
        - Deep-copies `voice_embeddings` to create a `prompt_cache`.
        - Passes text and cache to `processor.process_input_with_cached_prompt`.
        - Casts resulting tensors to the target `device` and `model_dtype`.
        - Executes `model.generate` within an `autocast` context.
    3. **Output**: Extracts audio from `speech_outputs` or `wav` attribute, converts to CPU/NumPy, and returns a `float32` array.
- **Conditional Branching**:
    - **Hardware Detection**: Switches between `cuda` (float16) and `cpu` (float32).
    - **Voice Discovery**: If the preferred `.pt` file is missing, it attempts to glob the `assets/voices` directory for any available `.pt` file.
    - **Output Extraction**: Checks multiple possible attributes (`speech_outputs`, `wav`, or `audio`) to ensure compatibility with different model output formats.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `copy`, `pathlib`
- **Internal Modules**: 
    - [BaseVoiceModule](/docs/ai/modules/voice/base_module.md)
    - [ai.functions](/docs/ai/functions.md)
- **External Packages**: `torch`, `numpy`, `vibevoice` (Official Microsoft package)