"""``ai mcp``: see the configured MCP servers and turn them on or off."""
from ai.cli.base import add_actions, add_command

NAME = "mcp"
HELP = "List the MCP servers (browser, GitHub...) and enable or disable them"
DESCRIPTION = """MCP servers give the agents extra tools. Shipped ones start disabled.

  ai mcp list                      configured servers and whether they're enabled
  ai mcp enable playwright         start it in every agent run (saved in user/config/mcp_config.json)
  ai mcp disable playwright

Agents can also see them (list_mcp_servers) and turn one on for a run (enable_mcp_server, which
asks you first).
"""

DEFAULTS = {"mcp_action": None, "mcp_server": None}

LEGACY = {}


def register(subparsers, parent):
    parser = add_command(subparsers, NAME, HELP, DESCRIPTION, usage="%(prog)s ACTION")
    actions = add_actions(parser, "mcp_command")
    add_command(actions, "list", "List the configured MCP servers", usage="%(prog)s").set_defaults(mcp_action="list")
    for action, text in (("enable", "Enable a server in every agent run"), ("disable", "Disable a server")):
        sub = add_command(actions, action, text, usage="%(prog)s NAME")
        sub.add_argument("mcp_server", metavar="NAME")
        sub.set_defaults(mcp_action=action)


def add_legacy(parser):
    pass


# --- handlers -----------------------------------------------------------------------

def mcp_command(prog, args, directory_manager) -> None:
    """``ai mcp list|enable|disable``: reads/writes the user's mcp_config.json and exits."""
    action = getattr(args, "mcp_action", None)
    if not action:
        return
    import sys
    import ai.functions as func
    from ai.color import Color
    from ai.tools import mcp_config

    if action == "list":
        rows = mcp_config.describe(mcp_config.load_servers(directory_manager))
        if not rows:
            func.out("No MCP servers configured.")
        for row in rows:
            state = f"{Color.GREEN}enabled{Color.RESET} " if row["enabled"] else f"{Color.DIM}disabled{Color.RESET}"
            ask = "" if row["auto_allow"] else "  (asks before each call)"
            func.out(f"  {row['name']:<14} {state}  {row['description']}{ask}")
            func.out(f"  {'':<14} {Color.DIM}{row['command']}{Color.RESET}")
        func.out(f"\nFiles: {', '.join(mcp_config.config_paths(directory_manager))}")
        sys.exit(0)

    try:
        path = mcp_config.set_enabled(args.mcp_server, action == "enable", directory_manager)
    except KeyError:
        func.error(f"No MCP server named '{args.mcp_server}'. See: ai mcp list")
        sys.exit(1)
    func.out(f"MCP server '{args.mcp_server}' {action}d ({path}). Applies to the next agent run.")
    sys.exit(0)


MAINTENANCE = (mcp_command,)
