## 1. Architectural Role
Provides a specialized implementation of `BaseVoiceModule` for real-time text-to-speech synthesis using the Microsoft VibeVoice-Realtime-0.5B model.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `VibeVoiceModule` | Class | Orchestrates model loading, hardware acceleration, voice profile management, and inference. |
| `preload` | Method | Triggers the model loading sequence via `_initialize_model`. |
| `_initialize_model` | Method | Performs hardware detection, voice asset discovery, and loads the processor and model weights. |
| `_recursive_cast` | Method | Recursively migrates tensors and nested structures to the target `device` and `model_dtype`. |
| `_run_inference` | Method | Transforms input text into a NumPy audio array via model generation and autocasting. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Calls `super().__init__` to initialize audio queues and playback at 24kHz.
    2. Sets internal state for `model_id`, `voice_file`, `volume`, and placeholder attributes for `model`, `processor`, `voice_embeddings`, `device`, and `model_dtype`.
- **Data Path**: 
    1. **Input**: `text` (string) passed to `_run_inference`.
    2. **Processing**: 
        - Deep copies `voice_embeddings` into `prompt_cache`.
        - `processor.process_input_with_cached_prompt` converts text + cache into `raw_inputs`.
        - `_recursive_cast` moves `raw_inputs` to GPU/CPU and correct precision.
        - `model.generate` executes inference within a `torch.amp.autocast` context.
    3. **Output**: `audio_tensor` extracted from `output.speech_outputs` (or `wav`/`audio`), converted to CPU, squeezed, and cast to `np.float32` NumPy array.
- **Conditional Branching**:
    - **Hardware Detection**: Selects `cuda` (float16) or `cpu` (float32) based on `torch.cuda.is_available()`.
    - **Voice Discovery**: 
        - If `voice_file` exists in `assets/voices`, load it.
        - If `voice_file` is missing, attempts to glob the first available `.pt` file in `assets/voices`.
        - If no `.pt` files exist, logs a warning.
    - **Output Extraction**: Checks for `speech_outputs` attribute; falls back to `wav` or `audio` attributes if unavailable.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `copy`, `pathlib.Path`
- **Internal Modules**: `modules.voice.base_module.BaseVoiceModule`, `functions`
- **External Packages**: `torch`, `numpy`, `vibevoice` (specifically `VibeVoiceStreamingForConditionalGenerationInference` and `VibeVoiceStreamingProcessor`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `sample_rate`: 24000
    - `cfg_scale`: 1.5
    - `ddpm_inference_steps`: 5
    - `model_id`: "microsoft/VibeVoice-Realtime-0.5B"
- **Environment Lookups**: 
    - Hardware availability via `torch.cuda.is_available()`.
    - File system traversal via `Path(__file__).resolve()` to locate `assets/voices`.