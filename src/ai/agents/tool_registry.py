from typing import Dict, Any
import functions as func

class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register_tool(self, name: str, func_ref: callable):
        self._tools[name] = func_ref
        
    def get_tool_info(self, name: str) -> str:
        if name not in self._tools:
            return f"- {name}: No description available."
        
        doc = self._tools[name].__doc__ or "No description provided."
        indented_doc = "\n  ".join([line.strip() for line in doc.strip().split("\n")])
        return f"- {name}:\n  {indented_doc}"

    def execute_tool(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self._tools:
            error_msg = f"Tool '{name}' does not exist."
            return {"status": "FAILED", "error": error_msg}
    
        try:
            p = params if isinstance(params, dict) else {}
            func.log(f"Calling tool [{name}] with: {p}")
            result = self._tools[name](**p)
            return {"status": "SUCCESS", "output": result}
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}