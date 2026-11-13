class SessionError(Exception):
    """Base exception for session handling."""
    pass
class SessionNotFoundError(SessionError):
    """Raised when a session file does not exist."""
    pass
class InvalidPathError(SessionError):
    """Raised when a provided path would escape the root session directory."""
    pass
class SessionAccessError(SessionError):
    """Raised on generic IO errors while handling sessions."""
    pass

class ModelError(Exception):
    """Base exception for model selection on the server."""
    pass
class ModelNotFoundError(ModelError):
    """Raised when a requested model has no config file on the server."""
    pass
class ModelLoadError(ModelError):
    """Raised when a model config exists but the engine failed to load it."""
    pass
class ModelBusyError(ModelError):
    """Raised when a model swap is refused because the loaded model is still in use."""
    pass
