"""
resolve_path keeps every tool path inside PROJECT_ROOT.
"""

import os

import pytest

import ai.tools.base as base


@pytest.fixture
def root(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.setattr(base, "PROJECT_ROOT", str(ws))
    return ws


@pytest.mark.parametrize("path", ["a.txt", "@ROOT/a.txt", "sub/../a.txt", "@ROOT", "."])
def test_paths_inside_are_allowed(root, path):
    assert os.path.realpath(base.resolve_path({"path": path})).startswith(os.path.realpath(root))


@pytest.mark.parametrize("path", ["../x", "/etc/passwd", "@ROOT/../x"])
def test_paths_outside_are_denied(root, path):
    with pytest.raises(PermissionError):
        base.resolve_path({"path": path})


def test_sibling_folder_sharing_the_prefix_is_denied(root, tmp_path):
    # Before: a plain startswith let /tmp/.../ws2 pass as inside /tmp/.../ws.
    (tmp_path / "ws2").mkdir()
    with pytest.raises(PermissionError):
        base.resolve_path({"path": "../ws2/x"})


def test_symlink_pointing_outside_is_denied(root, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    os.symlink(outside, root / "link")
    with pytest.raises(PermissionError):
        base.resolve_path({"path": "link/secret.txt"})
