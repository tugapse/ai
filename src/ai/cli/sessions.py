"""``ai sessions``: saved agent sessions of this folder."""
from ai.cli.base import SUPPRESS, add_actions, add_command

NAME = "sessions"
HELP = "List the saved agent sessions of this folder"
DESCRIPTION = """Saved agent sessions belong to the folder they were started in.

  ai sessions list                 sessions of this folder
  ai agent --resume [ID]           continue one
"""

DEFAULTS = {"list_sessions": False}

LEGACY = {"--list-sessions": "ai sessions list", "-ls": "ai sessions list"}


def register(subparsers, parent):
    parser = add_command(subparsers, NAME, HELP, DESCRIPTION, usage="%(prog)s ACTION")
    actions = add_actions(parser, "sessions_command")
    add_command(actions, "list", "List the sessions of this folder").set_defaults(list_sessions=True)


def add_legacy(parser):
    parser.add_argument("--list-sessions", "-ls", action="store_true", help=SUPPRESS)


# --- handlers -----------------------------------------------------------------------

def list_sessions(prog, args, directory_manager) -> None:
    """
    Lists all active agent sessions found in the current working directory.

    :param args: The parsed command-line arguments containing the --list-sessions flag.
    :raises SystemExit: Exits after displaying the session list or a 'not found' message.
    """
    import os
    import sys
    import ai.functions as func
    from ai.agents.session_manager import AgentSessionManager
    if args.list_sessions:
        sessions = AgentSessionManager.list_sessions(os.getcwd())
        if not sessions:
            func.out("No agent sessions found.", level="INFO")
            sys.exit(0)

        func.out("Agent Sessions:", level="INFO")
        for session in sessions:
            func.out(f"Session ID: {session['session_id']}, User Request: {session.get('user_request', 'N/A')}", level="INFO")
        sys.exit(0)


MAINTENANCE = (list_sessions,)
