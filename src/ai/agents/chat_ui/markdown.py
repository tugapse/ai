"""
Small Markdown-to-ANSI renderer for agent answers in the chat UI.

Covers what models actually write: headings, bullet and numbered lists (nested),
bold / italic / inline code / links, fenced code blocks (highlighted with pygments
when it is installed), block quotes, horizontal rules and simple tables.
Line breaks inside paragraphs are kept. Text and list items are word-wrapped with a hanging indent so wrapped lines
stay aligned. Anything it does not understand is printed as plain text.
"""

import re
from typing import List, Optional

from ai.agents.terminal_ui import TerminalUI

RESET = "\033[0m"
BOLD_ON, BOLD_OFF = "\033[1m", "\033[22m"
ITALIC_ON, ITALIC_OFF = "\033[3m", "\033[23m"
UNDERLINE_ON, UNDERLINE_OFF = "\033[4m", "\033[24m"
GREY = "\033[38;5;245m"
CODE = "\033[38;5;180m"
RULE = "\033[38;5;240m"

_SGR_RE = re.compile(r"\x1b\[[0-9;]*m")
_FENCE_RE = re.compile(r"^\s*(```|~~~)\s*([\w+-]*)")
_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_BULLET_RE = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_NUMBERED_RE = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_QUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
_RULE_RE = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")

_INLINE_RE = re.compile(
    r"(?P<code>`+)(?P<code_text>.+?)(?P=code)"
    r"|\*\*(?P<bold>.+?)\*\*"
    r"|__(?P<bold2>.+?)__"
    r"|(?<![\w*])\*(?P<italic>[^*\s](?:[^*]*[^*\s])?)\*(?!\w)"
    r"|(?<![\w_])_(?P<italic2>[^_\s](?:[^_]*[^_\s])?)_(?!\w)"
    r"|\[(?P<link_text>[^\]]+)\]\((?P<link_url>[^)\s]+)\)"
)


def visible_len(text: str) -> int:
    return len(_SGR_RE.sub("", text))


def render_inline(text: str, base: str = "") -> str:
    """Applies bold / italic / code / link styling inside one line of text."""

    def repl(m: re.Match) -> str:
        if m.group("code"):
            return f"{CODE}{m.group('code_text')}{RESET}{base}"
        if m.group("bold") or m.group("bold2"):
            return f"{BOLD_ON}{render_inline(m.group('bold') or m.group('bold2'), base)}{BOLD_OFF}"
        if m.group("italic") or m.group("italic2"):
            return f"{ITALIC_ON}{render_inline(m.group('italic') or m.group('italic2'), base)}{ITALIC_OFF}"
        label, url = m.group("link_text"), m.group("link_url")
        tail = "" if label == url else f" {GREY}({url}){RESET}{base}"
        return f"{UNDERLINE_ON}{label}{UNDERLINE_OFF}{tail}"

    return _INLINE_RE.sub(repl, text)


def _active_sgr(text: str) -> str:
    """The SGR codes still in effect at the end of ``text`` (since its last reset)."""
    codes = _SGR_RE.findall(text)
    for i in range(len(codes) - 1, -1, -1):
        if codes[i] in (RESET, "\033[m"):
            return "".join(codes[i + 1:])
    return "".join(codes)


def wrap(styled: str, width: int, first_prefix: str, rest_prefix: str, base: str = "") -> List[str]:
    """Word-wraps already-styled text; styles carry over to the next line."""
    words = styled.split(" ")
    lines: List[str] = []
    current, current_len = first_prefix, visible_len(first_prefix)
    empty = True
    for word in words:
        wlen = visible_len(word)
        if not empty and current_len + 1 + wlen > width:
            carried = _active_sgr(current)
            lines.append(current + RESET)
            current = rest_prefix + base + carried
            current_len = visible_len(rest_prefix)
            empty = True
        if not empty:
            current += " "
            current_len += 1
        current += word
        current_len += wlen
        empty = False
    lines.append(current + RESET)
    return lines


def _highlight(code: str, lang: str) -> Optional[List[str]]:
    try:
        from pygments import highlight
        from pygments.formatters import Terminal256Formatter
        from pygments.lexers import get_lexer_by_name
        from pygments.util import ClassNotFound
    except ImportError:
        return None
    try:
        lexer = get_lexer_by_name(lang)
    except ClassNotFound:
        return None
    return highlight(code, lexer, Terminal256Formatter(style="monokai")).rstrip("\n").split("\n")


