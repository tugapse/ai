import threading
from typing import Any, Optional
import ai.functions as func
from ai.modules.base_module import BaseModule
from ai.core.llms.base_llm import BaseModel
from ai.modules.vector_memory.vector_memory import VectorMemory


class VectorMemoryModule(BaseModule):
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
            **kwargs: Additional arguments for VectorMemory (weights, llm_importance, etc.).
        """
        self.db_path = db_path
        super().__init__(module_name="vector_memory", **kwargs)
        self.kwargs = kwargs
        self._lock = threading.Lock()

    def initialize(self, session_id: str, llm: Optional[BaseModel], scope_key: Optional[str] = None):
        """
        Initializes (or re-targets) the underlying VectorMemory instance.

        Calling it again with the same scope only updates the session id and LLM; a different
        scope (e.g. another workspace) opens that scope's collection.

        Args:
            session_id (str): The unique ID for the current session.
            llm (BaseModel): The LLM instance used for reflection.
            scope_key (str, optional): Key naming the memory collection (see resolve_ltm_scope).
        """
        scope_key = scope_key or session_id
        with self._lock:
            if self._instance is not None and getattr(self._instance, "scope_key", None) == scope_key:
                self._instance.session_id = session_id
                if llm is not None and self._instance.llm is not None:
                    self._instance.llm.llm = llm
                return

            func.log(f"Initializing VectorMemory (scope {scope_key})...")
            try:
                self._instance = VectorMemory(
                    session_id=session_id,
                    llm=llm,
                    db_path=self.db_path,
                    scope_key=scope_key,
                    **self.kwargs
                )
                self._is_initialized = True
                func.log("VectorMemoryModule initialized successfully.")
            except Exception as e:
                func.error(f"VectorMemory could not start: {e}")
                self._instance = None
                self._is_initialized = False

    def get_instance(self) -> Optional[VectorMemory]:
        """
        Returns the active VectorMemory instance, or None if the module has not been initialized.

        Returns:
            Optional[VectorMemory]: The initialized VectorMemory instance or None.
        """
        return self._instance

    def shutdown(self):
        """Handles any cleanup for the vector memory."""
        func.log("Shutting down VectorMemoryModule.")
        self._instance = None
        self._is_initialized = False
