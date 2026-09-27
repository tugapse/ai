import sys
import torch
import requests.exceptions
from huggingface_hub.errors import RepositoryNotFoundError, GatedRepoError
import ai.functions as func

class HFModelLoaderMixin:
    """Isolates model/tokenizer initialization and hardware-specific configurations."""
    
    def _load_llm_params(self, **kwargs):
        super()._load_llm_params(kwargs=kwargs)
        self.init_pytorch_cuda()
        self.torch_lib = torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        func.log(f"Preparing to load model: {self.model_name}...")
        load_kwargs = {"trust_remote_code": True}
        
        tokenizer_kwargs = {"trust_remote_code": True}
        overrides = self.options.get("tokenizer_kwargs", {})
        if overrides:
            tokenizer_kwargs.update(overrides)
            func.debug(f"Applied tokenizer_kwargs from config: {overrides}")

        quant_method = self.quantization_method.lower()
        quantization_config = None

        if quant_method == "awq":
            func.log("AWQ method selected from config. Expecting a pre-quantized AWQ model repository.")
        else:
            if self.quantization_bits in [4, 8]:
                try:
                    import bitsandbytes as bnb  
                    from transformers import BitsAndBytesConfig

                    if self.quantization_bits == 4:
                        quantization_config = BitsAndBytesConfig(
                            load_in_4bit=True,
                            bnb_4bit_quant_type="nf4", 
                            bnb_4bit_compute_dtype=torch.bfloat16,
                            bnb_4bit_use_double_quant=True,
                            llm_int8_enable_fp32_cpu_offload=True
                        )
                        func.log("Configured for 4-bit quantization using BitsAndBytesConfig.")
                    elif self.quantization_bits == 8:
                        quantization_config = BitsAndBytesConfig(
                            load_in_8bit=True, 
                            llm_int8_enable_fp32_cpu_offload=True
                        )
                        func.log("Configured for 8-bit quantization using BitsAndBytesConfig.")

                except ImportError:
                    func.log("WARNING: bitsandbytes not found. Falling back to non-quantized loading.")
                    self.quantization_bits = 0
                except Exception as e:
                    func.log(f"ERROR: Could not create BitsAndBytesConfig for {self.quantization_bits}-bit quantization: {e}. Falling back to non-quantized loading.")
                    self.quantization_bits = 0

        if quantization_config:
            load_kwargs["quantization_config"] = quantization_config
            if self.is_gpu_available():
                load_kwargs["device_map"] = self.device_map
            func.log(f"Attempting to load model: {self.model_name} with {self.quantization_bits}-bit BNB config.")
        else:
            if quant_method == "awq":
                func.log("Loading AWQ model natively without BNB config.")
            else:
                func.log("Loading model without quantization.")
            if self.is_gpu_available():
                load_kwargs["torch_dtype"] = torch.bfloat16
                load_kwargs["device_map"] = self.device_map

        try:
            func.debug(f"Checking local cache for model {self.model_name}...")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                local_files_only=True,
                **tokenizer_kwargs
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            if self.is_gpu_available():
                torch.cuda.empty_cache()

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                local_files_only=True,
                **load_kwargs
            )
            func.log(f"Found model in local cache. Loaded: {self.model_name}")

        except Exception:
            func.log(f"Model not found locally (or cache is incomplete). Downloading from HuggingFace...")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                local_files_only=False,
                **tokenizer_kwargs
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                local_files_only=False,
                **load_kwargs
            )
            func.log(f"Successfully downloaded and loaded model: {self.model_name}")