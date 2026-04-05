# Eagerly importing all models here was causing a CUDA context collision.
# PyTorch-based models (HuggingFace, T5) were being loaded even when
# a GGUF model was selected, causing torch to initialize CUDA first.
# The ModelManager now handles the lazy-loading of specific model classes.
