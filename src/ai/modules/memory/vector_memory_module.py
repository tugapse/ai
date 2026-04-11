from typing import Any, Optional
import functions as func
from .vector_memory import VectorMemory

class VectorMemoryModule:
    """
    A module wrapper for the VectorMemory system.
    This allows it to be managed by the ModuleRegistry and initialized
    with session-specific context when it becomes available.
    """
    def __init__(self, db_path: str, **kwargs):
        """
        Initializes the module wrapper. The actual VectorMemory is not created
        until initialize() is called.

        Args:
            db_path (str): Path to the persistent database directory.
            **kwargs: Additional arguments for VectorMemory (weights, etc.).
        """
        self.db_path = db_path
        self.kwargs = kwargs
        self._memory_instance: Optional[VectorMemory] = None

    def initialize(self, session_id: str, connector: Any):
        """
        Initializes the underlying VectorMemory instance with session-specific data.
        This must be called before the memory can be used.
        
        Args:
            session_id (str): The unique ID for the current session.
            connector (Any): The LLMConnector for importance rating and reflection.
        """
        if self._memory_instance:
            func.log("VectorMemoryModule is already initialized.", level="WARN")
            return

        func.log(f"Initializing VectorMemory for session {session_id}...")
        self._memory_instance = VectorMemory(
            session_id=session_id,
            connector=connector,
            db_path=self.db_path,
            **self.kwargs
        )

    def get_instance(self) -> Optional[VectorMemory]:
        """
        Returns the active VectorMemory instance.
        Returns None if the module has not been initialized.
        """
        if not self._memory_instance:
            func.log("Attempted to use VectorMemory before it was initialized.", level="ERROR")
        return self._memory_instance

    def shutdown(self):
        """Handles any cleanup for the vector memory."""
        func.log("Shutting down VectorMemoryModule.")
        self._memory_instance = None