def _render_code(lines: List[str], lang: str) -> List[str]:
    body = _highlight("\n".join(lines), lang) if lang else None
    if body is None:
        body = [f"{CODE}{line}{RESET}" for line in lines]
    gutter = f"{RULE}│{RESET} "
    header = [f"{RULE}╭─ {lang}{RESET}"] if lang else [f"{RULE}╭─{RESET}"]
    return header + [gutter + line + RESET for line in body] + [f"{RULE}╰─{RESET}"]


def _split_row(line: str) -> List[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def _render_table(rows: List[str], base: str) -> List[str]:
    header, *body = rows
    cells = [_split_row(header)] + [_split_row(r) for r in body if not _TABLE_SEP_RE.match(r)]
    cols = max(len(r) for r in cells)
    styled = [[render_inline(c, base) for c in r] + [""] * (cols - len(r)) for r in cells]
    widths = [max(visible_len(r[i]) for r in styled) for i in range(cols)]
    sep = f" {RULE}│{RESET}{base} "
    out = []
    for n, row in enumerate(styled):
        padded = [cell + " " * (widths[i] - visible_len(cell)) for i, cell in enumerate(row)]
        if n == 0:
            padded = [f"{BOLD_ON}{p}{BOLD_OFF}" for p in padded]
        out.append(base + sep.join(padded) + RESET)
        if n == 0:
            out.append(RULE + "─┼─".join("─" * w for w in widths) + RESET)
    return out


def render_markdown(text: str, width: int = 100, base: str = "") -> List[str]:
    """Renders Markdown to a list of ANSI lines no wider than ``width`` (except code)."""
    width = max(20, width)
    src = text.replace("\t", "    ").split("\n")
    out: List[str] = []
    i = 0

    def blank():
        if out and out[-1] != "":
            out.append("")

    while i < len(src):
        line = src[i]

        fence = _FENCE_RE.match(line)
        if fence:
            marker, lang = fence.group(1), fence.group(2)
            code = []
            i += 1
            while i < len(src) and not src[i].strip().startswith(marker):
                code.append(src[i])
                i += 1
            i += 1  # closing fence
            out.extend(_render_code(code, lang))
            continue

        if not line.strip():
            blank()
            i += 1
            continue

        if "|" in line and i + 1 < len(src) and _TABLE_SEP_RE.match(src[i + 1]):
            rows = []
            while i < len(src) and "|" in src[i] and src[i].strip():
                rows.append(src[i])
                i += 1
            out.extend(_render_table(rows, base))
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            level, title = len(heading.group(1)), heading.group(2)
            color = TerminalUI.PRIMARY if level <= 2 else base
            blank()
            out.extend(wrap(f"{color}{BOLD_ON}{render_inline(title, color)}{BOLD_OFF}", width, "", "", color))
            i += 1
            continue

        if _RULE_RE.match(line):
            out.append(f"{RULE}{'─' * min(width, 40)}{RESET}")
            i += 1
            continue

        quote = _QUOTE_RE.match(line)
        if quote:
            bar = f"{RULE}▎{RESET} "
            style = f"{GREY}{ITALIC_ON}"
            out.extend(wrap(style + render_inline(quote.group(1), style), width, bar, bar, style))
            i += 1
            continue

        bullet = _BULLET_RE.match(line)
        numbered = None if bullet else _NUMBERED_RE.match(line)
        if bullet or numbered:
            indent = len((bullet or numbered).group(1)) // 2 * 2
            if bullet:
                marker, body = f"{TerminalUI.PRIMARY}•{RESET}", bullet.group(2)
                mlen = 1
            else:
                marker, body = f"{GREY}{numbered.group(2)}.{RESET}", numbered.group(3)
                mlen = len(numbered.group(2)) + 1
            # Continuation lines of the same item (indented, not a new block).
            i += 1
            while i < len(src) and src[i].strip() and src[i].startswith(" " * (indent + 2)) \
                    and not (_BULLET_RE.match(src[i]) or _NUMBERED_RE.match(src[i]) or _FENCE_RE.match(src[i])):
                body += " " + src[i].strip()
                i += 1
            first = " " * indent + marker + " " + base
            rest = " " * (indent + mlen + 1)
            out.extend(wrap(base + render_inline(body, base), width, first, rest, base))
            continue

        # Plain text. Line breaks are kept (unlike strict Markdown): models use them on purpose.
        out.extend(wrap(base + render_inline(line.strip(), base), width, "", "", base))
        i += 1

    while out and out[-1] == "":
        out.pop()
    while out and out[0] == "":
        out.pop(0)
    return out or [""]
