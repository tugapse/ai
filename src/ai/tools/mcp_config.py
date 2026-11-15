"""
MCP server configuration: the shipped ``system/config/mcp_config.json`` merged with the user's
``user/config/mcp_config.json`` (by server name, user wins), and turning servers on or off.

Shipped servers start disabled. They are turned on per user — ``ai mcp enable NAME`` or the agent
tool ``enable_mcp_server`` — which writes only ``{"NAME": {"enabled": true}}`` to the user file, so
the rest of the shipped definition still comes from the system file.
"""
import json
import os
from typing import Any, Dict, List, Optional

CONFIG_NAME = "mcp_config.json"


def config_paths(directory=None) -> List[str]:
    """[system file, user file], in merge order."""
    if directory is None:
        from ai.services.directory_manager import DirectoryManager
        directory = DirectoryManager()
    return [os.path.join(directory.get_system_config_dir(), CONFIG_NAME),
            os.path.join(directory.get_user_config_directory(), CONFIG_NAME)]


def _read_servers(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f) or {}
    servers = data.get("mcpServers", {}) or {}
    return {name: details for name, details in servers.items() if isinstance(details, dict)}


def merge(paths: List[str], on_error=None) -> Dict[str, Dict[str, Any]]:
    """Servers of every file, merged by name (later files win, key by key)."""
    merged: Dict[str, Dict[str, Any]] = {}
    for path in paths:
        try:
            servers = _read_servers(path)
        except Exception as e:
            if on_error:
                on_error(path, e)
            continue
        for name, details in servers.items():
            merged[name] = {**merged.get(name, {}), **details}
    return merged


def load_servers(directory=None) -> Dict[str, Dict[str, Any]]:
    return merge(config_paths(directory))


def is_enabled(details: Dict[str, Any]) -> bool:
    return details.get("enabled", True) is not False


def describe(servers: Dict[str, Dict[str, Any]], running: Optional[set] = None) -> List[Dict[str, Any]]:
    """One row per server: name, enabled, running, needs approval, description, command."""
    running = running or set()
    rows = []
    for name in sorted(servers):
        d = servers[name]
        rows.append({
            "name": name,
            "enabled": is_enabled(d),
            "running": name in running,
            "auto_allow": d.get("auto_allow", True) is not False,
            "description": d.get("description", ""),
            "command": " ".join([str(d.get("command", ""))] + [str(a) for a in d.get("args", [])]).strip(),
        })
    return rows


def set_enabled(name: str, enabled: bool, directory=None) -> str:
    """
    Turns a configured server on or off for this user (writes the user file). Returns its path.

    Raises:
        KeyError: no server with that name in the system or user config.
    """
    system_path, user_path = config_paths(directory)
    if name not in merge([system_path, user_path]):
        raise KeyError(name)
    data: Dict[str, Any] = {}
    if os.path.exists(user_path):
        with open(user_path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    servers = data.setdefault("mcpServers", {})
    servers.setdefault(name, {})["enabled"] = bool(enabled)
    os.makedirs(os.path.dirname(user_path), exist_ok=True)
    with open(user_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return user_path
