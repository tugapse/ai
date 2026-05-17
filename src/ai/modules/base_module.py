from typing import Any, Optional
import ai.functions as func

class BaseModule:
    """
    The fundamental blueprint for all JARVIS modules.
    Enforces a consistent lifecycle for pluggable components.
    """
    def __init__(self, module_name: str, **kwargs):
        self.module_name = module_name
        self.kwargs = kwargs
        self._instance: Optional[Any] = None
        self._is_initialized: bool = False

    def initialize(self, *args, **kwargs):
        """
        Setup the internal logic/engine. 
        To be overridden by child classes.
        """
        if self._is_initialized:
            func.log(f"Module '{self.module_name}' is already initialized.", level="WARN")
            return
        
        func.log(f"Initializing Module: {self.module_name}")
        # Concrete implementation happens in subclasses
        self._is_initialized = True

    def get_instance(self) -> Any:
        """
        Returns the active instance/engine managed by this module.
        """
        if not self._is_initialized:
            func.error(f"Attempted to access '{self.module_name}' before initialization.", level="ERROR")
        return self._instance

    @property
    def is_active(self) -> bool:
        """Returns True if the module is initialized and has an active instance."""
        return self._is_initialized and self._instance is not None

    def shutdown(self):
        """
        Standard cleanup logic. 
        Resets instance and initialization state.
        """
        func.log(f"Shutting down Module: {self.module_name}")
        self._instance = None
        self._is_initialized = False