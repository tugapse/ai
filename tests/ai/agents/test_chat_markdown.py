from ai.agents.chat_ui import markdown as M


def plain(lines):
    return [M._SGR_RE.sub("", line).rstrip() for line in lines]


def test_inline_styles_are_removed_and_styled():
    out = M.render_inline("**bold** and `code` and *it* and [docs](http://x)")
    assert M._SGR_RE.sub("", out) == "bold and code and it and docs (http://x)"
    assert M.BOLD_ON in out and M.CODE in out and M.ITALIC_ON in out


def test_snake_case_is_not_italic():
    assert M.render_inline("my_var_name and 2*3*4") == "my_var_name and 2*3*4"


def test_lists_wrap_with_hanging_indent():
    lines = plain(M.render_markdown("* " + "word " * 30, width=40))
    assert lines[0].startswith("• ") and all(l.startswith("  ") for l in lines[1:])
    assert all(len(l) <= 40 for l in lines)


def test_headings_numbered_quote_rule():
    lines = plain(M.render_markdown("intro\n### Title\n1. first\n2. second\n> quoted\n---", width=60))
    assert lines == ["intro", "", "Title", "1. first", "2. second", "▎ quoted", "─" * 40]


def test_code_block_is_kept_verbatim():
    lines = plain(M.render_markdown("```\n  x = **1**\n```", width=60))
    assert lines == ["╭─", "│   x = **1**", "╰─"]


def test_table_columns_align():
    lines = plain(M.render_markdown("| a | bb |\n|---|---|\n| ccc | d |", width=60))
    assert lines == ["a   │ bb", "────┼───", "ccc │ d"]


def test_line_breaks_are_kept():
    assert plain(M.render_markdown("one\ntwo", width=60)) == ["one", "two"]
