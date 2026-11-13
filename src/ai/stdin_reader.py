"""Reading input piped into the CLI without hanging on a stdin nobody writes to."""

import os
import select
import stat
import sys
from typing import Optional

import ai.functions as func
from ai.color import Color

STDIN_WAIT_ENV = "AI_STDIN_WAIT"
STDIN_WAIT_DEFAULT = 3.0   # seconds to wait for the first piped byte when a prompt was also given
STDIN_HINT_AFTER = 2.0     # seconds before telling the user we are waiting on stdin


def read_piped_stdin(has_other_input: bool, stream=None, wait: Optional[float] = None) -> str:
    """
    Reads input piped into the program (``git diff | ai -m "review"``) without hanging on a
    stdin that is open but never written to (a parent that left its pipe open: IDEs, agents,
    subprocess calls).

    - terminal: nothing is read;
    - regular file or /dev/null: read (EOF is immediate);
    - pipe/socket and no other prompt: stdin is the only input, so wait for it (with a hint);
    - pipe/socket with a prompt: wait up to ``wait`` seconds (``AI_STDIN_WAIT``, default 3) for
      the first byte; once data arrives it is read to EOF, otherwise stdin is ignored.

    Args:
        has_other_input: A prompt was given another way (--msg, --task, --task-file, ...).
        stream: The input stream (default sys.stdin).
        wait: Seconds to wait for the first byte when ``has_other_input``.

    Returns:
        The stripped piped text, or "" when there is none.
    """
    stream = sys.stdin if stream is None else stream
    try:
        if stream is None or stream.closed or stream.isatty():
            return ""
        fd = stream.fileno()
        mode = os.fstat(fd).st_mode
    except (ValueError, OSError, AttributeError):
        return ""

    if os.name == "nt" or not (stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode)):
        return stream.read().strip()

    if not has_other_input:
        if not select.select([fd], [], [], STDIN_HINT_AFTER)[0]:
            func.out(f"{Color.YELLOW}[ * ] Waiting for input on stdin... "
                     f"(end it with Ctrl+D, or run with < /dev/null){Color.RESET}")
        return stream.read().strip()

    if wait is None:
        try:
            wait = float(os.environ.get(STDIN_WAIT_ENV, STDIN_WAIT_DEFAULT))
        except ValueError:
            wait = STDIN_WAIT_DEFAULT
    if not select.select([fd], [], [], max(wait, 0.0))[0]:
        func.debug(f"stdin is an open pipe with no data after {wait}s; ignoring it.")
        return ""
    return stream.read().strip()
