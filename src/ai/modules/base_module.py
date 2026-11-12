from typing import Any, Optional
import ai.functions as func

class ModuleTools:
    """
    A simple container for module-specific tools.
    Each module can define its own set of tools and expose them via this class.
    """
    def __init__(self):
        """Initializes the ModuleTools container with an empty dictionary for tools."""
        self._tools = {}

    def register_tool(self, name: str, func: Any):
        """
        Registers a tool with a given name.

        :param name: The unique name under which the tool will be registered.
        :param func: The callable function or object to be registered as a tool.
        """
        self._tools[name] = func

    def get_tools(self) -> dict:
        """
        Returns the registered tools as a dictionary.

        :return: A dictionary containing all registered tools.
        """
        return self._tools


class BaseModule:
    """
    The fundamental blueprint for all JARVIS modules.
    Enforces a consistent lifecycle for pluggable components.
    """
    def __init__(self, module_name: str, **kwargs):
        """
        Initializes the BaseModule.

        :param module_name: A unique string identifier for this module.
        :param kwargs: Additional keyword arguments passed to the module upon creation.
        """
        self.module_name = module_name
        self.kwargs = kwargs
        self._instance: Optional[Any] = None
        self._is_initialized: bool = False
        self.tools = ModuleTools()  # Placeholder for module-specific tools

    def initialize(self, *args, **kwargs):
        """
        Setup the internal logic/engine. 
        To be overridden by child classes.

        If the module is already initialized, a warning is logged and the method returns.
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

        :raises Exception: If the module has not been initialized, an error is logged.
        :return: The active instance of the module's engine.
        """
        if not self._is_initialized:
            func.error(f"Attempted to access '{self.module_name}' before initialization.", level="ERROR")
        return self._instance

    @property
    def is_active(self) -> bool:
        """
        Returns True if the module is initialized and has an active instance.

        :return: Boolean indicating the active state of the module.
        """
        return self._is_initialized and self._instance is not None

    def shutdown(self):
        """
        Standard cleanup logic. 
        Resets instance and initialization state.
        """
        func.log(f"Shutting down Module: {self.module_name}")
        self._instance = None
        self._is_initialized = False

class ToolModule(BaseModule):
    """
    A module whose only job is to expose agent tools (``@tool`` functions).

    Loaded by the ModuleRegistry like any other module and enabled/disabled with
    ``<MODULE_NAME>_ENABLED`` in config.json. Its tools are collected by the agent
    orchestrator and the chat program through ``get_instance().tools``.
    """

    def __init__(self, module_name: str, tool_functions, description: str = "", **kwargs):
        super().__init__(module_name, **kwargs)
        self.description = description
        self._tool_functions = list(tool_functions)

    def initialize(self, *args, **kwargs):
        if self._is_initialized:
            return
        for fn in self._tool_functions:
            self.tools.register_tool(fn.__name__, fn)
        self._instance = self
        self._is_initialized = True
        func.debug(f"ToolModule '{self.module_name}': {len(self._tool_functions)} tools ({', '.join(self.tool_names)})")

    def get_instance(self):
        if not self._is_initialized:
            self.initialize()
        return self._instance

    @property
    def tool_names(self):
        return [fn.__name__ for fn in self._tool_functions]

    def shutdown(self):
        self.tools = ModuleTools()
        super().shutdown()
