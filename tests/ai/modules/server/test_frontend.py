"""
Frontend source resolution: folder, pinned cache version, bundled tar.gz, legacy folder, none.
"""

import io
import json
import tarfile
from unittest.mock import MagicMock

import pytest

from ai.config import ProgramSetting
from ai.modules.server.services import frontend as fe


def make_tar(path, version="0.1.0", api_level=1, extra=None, index=True):
    with tarfile.open(path, "w:gz") as tar:
        files = {"version.json": json.dumps({"version": version, "api_level": api_level, "built_at": "x"})}
        if index:
            files["index.html"] = f"<html>{version}</html>"
        files.update(extra or {})
        for name, text in files.items():
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return path


def config(**values):
    cfg = MagicMock()
    mapping = {getattr(ProgramSetting, k): v for k, v in values.items()}
    cfg.get.side_effect = lambda key, default=None: mapping.get(key, default)
    return cfg


@pytest.fixture
def root(tmp_path):
    return tmp_path / "cache"


@pytest.fixture
def legacy(tmp_path):
    folder = tmp_path / "legacy"
    folder.mkdir()
    (folder / "index.html").write_text("old")
    return folder


class TestResolve:
    def test_bundled_is_extracted_into_the_cache_and_served(self, tmp_path, root, legacy):
        tar = make_tar(tmp_path / "frontend.tar.gz")
        path, info = fe.resolve(config(), bundled=tar, legacy=legacy, root=root)
        assert info == {"version": "0.1.0", "source": "bundled"}
        assert path == root / "0.1.0" and (path / "index.html").read_text() == "<html>0.1.0</html>"

    def test_extraction_is_reused(self, tmp_path, root, legacy):
        tar = make_tar(tmp_path / "frontend.tar.gz")
        fe.resolve(config(), bundled=tar, legacy=legacy, root=root)
        (root / "0.1.0" / "marker").write_text("kept")
        fe.resolve(config(), bundled=tar, legacy=legacy, root=root)
        assert (root / "0.1.0" / "marker").exists()

    def test_folder_setting_wins(self, tmp_path, root, legacy):
        dev = tmp_path / "dev"
        dev.mkdir()
        (dev / "index.html").write_text("dev")
        tar = make_tar(tmp_path / "frontend.tar.gz")
        path, info = fe.resolve(config(SERVER_FRONTEND_DIR=str(dev)), bundled=tar, legacy=legacy, root=root)
        assert path == dev and info["source"] == "dir"

    def test_pinned_cached_version_is_served(self, tmp_path, root, legacy):
        fe.extract(make_tar(tmp_path / "old.tar.gz", "0.1.0"), root)
        tar = make_tar(tmp_path / "frontend.tar.gz", "0.2.0")
        path, info = fe.resolve(config(SERVER_FRONTEND_VERSION="0.1.0"), bundled=tar, legacy=legacy, root=root)
        assert info == {"version": "0.1.0", "source": "pinned"} and path == root / "0.1.0"

    def test_pinned_missing_or_too_new_falls_back_to_bundled(self, tmp_path, root, legacy):
        fe.extract(make_tar(tmp_path / "new.tar.gz", "9.0.0", api_level=fe.API_LEVEL + 1), root)
        tar = make_tar(tmp_path / "frontend.tar.gz", "0.2.0")
        for pinned in ("nope", "9.0.0"):
            _, info = fe.resolve(config(SERVER_FRONTEND_VERSION=pinned), bundled=tar, legacy=legacy, root=root)
            assert info["source"] == "bundled"

    def test_legacy_folder_without_a_tar(self, tmp_path, root, legacy):
        path, info = fe.resolve(config(), bundled=tmp_path / "missing.tar.gz", legacy=legacy, root=root)
        assert path == legacy and info["source"] == "legacy"

    def test_nothing_means_api_only(self, tmp_path, root):
        path, info = fe.resolve(config(), bundled=tmp_path / "x.tar.gz", legacy=tmp_path / "y", root=root)
        assert path is None and info == {"version": None, "source": "none"}

    def test_old_versions_are_pruned_but_pinned_kept(self, tmp_path, root, legacy):
        import os, time
        for i in range(7):
            fe.extract(make_tar(tmp_path / f"{i}.tar.gz", f"0.0.{i}"), root)
            os.utime(root / f"0.0.{i}", (time.time() - 100 + i, time.time() - 100 + i))
        tar = make_tar(tmp_path / "frontend.tar.gz", "0.1.0")
        fe.resolve(config(SERVER_FRONTEND_VERSION="0.0.0"), bundled=tar, legacy=legacy, root=root)
        left = {v["version"] for v in fe.cached_versions(root)}
        assert "0.0.0" in left and "0.1.0" in left and len(left) <= fe.KEEP_VERSIONS + 1


class TestUnsafeArchives:
    @pytest.mark.parametrize("name", ["../evil.txt", "/abs.txt", "a/../../evil.txt"])
    def test_path_escape_is_refused_and_nothing_is_left(self, tmp_path, root, name):
        tar = make_tar(tmp_path / "bad.tar.gz", extra={name: "x"})
        with pytest.raises(fe.FrontendError):
            fe.extract(tar, root)
        assert not (tmp_path / "evil.txt").exists()
        assert fe.cached_versions(root) == []

    def test_symlink_is_refused(self, tmp_path, root):
        path = tmp_path / "link.tar.gz"
        with tarfile.open(path, "w:gz") as tar:
            data = json.dumps({"version": "0.1.0"}).encode()
            info = tarfile.TarInfo("version.json"); info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
            link = tarfile.TarInfo("index.html"); link.type = tarfile.SYMTYPE; link.linkname = "/etc/passwd"
            tar.addfile(link)
        with pytest.raises(fe.FrontendError):
            fe.extract(path, root)

    def test_missing_index_or_version_is_refused(self, tmp_path, root):
        with pytest.raises(fe.FrontendError):
            fe.extract(make_tar(tmp_path / "noindex.tar.gz", index=False), root)
        with pytest.raises(fe.FrontendError):
            fe.extract(make_tar(tmp_path / "badver.tar.gz", version="../x"), root)
        assert fe.cached_versions(root) == []

    def test_broken_bundled_falls_back_to_legacy(self, tmp_path, root, legacy):
        bad = make_tar(tmp_path / "frontend.tar.gz", extra={"../evil": "x"})
        _, info = fe.resolve(config(), bundled=bad, legacy=legacy, root=root)
        assert info["source"] == "legacy"


def test_health_reports_frontend_and_api_level(hub, auth, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from ai.modules.server.app import create_app
    monkeypatch.setattr("ai.functions.get_root_directory", lambda: str(tmp_path))
    monkeypatch.setattr(fe, "resolve", lambda config: (None, {"version": "0.1.0", "source": "bundled"}))
    health = TestClient(create_app(hub, {}, auth=auth)).get("/api/health").json()
    assert health["api_level"] == fe.API_LEVEL and health["frontend"] == {"version": "0.1.0", "source": "bundled"}
