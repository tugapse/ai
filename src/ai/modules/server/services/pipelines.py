"""
Pipeline files for the web editor: read, validate, save, create and delete.

A pipeline is ``<name>.json`` in the user or the system pipelines folder (the user one wins, as
when a run loads it). Edits go back to the file they were read from; new pipelines go to the
user folder. Unknown keys are kept as they are.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from ai.services.directory_manager import DirectoryManager

NAME_RE = re.compile(r"[A-Za-z0-9_-]+")
SPECIAL_TARGETS = {"USER", "STOP", "DONE"}


class PipelineError(Exception):
    """``status`` is the HTTP code; ``detail`` a message or a list of validation messages."""

    def __init__(self, status: int, detail: Any):
        super().__init__(str(detail))
        self.status, self.detail = status, detail


def _folders() -> List[Tuple[str, str]]:
    directory = DirectoryManager()
    return [("user", directory.get_user_pipelines_directory()),
            ("system", directory.get_system_pipelines_directory())]


def _check_name(name: str) -> str:
    if not NAME_RE.fullmatch(name or ""):
        raise PipelineError(400, "A pipeline name may only use letters, digits, '_' and '-'.")
    return name


def locate(name: str) -> Optional[Tuple[str, str]]:
    """``(source, path)`` of an existing pipeline, user folder first, or None."""
    _check_name(name)
    for source, folder in _folders():
        path = os.path.join(folder, f"{name}.json")
        if os.path.isfile(path):
            return source, path
    return None


def read(name: str) -> dict:
    found = locate(name)
    if found is None:
        raise PipelineError(404, f"Pipeline '{name}' not found.")
    source, path = found
    try:
        with open(path, encoding="utf-8") as f:
            content = json.load(f)
    except (OSError, ValueError) as e:
        raise PipelineError(500, f"Pipeline '{name}' can't be read: {e}")
    return {"name": name, "source": source, "content": content}


def validate(content: Any, known_tools: Optional[set]) -> List[str]:
    """
    Problems that would stop the pipeline from running.

    Raises:
        PipelineError: 400 with the list of problems.

    Returns:
        Warnings: tools no active module provides (they may come from a module that is off).
    """
    errors: List[str] = []
    warnings: List[str] = []
    if not isinstance(content, dict):
        raise PipelineError(400, ["The pipeline must be a JSON object."])
    agents = content.get("agents")
    if not isinstance(agents, dict) or not agents:
        raise PipelineError(400, ["'agents' must be a non-empty object."])

    if content.get("entry_point") not in agents:
        errors.append(f"'entry_point' must be one of the agents ({', '.join(agents)}).")
    if "max_iterations" in content:
        value = content["max_iterations"]
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            errors.append("'max_iterations' must be a positive integer.")
    for key in ("name", "description"):
        if key in content and not isinstance(content[key], str):
            errors.append(f"'{key}' must be text.")

    prompts_dir = os.path.realpath(DirectoryManager().get_system_prompts_templates_directory())
    targets = set(agents) | SPECIAL_TARGETS
    for agent_name, agent in agents.items():
        where = f"Agent '{agent_name}'"
        if not NAME_RE.fullmatch(agent_name):
            errors.append(f"{where}: the name may only use letters, digits, '_' and '-'.")
        if not isinstance(agent, dict):
            errors.append(f"{where}: must be an object.")
            continue

        prompt_file = agent.get("prompt_file")
        if not isinstance(prompt_file, str) or not prompt_file.strip():
            errors.append(f"{where}: 'prompt_file' is required (e.g. agents/default.md).")
        elif os.path.isabs(prompt_file) or ".." in prompt_file.replace("\\", "/").split("/"):
            errors.append(f"{where}: 'prompt_file' must be a path inside system-prompt/ (e.g. agents/default.md).")
        elif not os.path.isfile(os.path.join(prompts_dir, prompt_file)):
            errors.append(f"{where}: prompt file 'system-prompt/{prompt_file}' doesn't exist.")

        tools = agent.get("tools", [])
        if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
            errors.append(f"{where}: 'tools' must be a list of tool names.")
        elif known_tools is not None:
            unknown = [t for t in tools if t not in known_tools]
            if unknown:
                warnings.append(f"{where}: no active module provides {', '.join(unknown)}.")

        allowed = agent.get("allowed_targets")
        if allowed is not None:
            if not isinstance(allowed, list) or not all(isinstance(t, str) for t in allowed):
                errors.append(f"{where}: 'allowed_targets' must be a list of names.")
            else:
                bad = [t for t in allowed if t not in targets]
                if bad:
                    errors.append(f"{where}: unknown targets {', '.join(bad)} (use agent names, USER or STOP).")

    if errors:
        raise PipelineError(400, errors)
    return warnings


def _write(path: str, content: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)  # never leaves a half-written pipeline


def save(name: str, content: Any, known_tools: Optional[set]) -> dict:
    """Overwrites an existing pipeline in the folder it was read from."""
    found = locate(name)
    if found is None:
        raise PipelineError(404, f"Pipeline '{name}' not found.")
    warnings = validate(content, known_tools)
    source, path = found
    _write(path, content)
    return {"name": name, "source": source, "warnings": warnings}


def create(name: str, content: Any, known_tools: Optional[set]) -> dict:
    """Creates a pipeline in the user folder; 409 when one with that name exists anywhere."""
    if locate(name) is not None:
        raise PipelineError(409, f"Pipeline '{name}' already exists.")
    warnings = validate(content, known_tools)
    folder = dict(_folders())["user"]
    _write(os.path.join(folder, f"{name}.json"), content)
    return {"name": name, "source": "user", "warnings": warnings}


def delete(name: str) -> dict:
    """Deletes the pipeline file a run would use (a system one may then show through)."""
    if name == "default":
        raise PipelineError(409, "The default pipeline can't be deleted.")
    found = locate(name)
    if found is None:
        raise PipelineError(404, f"Pipeline '{name}' not found.")
    source, path = found
    os.remove(path)
    return {"name": name, "source": source}


def list_tools(modules, hil_tools: List[str], totp_tools: set) -> List[dict]:
    """Tools a pipeline can give its agents (active modules and user tools), sorted by name."""
    from ai.tools.tool_loader import load_and_register_user_tools
    from ai.tools.tool_registry import ToolRegistry

    found: Dict[str, Any] = {}
    if modules is not None and hasattr(modules, "tool_functions"):
        found.update(modules.tool_functions())
    registry = ToolRegistry()
    load_and_register_user_tools(registry, DirectoryManager().get_user_tools_directory())
    for name, ref in registry.get_all_tools().items():
        found.setdefault(name, ref)

    tools = []
    for name in sorted(found):
        try:
            description = ToolRegistry.parse_docstring_to_schema(name, found[name]).get("description", "")
        except Exception:
            description = ""
        tools.append({"name": name, "description": description,
                      "needs_permission": name in hil_tools, "needs_totp": name in totp_tools})
    return tools
