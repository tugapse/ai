"""
What an agent sees of its tools: categories until it opens them.

The prompt lists each category an agent may use (name + one-line description). The agent calls
``open_tools`` to unlock one or more categories; from its next step on, those categories' full
tool descriptions are in its prompt and it calls the tools by name. Tools registered outside any
category are always shown in full. Calling a tool of a closed category still works (the pipeline
allow-list is the permission gate): it simply opens that category.
"""

from typing import Any, Dict, Iterable, List, Optional, Tuple

OPEN_TOOLS = "open_tools"

OPEN_TOOLS_DOC = """- open_tools:
  Unlocks one or more tool categories. From your next step, their tools are listed in full under
  OPEN TOOLS and you call them by name. Open every category you expect to need in one call.

  Args:
      category (string): A category name from TOOL CATEGORIES. Repeat the tag to open several:
          <category>filesystem</category><category>knowledge</category>"""


def requested_categories(params: Dict[str, Any]) -> List[str]:
    """Category names from open_tools parameters: repeated tags, a list or a comma-separated string."""
    raw = None
    for key in ("category", "categories", "name"):
        if params.get(key):
            raw = params[key]
            break
    values = raw if isinstance(raw, (list, tuple)) else [raw]
    names: List[str] = []
    for value in values:
        for part in str(value or "").replace(";", ",").split(","):
            name = part.strip().strip("'\"").lower()
            if name and name not in names:
                names.append(name)
    return names


class ToolCatalog:
    """Groups an agent's allowed tools by category and renders the AVAILABLE TOOLS block."""

    def __init__(self, registry: Any):
        self.registry = registry

    def _category_of(self, tool_name: str) -> Optional[str]:
        lookup = getattr(self.registry, "category_of", None)
        return lookup(tool_name) if callable(lookup) else None

    def group(self, tool_names: Iterable[str]) -> Tuple[Dict[str, List[str]], List[str]]:
        """({category: [tools]}, [tools outside any category]), keeping the given order."""
        categories: Dict[str, List[str]] = {}
        loose: List[str] = []
        for name in tool_names:
            category = self._category_of(name)
            if category:
                categories.setdefault(category, []).append(name)
            else:
                loose.append(name)
        return categories, loose

    def category_for(self, tool_name: str) -> Optional[str]:
        return self._category_of(tool_name)

    def _info(self, name: str) -> str:
        return self.registry.get_tool_info(name)

    def describe(self, tool_names: Iterable[str], open_categories: Iterable[str]) -> str:
        """The AVAILABLE TOOLS text: closed categories as one line each, open ones in full."""
        categories, loose = self.group(tool_names)
        opened = [c for c in open_categories if c in categories]
        closed = [c for c in categories if c not in opened]
        if not categories:
            return "\n".join(self._info(name) for name in loose)

        lines: List[str] = []
        if closed:
            lines.append("TOOL CATEGORIES (closed: open them with open_tools to see and use their tools):")
            for name in closed:
                category = self.registry.get_category(name)
                lines.append(f"- {name}: {getattr(category, 'description', '') or ''}".rstrip())
        else:
            lines.append("TOOL CATEGORIES: all open.")

        lines.append("\nOPEN TOOLS:" if opened or loose else "\nOPEN TOOLS: none yet.")
        lines.append(OPEN_TOOLS_DOC)
        lines.extend(self._info(name) for name in loose)
        for name in opened:
            lines.append(f"# category: {name}")
            lines.extend(self._info(tool) for tool in categories[name])
            category = self.registry.get_category(name)
            extra = category.describe_open() if category is not None else None
            if extra:
                lines.append("  " + str(extra).replace("\n", "\n  "))
        return "\n".join(lines)

    def open(self, params: Dict[str, Any], tool_names: Iterable[str], open_categories: List[str]) -> Dict[str, Any]:
        """
        Runs open_tools for an agent: adds the requested categories to ``open_categories`` (in place).

        Returns:
            The tool result shown to the agent.
        """
        categories, _ = self.group(tool_names)
        requested = requested_categories(params)
        if not requested:
            return {"status": "FAILED", "error": "Parameter 'category' is required.",
                    "categories": list(categories)}

        opened, already, unknown = [], [], []
        for name in requested:
            if name not in categories:
                unknown.append(name)
            elif name in open_categories:
                already.append(name)
            else:
                open_categories.append(name)
                opened.append(name)

        result: Dict[str, Any] = {"status": "SUCCESS" if opened or already else "FAILED"}
        if opened:
            result["opened"] = {name: categories[name] for name in opened}
            result["note"] = "Their full descriptions are now under OPEN TOOLS. Call them by name in your next step."
        if already:
            result["already_open"] = already
        if unknown:
            result["unknown"] = unknown
            result["available_categories"] = list(categories)
            if not (opened or already):
                result["error"] = f"No such category: {', '.join(unknown)}."
        return result
