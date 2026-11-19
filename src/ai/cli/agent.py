"""``ai agent``: run the agent pipeline (interactive chat, one-shot, resume)."""
from ai.cli.base import SUPPRESS, add_command

NAME = "agent"
HELP = "Work with the agents: chat, one-shot task or resume a session"
DESCRIPTION = """Run the agent pipeline in this folder.

  ai agent                         interactive agent chat
  ai agent -m "Find the TODOs"     one turn, then exit
  ai agent -t release/start        a task as the first message
  ai agent --resume [ID]           continue a saved session of this folder
  ai agent --pipeline small        another pipeline
"""

DEFAULTS = {"agent": False, "resume": None, "pipeline": None, "session_id": None, "knowledge": None}

# Old top-level flag -> what to type now (shown in the deprecation notice).
LEGACY = {
    "--agent": "ai agent",
    "--resume": "ai agent --resume", "-r": "ai agent --resume",
    "--pipeline": "ai agent --pipeline", "-ppl": "ai agent --pipeline",
    "--session-id": "ai agent --session-id",
    "--knowledge": "ai agent --knowledge", "-kb": "ai agent --knowledge",
}


def _add_options(group, hidden: bool = False):
    h = (lambda text: SUPPRESS) if hidden else (lambda text: text)
    group.add_argument("--resume", "-r", nargs="?", const="", metavar="SESSION_ID",
                       help=h("Resume a session of this folder: pick from a list, or pass an id/prefix"))
    group.add_argument("--pipeline", "-ppl", type=str, metavar="NAME",
                       help=h("Pipeline to use (default: default)"))
    group.add_argument("--session-id", type=str, metavar="ID", help=h("Start or continue the session with this id"))
    group.add_argument("--full-access", "--yes", dest="full_access", action="store_true",
                       help=h("Run tools without asking for permission (enabling an MCP server still asks)"))
    group.add_argument("--knowledge", "-kb", action="append", metavar="PATH",
                       help=h("Knowledge folder (component JSON and/or Markdown docs); repeatable, remembered for this folder"))


def register(subparsers, parent):
    parser = add_command(subparsers, NAME, HELP, DESCRIPTION, parents=[parent],
                         usage="%(prog)s [-m MSG | -t TASK] [--resume [ID]] [--pipeline NAME] [OPTIONS]")
    _add_options(parser.add_argument_group("AGENT"))
    parser.set_defaults(agent=True)


def add_legacy(parser):
    parser.add_argument("--agent", action="store_true", help=SUPPRESS)
    _add_options(parser, hidden=True)


MAINTENANCE = ()
