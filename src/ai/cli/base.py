"""
Shared pieces of the command line: the help formatter, the global options (usable before or
after a sub-command) and the defaults every run relies on.

Every option in the parser tree uses ``default=argparse.SUPPRESS``: argparse copies a sub-command's
namespace over the parent's, so a real default in a sub-command would erase a value given before
it (``ai -m hi agent``). Defaults are filled in once, after parsing (``DEFAULTS``).
"""
import argparse

from ai.color import Color

SUPPRESS = argparse.SUPPRESS

# Attribute -> default for everything the rest of the program reads from ``args``.
# Each command module adds its own (see ``ai.cli.__init__``).
DEFAULTS = {
    "command": None,
    # chat / one-shot
    "msg": None, "model": None, "system": None, "system_file": None,
    "file": None, "image": None, "load_folder": None, "ext": None,
    "task": None, "task_file": None, "output_file": None,
    # output and debugging
    "show_logo": False, "print_chat": None, "print_log": False, "print_debug": False,
    "no_out": False, "no_think_anim": False, "debug_console": False,
}


class JarvisHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Keeps descriptions aligned and leaves hand-written text as it is."""

    def __init__(self, prog):
        super().__init__(prog, max_help_position=46, width=110)


def title(text: str) -> str:
    return f"{Color.CYAN}{text}{Color.RESET}"


def add_common_options(parser: argparse.ArgumentParser) -> None:
    """Options shared by the chat, one-shot runs and the agent: message, model, context, output."""
    basics = parser.add_argument_group(title("MESSAGE & MODEL"))
    basics.add_argument("--msg", "-m", type=str, help="Send one message and print the answer")
    basics.add_argument("--model", "-md", type=str, help="Model config to use (e.g. agents/lite)")
    basics.add_argument("--system", "-s", type=str, help="System prompt by name (inside system/system-prompt/)")
    basics.add_argument("--system-file", "-sf", type=str, help="System prompt from a file")
    basics.add_argument("--task", "-t", type=str, help="Run a task (prompt template from user/task/)")
    basics.add_argument("--task-file", "-tf", type=str, help="Run a task from a file")
    basics.add_argument("--output-file", "-o", type=str, help="Write the answer to a file")

    context = parser.add_argument_group(title("FILES & CONTEXT"))
    context.add_argument("--file", "-f", type=str, help="Add a file to the context")
    context.add_argument("--image", "-i", type=str, help="Add an image (needs a vision model)")
    context.add_argument("--load-folder", "-D", type=str, help="Add a folder to the context")
    context.add_argument("--ext", "-e", type=str, help="Only load files with these extensions")

    output = parser.add_argument_group(title("OUTPUT & DEBUG"))
    output.add_argument("--print-chat", "-p", type=str, help="Print a saved chat history")
    output.add_argument("--print-log", "-pl", action="store_true", help="Show logs")
    output.add_argument("--print-debug", "-pdb", action="store_true", help="Show debug logs")
    output.add_argument("--no-out", "-q", action="store_true", help="Don't print to the terminal")
    output.add_argument("--no-think-anim", "-nta", action="store_true", help="Disable the thinking animation")
    output.add_argument("--debug-console", "-dc", action="store_true", help="Don't clear the screen")


def common_parent() -> argparse.ArgumentParser:
    """A parent parser with the common options, for sub-commands that accept them (e.g. ``agent``)."""
    parent = argparse.ArgumentParser(add_help=False, argument_default=SUPPRESS)
    add_common_options(parent)
    return parent


def add_command(subparsers, name: str, help_text: str, description: str = "", parents=None,
                usage: str = "%(prog)s [OPTIONS]", **kwargs) -> argparse.ArgumentParser:
    """A sub-command parser with the JARVIS formatter, a short usage line and suppressed defaults."""
    return subparsers.add_parser(
        name, help=help_text, description=description or help_text, parents=parents or [],
        usage=usage, formatter_class=JarvisHelpFormatter, argument_default=SUPPRESS, **kwargs)


def add_actions(parser: argparse.ArgumentParser, dest: str, required: bool = True):
    """Nested sub-commands (``ai knowledge build``): their usage reads ``ai knowledge <action>``."""
    return parser.add_subparsers(dest=dest, metavar="ACTION", required=required, prog=parser.prog,
                                 title="actions")
