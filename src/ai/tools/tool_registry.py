from typing import Dict, Any, Callable
import functions as func

class ToolRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Initialize attributes on the instance the first time it's created.
            cls._instance._tools: Dict[str, Callable] = {}
        return cls._instance

    def __init__(self):
        # This method is called on every "instantiation", but since we return
        # a singleton, we don't re-initialize here.
        pass

    def register_tool(self, name: str, func_ref: Callable):
        self._tools[name] = func_ref
        func.debug(f"Tool registered: {name}")
        
    def get_tool_info(self, name: str) -> str:
        if name not in self._tools:
            return f"- {name}: No description available."
        
        doc = self._tools[name].__doc__ or "No description provided."
        indented_doc = doc.strip().replace("\n", "\n  ")
        return f"- {name}:\n  {indented_doc}"

    def execute_tool(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self._tools:
            return {"status": "FAILED", "error": f"Tool '{name}' does not exist."}
    
        try:
            p = params if isinstance(params, dict) else {}
            func.log(f"Calling tool [{name}] with: {p}")
            return self._tools[name](**p)
        except Exception as e:
            func.debug(f"Tool execution failed: {e}")
            return {"status": "FAILED", "error": str(e)}
    
    def get_all_tools(self) -> dict:
        """Returns the full dictionary of registered tool functions."""
        return self._tools  # or self._tools, whichever dict holds your functions