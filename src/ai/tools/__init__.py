"""
Agent tools package: the @tool marker, the ToolCategory contract and the registry.
"""

from ai.tools.base import tool
from ai.tools.category import ToolCategory, ToolCategoryError

__all__ = ["tool", "ToolCategory", "ToolCategoryError"]
