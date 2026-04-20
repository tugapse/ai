import os
import torch
import copy
import numpy as np
from modules.voice.base_module import BaseVoiceModule
import functions as func

class VibeVoiceModule(BaseVoiceModule):
    """
    VibeVoice-Realtime-0.5B implementation.
    Auto-detects hardware (CUDA/CPU) and uses the official Microsoft package.
    """
    def __init__(self, model_id="microsoft/VibeVoice-Realtime-0.5B", voice_file="pt-Spk1_man", **kwargs):
        # Initialize the base class (starts audio queues and playback threads)
        super().__init__(sample_rate=24000, **kwargs)
        
        self.model_id = model_id
        self.voice_file = voice_file
        
        # Runtime hardware state
        self.model = None
        self.processor = None
        self.voice_embeddings = None
        self.device = None
        self.model_dtype = None

    def preload(self):
        """
        This is the method the ModuleRegistry calls.
        It triggers the actual model loading sequence.
        """
        func.log("VibeVoice: Preloading model components...")
        self._initialize_model()

    def _initialize_model(self):
        """
        Auto-detects hardware and loads the VibeVoice weights using the local package.
        """
        from vibevoice import VibeVoiceStreamingForConditionalGenerationInference, VibeVoiceStreamingProcessor # type: ignore
        
        # 1. Hardware Detection
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_dtype = torch.float16 if "cuda" in self.device else torch.float32
        
        func.log(f"VibeVoice: Initializing on {self.device.upper()} ({self.model_dtype})")

        # 2. Path Discovery for Voice Files
        current_file_path = os.path.dirname(os.path.abspath(__file__))
        voices_dir = None
        for i in range(4):
            test_path = os.path.abspath(os.path.join(current_file_path, *(['..'] * i), "voices"))
            if os.path.exists(test_path):
                voices_dir = test_path
                break
        
        if not voices_dir:
            func.log("VibeVoice: WARNING - Could not locate 'voices' directory.", level="WARN")
            voice_path = None
        else:
            voice_path = os.path.join(voices_dir, self.voice_file)
            if not os.path.exists(voice_path):
                # Fallback to first available voice if preferred one is missing
                available = [f for f in os.listdir(voices_dir) if f.endswith('.pt')]
                if available:
                    voice_path = os.path.join(voices_dir, available[0])

        # 3. Load Voice Profile
        if voice_path and os.path.exists(voice_path):
            func.log(f"VibeVoice: Loading voice profile: {os.path.basename(voice_path)}")
            raw_embeddings = torch.load(voice_path, map_location=self.device, weights_only=False)
            self.voice_embeddings = self._recursive_cast(raw_embeddings)
        
        # 4. Load Processor
        self.processor = VibeVoiceStreamingProcessor.from_pretrained(self.model_id)
        
        func.log("VibeVoice: Loading model weights (this may take a moment)...")
        
        # 5. Load Model (Using the fixed 'torch_dtype' argument)
        self.model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
            self.model_id, 
            torch_dtype=self.model_dtype
        ).to(self.device)
        
        if hasattr(self.model, "set_ddpm_inference_steps"):
            self.model.set_ddpm_inference_steps(num_steps=5)
            
        func.log("VibeVoice: Model ready.")

    def _recursive_cast(self, obj):
        """Moves tensors and dicts to the selected device/dtype."""
        if isinstance(obj, torch.Tensor):
            return obj.to(device=self.device, dtype=self.model_dtype if obj.is_floating_point() else None)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                obj[k] = self._recursive_cast(v)
            return obj
        elif isinstance(obj, list):
            for i in range(len(obj)):
                obj[i] = self._recursive_cast(obj[i])
            return obj
        elif hasattr(obj, "__dict__"):
            for k, v in vars(obj).items():
                setattr(obj, k, self._recursive_cast(v))
            return obj
        return obj

    def _run_inference(self, text: str) -> np.ndarray:
        """
        Converts text tokens to audio. This is the heart of the engine.
        """
        if not self.model or not text.strip():
            return np.zeros(1, dtype=np.float32)

        prompt_cache = copy.deepcopy(self.voice_embeddings)
        
        raw_inputs = self.processor.process_input_with_cached_prompt(
            text=text, 
            cached_prompt=prompt_cache, 
            padding=True, 
            return_tensors="pt"
        )
        
        inputs = self._recursive_cast(raw_inputs)
        
        with torch.no_grad():
            autocast_dev = "cuda" if "cuda" in str(self.device) else "cpu"
            with torch.amp.autocast(device_type=autocast_dev, dtype=self.model_dtype):
                output = self.model.generate(
                    **inputs, 
                    tokenizer=self.processor.tokenizer, 
                    cfg_scale=1.5, 
                    all_prefilled_outputs=prompt_cache
                )
        
        if hasattr(output, 'speech_outputs') and output.speech_outputs:
            audio_tensor = torch.cat(output.speech_outputs, dim=-1) if len(output.speech_outputs) > 1 else output.speech_outputs[0]
        else:
            audio_tensor = output.wav if hasattr(output, 'wav') else output.audio
            
        # Convert to numpy and return to BaseVoiceModule for playback
        audio_data = audio_tensor.cpu().numpy().squeeze().astype(np.float32)
        
        # Diagnostic Log
        max_amp = np.max(np.abs(audio_data)) if len(audio_data) > 0 else 0
        func.debug(f"VibeVoice: Audio generated (Peak Amplitude: {max_amp:.4f})", level="DEBUG")
        
        return audio_data