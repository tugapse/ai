"""
Which jarvis-web build the server serves, and the per-version cache that allows rolling back.

Sources, first that exists wins:
  1. SERVER_FRONTEND_DIR: a folder with a build, served as it is (development).
  2. SERVER_FRONTEND_VERSION: a version already in the cache (~/Ai/system/frontend/<version>).
  3. The bundled ``frontend.tar.gz`` (shipped in this package by jarvis-web's release script),
     extracted into the cache under the version in its ``version.json``.
  4. The legacy ``frontend/`` folder (until the first tar.gz is committed).
  5. None: the server runs the API only.
"""

import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import ai.functions as func
from ai.config import ProgramSetting
from ai.services.directory_manager import DirectoryManager

API_LEVEL = 1          # raise when the server adds endpoints a frontend may depend on
KEEP_VERSIONS = 5
PACKAGE_DIR = Path(__file__).resolve().parent.parent
BUNDLED_TAR = PACKAGE_DIR / "frontend.tar.gz"
LEGACY_DIR = PACKAGE_DIR / "frontend"


class FrontendError(Exception):
    """A frontend archive or folder that cannot be used."""


def cache_root() -> Path:
    return Path(DirectoryManager().get_system_dir()) / "frontend"


def read_version(folder: Path) -> dict:
    try:
        with open(folder / "version.json", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _safe_members(archive: tarfile.TarFile):
    """Archive members, refusing anything that could land outside the target folder."""
    members = archive.getmembers()
    for m in members:
        name = m.name
        if name.startswith("/") or ".." in Path(name).parts:
            raise FrontendError(f"Unsafe path in archive: {name}")
        if not (m.isfile() or m.isdir()):
            raise FrontendError(f"Links and special files are not allowed in the archive: {name}")
    return members


def archive_version(tar_path: Path) -> dict:
    """The ``version.json`` inside an archive (at its root)."""
    with tarfile.open(tar_path, "r:gz") as archive:
        for m in archive.getmembers():
            if m.isfile() and m.name.lstrip("./") == "version.json":
                data = json.load(archive.extractfile(m))
                if not isinstance(data, dict) or not data.get("version"):
                    raise FrontendError("version.json has no version.")
                return data
    raise FrontendError("The archive has no version.json at its root.")


def extract(tar_path: Path, root: Optional[Path] = None) -> Tuple[Path, dict]:
    """
    Extracts an archive into ``<cache>/<version>`` (atomically: a temp folder renamed at the
    end). An already extracted version is reused. Returns (folder, version info).
    """
    root = root or cache_root()
    info = archive_version(tar_path)
    version = str(info["version"])
    if "/" in version or version in ("", ".", "..", "bundled"):
        raise FrontendError(f"Invalid version '{version}'.")
    target = root / version
    if (target / "index.html").is_file():
        return target, info
    root.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f".{version}-", dir=root))
    try:
        with tarfile.open(tar_path, "r:gz") as archive:
            members = _safe_members(archive)
            if hasattr(tarfile, "data_filter"):  # Python 3.12+: the standard library's own guard too
                archive.extractall(tmp, members=members, filter="data")
            else:
                archive.extractall(tmp, members=members)
        if not (tmp / "index.html").is_file():
            raise FrontendError("The archive has no index.html at its root.")
        if target.exists():
            shutil.rmtree(target)
        os.replace(tmp, target)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    func.log(f"Frontend {version} extracted to {target}")
    return target, info


def cached_versions(root: Optional[Path] = None) -> list:
    """Versions in the cache, newest first: [{version, path, api_level, built_at}]."""
    root = root or cache_root()
    found = []
    if root.is_dir():
        for folder in root.iterdir():
            if folder.is_dir() and not folder.name.startswith(".") and (folder / "index.html").is_file():
                info = read_version(folder)
                found.append({"version": folder.name, "path": str(folder), "api_level": info.get("api_level"),
                              "built_at": info.get("built_at"), "mtime": folder.stat().st_mtime})
    found.sort(key=lambda v: v["mtime"], reverse=True)
    return found


def prune(keep: int = KEEP_VERSIONS, protect: tuple = (), root: Optional[Path] = None) -> None:
    for entry in cached_versions(root)[keep:]:
        if entry["version"] not in protect:
            shutil.rmtree(entry["path"], ignore_errors=True)


def _setting(config, key: ProgramSetting) -> Optional[str]:
    try:
        value = config.get(key) if config is not None else None
    except Exception:
        value = None
    return str(value).strip() if value not in (None, "") else None


def resolve(config=None, bundled: Path = BUNDLED_TAR, legacy: Path = LEGACY_DIR,
            root: Optional[Path] = None) -> Tuple[Optional[Path], dict]:
    """The folder to serve and ``{version, source}`` (source: dir, pinned, bundled, legacy, none)."""
    folder = _setting(config, ProgramSetting.SERVER_FRONTEND_DIR)
    if folder:
        path = Path(os.path.expanduser(folder))
        if (path / "index.html").is_file():
            return path, {"version": read_version(path).get("version"), "source": "dir"}
        func.log(f"SERVER_FRONTEND_DIR '{folder}' has no index.html; ignoring it.", level="WARN")

    root = root or cache_root()
    bundled_version = None
    if bundled.is_file():
        try:
            bundled_path, info = extract(bundled, root)
            bundled_version = str(info["version"])
        except Exception as e:
            func.log(f"Bundled frontend unusable: {e}", level="ERROR")
            bundled_path = None
    else:
        bundled_path = None

    pinned = _setting(config, ProgramSetting.SERVER_FRONTEND_VERSION)
    if pinned and pinned != "bundled":
        path = root / pinned
        info = read_version(path)
        if not (path / "index.html").is_file():
            func.log(f"Pinned frontend {pinned} is not in the cache; serving the bundled one.", level="WARN")
        elif int(info.get("api_level") or 0) > API_LEVEL:
            func.log(f"Pinned frontend {pinned} needs api_level {info.get('api_level')} "
                     f"but this server has {API_LEVEL}; serving the bundled one.", level="WARN")
        else:
            prune(protect=(pinned, bundled_version or ""), root=root)
            return path, {"version": pinned, "source": "pinned"}

    if bundled_path is not None:
        prune(protect=(bundled_version,), root=root)
        return bundled_path, {"version": bundled_version, "source": "bundled"}

    if (legacy / "index.html").is_file():
        return legacy, {"version": read_version(legacy).get("version"), "source": "legacy"}

    func.log("No frontend found: serving the API only.", level="WARN")
    return None, {"version": None, "source": "none"}
