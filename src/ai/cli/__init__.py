"""
The JARVIS command line.

One module per command group (``agent``, ``server``, ``knowledge``...). Each module defines:

- ``register(subparsers, parent)``: its sub-command(s) and options, with their own ``--help``;
- ``DEFAULTS``: the ``args`` attributes it sets, with their default values;
- ``LEGACY`` + ``add_legacy(parser)``: the old top-level flags it replaces (``--agent``,
  ``--server``...). They keep working, hidden from the help, with a one-line notice;
- ``MAINTENANCE``: handlers ``fn(prog, args, directory_manager)`` run before the model loads; each
  returns when its option isn't set, and exits when it did its job. Optionally ``AFTER_MODEL``:
  the same, run once the model is loaded (e.g. ``knowledge build``).

Sub-commands and old flags fill the **same** ``args`` attributes, so the code that acts on them
(``ai.cli_args``) doesn't care which form was typed.

To add a group: write ``ai/cli/<name>.py`` with those names and add it to ``COMMAND_MODULES``.
The agent run, server mode and one-shot answers stay in ``ai.cli_args`` (the dispatcher).
"""
import argparse
import copy
import sys
from typing import List, Optional, Sequence, Tuple

from ai.cli import agent, knowledge, mcp, models, server, sessions, setup, tools
from ai.cli.base import DEFAULTS, JarvisHelpFormatter, SUPPRESS, add_common_options, common_parent, title
from ai.color import Color

# Order = order in the help.
COMMAND_MODULES = [agent, sessions, knowledge, models, tools, mcp, server, setup]


def all_defaults() -> dict:
    defaults = dict(DEFAULTS)
    for module in COMMAND_MODULES:
        defaults.update(module.DEFAULTS)
    return defaults


def legacy_flags() -> dict:
    flags = {}
    for module in COMMAND_MODULES:
        flags.update(module.LEGACY)
    return flags


def build_parser(version: str = "", description: str = "") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai",
        description=description,
        formatter_class=JarvisHelpFormatter,
        usage=f"{Color.CYAN}ai{Color.RESET} [OPTIONS]  |  {Color.CYAN}ai{Color.RESET} COMMAND [OPTIONS]   "
              f"(ai COMMAND --help for each command)",
        add_help=False,
        argument_default=SUPPRESS,
        epilog=f"{Color.DIM}Old flags such as --agent or --server still work.{Color.RESET}",
    )
    general = parser.add_argument_group(title("GENERAL"))
    general.add_argument("-h", "--help", action="help", help="Show this help (ai COMMAND --help for a command)")
    general.add_argument("-v", "--version", action="version", version=f"JARVIS Version {version}",
                         help="Show the version")
    general.add_argument("--show-logo", action="store_true", help="Show the JARVIS banner")

    # Commands first in the help, then the options shared by chat, one-shot runs and the agent.
    parent = common_parent()
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND", title=title("COMMANDS"), prog="ai")
    for module in COMMAND_MODULES:
        module.register(subparsers, parent)
    add_common_options(parser)
    for module in COMMAND_MODULES:
        module.add_legacy(parser)
    return parser


def _legacy_used(argv: Sequence[str], command: Optional[str]) -> List[str]:
    """Old top-level flags typed before the sub-command (or anywhere, when there is none)."""
    flags = legacy_flags()
    stop = len(argv)
    if command:
        try:
            stop = list(argv).index(command)
        except ValueError:
            pass
    used = []
    for token in argv[:stop]:
        name = token.split("=", 1)[0]
        if name in flags and name not in used:
            used.append(name)
    return used


def warn_legacy(used: List[str], stream=None) -> None:
    if not used:
        return
    flags = legacy_flags()
    stream = stream or sys.stderr
    hints = ", ".join(f"{flag} -> {flags[flag]}" for flag in used)
    try:
        stream.write(f"{Color.DIM}[ * ] Old flags still work but will go away: {hints}{Color.RESET}\n")
    except Exception:
        pass


def parse_args(argv: Optional[Sequence[str]] = None, version: str = "", description: str = "",
               warn: bool = True) -> Tuple[argparse.ArgumentParser, argparse.Namespace]:
    """Parses the command line into the ``args`` the rest of JARVIS expects."""
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser(version, description)
    args = parser.parse_args(argv)
    for key, value in all_defaults().items():
        if not hasattr(args, key):
            setattr(args, key, copy.copy(value))
    if warn:
        warn_legacy(_legacy_used(argv, args.command))
    return parser, args


def run_maintenance(prog, args, directory_manager) -> None:
    """Runs the command handlers that don't need a model (each exits when it handled the run)."""
    for module in COMMAND_MODULES:
        for handler in getattr(module, "MAINTENANCE", ()):
            handler(prog, args, directory_manager)


def run_after_model(prog, args, directory_manager) -> None:
    """Runs the command handlers that need the loaded model."""
    for module in COMMAND_MODULES:
        for handler in getattr(module, "AFTER_MODEL", ()):
            handler(prog, args, directory_manager)
