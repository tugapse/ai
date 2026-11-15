import shutil
import subprocess

import pytest

from ai.modules.tools_search.tools import _python_grep


def _tree(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("import os\n\ndef load_config():\n    pass\n\n\n\nx = load_config()\n")
    (tmp_path / "src" / "b.txt").write_text("nothing here\nLOAD_CONFIG upper\n")
    (tmp_path / "bin.dat").write_bytes(b"load_config\0\0binary")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "c.js").write_text("load_config")
    return tmp_path


def _excluded(path):
    return "/node_modules/" in "/" + path.replace("\\", "/") + "/"


def test_python_grep_output_format(tmp_path):
    root = _tree(tmp_path)
    lines = _python_grep("load_config", str(root), _excluded)
    a, b = str(root / "src" / "a.py"), str(root / "src" / "b.txt")
    assert lines == [
        f"{a}-2-", f"{a}:3:def load_config():", f"{a}-4-    pass",
        "--",
        f"{a}-7-", f"{a}:8:x = load_config()",
        "--",
        f"{b}-1-nothing here", f"{b}:2:LOAD_CONFIG upper",
    ]


@pytest.mark.skipif(not shutil.which("grep"), reason="needs grep")
def test_python_grep_matches_grep(tmp_path):
    root = _tree(tmp_path)
    res = subprocess.run(["grep", "-E", "-n", "-i", "-r", "-H", "-C", "1", "-I",
                          "--exclude-dir=node_modules", "load_config", str(root)],
                         capture_output=True, text=True)
    def groups(lines):
        return sorted("\n".join(lines).split("\n--\n"))
    assert groups(_python_grep("load_config", str(root), _excluded)) == groups(res.stdout.splitlines())


def test_bad_regex_is_searched_as_text(tmp_path):
    (tmp_path / "f.txt").write_text("call foo(\n")
    assert _python_grep("foo(", str(tmp_path), lambda p: False) == [f"{tmp_path / 'f.txt'}:1:call foo("]


def test_smart_search_without_grep(tmp_path, monkeypatch):
    import ai.modules.tools_search.tools as search
    root = _tree(tmp_path)
    monkeypatch.setattr(search.shutil, "which", lambda name: None)
    monkeypatch.setattr(search, "_resolve_path", lambda kwargs: str(root))
    monkeypatch.setattr(search, "get_project_root", lambda: str(root))
    res = search.smart_search(pattern="load_config")
    assert res["status"] == "SUCCESS"
    assert "@ROOT/src/a.py:3:def load_config():" in res["matched_content"]
    assert not any("node_modules" in line or "bin.dat" in line for line in res["matched_content"])
