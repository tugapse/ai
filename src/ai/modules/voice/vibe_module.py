import os
import torch
import copy
import numpy as np
from modules.voice.base_module import BaseVoiceModule

class VibeVoiceModule(BaseVoiceModule):
    def __init__(self, model_id="microsoft/VibeVoice-Realtime-0.5B", voice_file="en-Carter_man.pt", **kwargs):
        super().__init__(sample_rate=24000, **kwargs)
        self.model_id = model_id
        self.voice_file = voice_file
        self.model = None
        self.processor = None
        self.voice_embeddings = None
        self.model_dtype = None
        self.device = None

    def _initialize_model(self):
        from vibevoice import VibeVoiceStreamingForConditionalGenerationInference, VibeVoiceStreamingProcessor
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_dtype = torch.float16 if "cuda" in self.device else torch.float32
        
        # Robust Path Discovery
        current_file_path = os.path.dirname(os.path.abspath(__file__))
        voices_dir = None
        for i in range(4):
            test_path = os.path.abspath(os.path.join(current_file_path, *(['..'] * i), "voices"))
            if os.path.exists(test_path):
                voices_dir = test_path
                break
        
        if not voices_dir:
            raise FileNotFoundError("[!] VibeVoice: Could not locate 'voices' directory.")

        available_voices = [f for f in os.listdir(voices_dir) if f.endswith('.pt')]
        selected_voice = self.voice_file if self.voice_file in available_voices else available_voices[0]
        voice_path = os.path.join(voices_dir, selected_voice)

        # LOAD: Keep the original object type (ModelOutput)
        raw_embeddings = torch.load(voice_path, map_location=self.device, weights_only=False)
        self.voice_embeddings = self._recursive_cast(raw_embeddings)
        
        self.processor = VibeVoiceStreamingProcessor.from_pretrained(self.model_id)
        self.model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
            self.model_id, torch_dtype=self.model_dtype
        ).to(self.device)
        
        if hasattr(self.model, "set_ddpm_inference_steps"):
            self.model.set_ddpm_inference_steps(num_steps=5)

    def _recursive_cast(self, obj):
        """
        CRITICAL FIX: This now modifies objects in-place or preserves their class type
        to ensure attribute access (like .past_key_values) doesn't break.
        """
        if isinstance(obj, torch.Tensor):
            if obj.is_floating_point():
                return obj.to(device=self.device, dtype=self.model_dtype)
            return obj.to(device=self.device)
        
        elif isinstance(obj, dict):
            # If it's a special dict (like ModelOutput), we must preserve its class
            for k, v in obj.items():
                obj[k] = self._recursive_cast(v)
            return obj
            
        elif isinstance(obj, list):
            for i in range(len(obj)):
                obj[i] = self._recursive_cast(obj[i])
            return obj
            
        elif hasattr(obj, "__dict__"):
            # For custom objects that aren't dicts but have attributes
            for k, v in vars(obj).items():
                setattr(obj, k, self._recursive_cast(v))
            return obj
            
        return obj

    def _run_inference(self, text) -> np.ndarray:
        # Use the already-cast embeddings as the prompt cache
        # We use deepcopy so the model doesn't modify our master voice file in VRAM
        prompt_cache = copy.deepcopy(self.voice_embeddings)
        
        raw_inputs = self.processor.process_input_with_cached_prompt(
            text=text, 
            cached_prompt=prompt_cache, 
            padding=True, 
            return_tensors="pt"
        )
        
        inputs = self._recursive_cast(raw_inputs)
        tokenizer = getattr(self.processor, "tokenizer", self.processor)
        
        with torch.no_grad():
            autocast_device = "cuda" if "cuda" in self.device else "cpu"
            with torch.amp.autocast(device_type=autocast_device, dtype=self.model_dtype):
                # VibeVoice generate needs all_prefilled_outputs to be the exact object type
                output = self.model.generate(
                    **inputs, 
                    tokenizer=tokenizer, 
                    cfg_scale=1.5, 
                    all_prefilled_outputs=prompt_cache
                )
        
        if hasattr(output, 'speech_outputs') and output.speech_outputs:
            audio_tensor = torch.cat(output.speech_outputs, dim=-1) if len(output.speech_outputs) > 1 else output.speech_outputs[0]
        else:
            audio_tensor = output.wav if hasattr(output, 'wav') else output.audio
            
        return audio_tensor.cpu().numpy().squeeze().astype(np.float32)