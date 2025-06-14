from enum import Enum

class EngineType(Enum):
    """
    Enum to define the different types of LLM engines supported.
    """
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"

class ModelType(Enum):
    """
    Enum to define the different types of LLM models based on their architecture.
    """
    CAUSAL_LM = "causal_lm"
    SEQ2SEQ_LM = "seq2seq_lm"
    OLLAMA_MODEL = "ollama" # Can be used for specific Ollama model types if needed
