"""Tokens written to the agent output file keep non-ASCII text and lose only control characters."""

import ai.program  # noqa: F401  (startup import order, avoids a circular import)
from ai.direct import _sanitize_token


def test_keeps_accents_emoji_and_cjk():
    for text in ("O ficheiro contém olá, ação e café.", "done ✅", "中文", "<response>ñ</response>"):
        assert _sanitize_token(text) == text


def test_keeps_newline_and_tab_but_drops_control_characters():
    assert _sanitize_token("a\tb\nc") == "a\tb\nc"
    assert _sanitize_token("a\x00b\x07c\x1bd\x7fe\x85f\r") == "abcdef"
