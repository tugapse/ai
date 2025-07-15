from enum import Enum

class EngineType(Enum):
    """
    Enum to define the different types of LLM engines supported.
    """
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    GGUF = "gguf"                 # GGUF quantized models (typically run with llama.cpp bindings)
    

class ModelType(Enum):
    """
    Defines the architectural types of language models supported by the application.
    """
    CAUSAL_LM = "causal_lm"       # Models like GPT, Llama (decoder-only)
    SEQ2SEQ_LM = "seq2seq_lm"     # Models like T5, BART (encoder-decoder)
    OLLAMA = "ollama"             # Models served via Ollama
    GGUF = "gguf"                 # GGUF quantized models (typically run with llama.cpp bindings)

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.name

class InferenceBackend(Enum):
    GPU_CUDA = "cuda"
    GPU_AMD = "amd"
    CPU = "cpu"
    