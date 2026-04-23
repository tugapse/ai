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