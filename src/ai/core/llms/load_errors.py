"""Errors raised while loading a local model, kept free of engine imports."""

from typing import Optional


class GpuMemoryError(RuntimeError):
    """
    The model did not fit in the free GPU memory (the engine's GPU allocation failed).

    Attributes:
        model_path: The model file that failed to load.
        n_gpu_layers: The layer offload that was requested (-1 = all).
        log_tail: The engine's last log lines, for diagnostics.
    """

    def __init__(self, message: str, model_path: str = "", n_gpu_layers: Optional[int] = None, log_tail: str = ""):
        super().__init__(message)
        self.model_path = model_path
        self.n_gpu_layers = n_gpu_layers
        self.log_tail = log_tail
