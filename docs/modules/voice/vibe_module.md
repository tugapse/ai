## 1. Architectural Role
Implements a real-time text-to-speech engine using the `VibeVoice-Realtime-0.5B` model, handling hardware-accelerated inference and voice profile management.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `VibeVoiceModule` | Class | Inherits `BaseVoiceModule` to manage the lifecycle and execution of the VibeVoice TTS model. |
| `preload` | Method | Triggered by the Registry to initiate the `_initialize_model` sequence. |
| `_initialize_model` | Method | Handles hardware detection, voice file path discovery, and loading of model weights/processors. |
| `_recursive_cast` | Method | Recursively casts tensors and data structures to the target `device` and `model_dtype`. |
| `_run_inference` | Method | Transforms input text into a numpy audio array via the model's generation pipeline. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. `__init__` sets default `model_id` and `voice_file`, initializes `BaseVoiceModule` (sample rate 24000), and nullifies runtime state (`model`, `processor`, `voice_embeddings`, `device`, `model_dtype`).
- **Data Path**: 
    1. **Input**: `text` string passed to `_run_inference`.
    2. **Preprocessing**: `processor.process_input_with_cached_prompt` combines text with a deep copy of `voice_embeddings`.
    3. **Casting**: `_recursive_cast` ensures inputs match the model's hardware/precision.
    4. **Inference**: `model.generate` executes within a `torch.amp.autocast` block using `cfg_scale=1.5`.
    5. **Post-processing**: `speech_outputs` or `wav`/`audio` attributes are concatenated and converted to a `np.float32` numpy array.
    6. **Output**: Returns `audio_data` to `BaseVoiceModule` for playback.
- **Conditional Branching**:
    - **Hardware Selection**: Sets `cuda` and `float16` if `torch.cuda.is_available()`, otherwise `cpu` and `float32`.
    - **Voice Discovery**: Iteratively searches up to 4 directory levels for a `/voices` folder; falls back to the first available `.pt` file if the specified `voice_file` is missing.
    - **Output Extraction**: Checks for `speech_outputs` first, then falls back to `wav`, then `audio`.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `copy`
- **Internal Modules**: `modules.voice.base_module.BaseVoiceModule`, `functions` (aliased as `func`)
- **External Packages**: `torch`, `numpy`, `vibevoice` (`VibeVoiceStreamingForConditionalGenerationInference`, `VibeVoiceStreamingProcessor`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `sample_rate`: 24000
    - `model_id`: "microsoft/VibeVoice-Realtime-0.5B"
    - `voice_file`: "en-Davis_man.pt"
    - `num_steps`: 5 (DDPM inference steps)
    - `cfg_scale`: 1.5