"""
Keeps ``<root>/system`` in step with the shipped templates (``assets/templates/system``).

``system/`` holds JARVIS's own defaults; customisations belong in ``user/``, which is looked up first
and is never touched here. On every start each shipped file is compared with the copy in
``system/``:

- missing                → copied;
- same as shipped        → nothing to do;
- different, and still the copy JARVIS wrote last time (hash in the manifest) → replaced;
- different, and edited by hand (or no manifest yet, from an older install) → the old file is
  kept in ``system/backup/<date>/`` and then replaced.

The manifest (``system/.templates.json``) records the hash of every file as written, so later
template changes can tell "untouched" from "edited".
"""
import hashlib
import json
import logging
import os
import shutil
import time
from typing import Callable, Dict, Iterable, List, Optional

MANIFEST_NAME = ".templates.json"
BACKUP_DIR = "backup"

logger = logging.getLogger(__name__)


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _template_files(src_root: str, skip: Callable[[str], bool]) -> Iterable[str]:
    """Relative paths (with ``/``) of every shipped file under ``src_root``."""
    for directory, dirs, files in os.walk(src_root):
        rel_dir = os.path.relpath(directory, src_root).replace(os.sep, "/")
        prefix = "" if rel_dir == "." else rel_dir + "/"
        dirs[:] = sorted(d for d in dirs if not skip(prefix + d))
        for name in sorted(files):
            if not skip(prefix + name):
                yield prefix + name


def _load_manifest(path: str) -> Dict[str, str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(v, str)} if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def sync_system_templates(src_root: str, dst_root: str,
                          skip: Optional[Callable[[str], bool]] = None) -> List[str]:
    """
    Brings ``dst_root`` (``<root>/system``) up to date with ``src_root`` (``assets/templates/system``).

    Args:
        src_root: shipped templates folder.
        dst_root: the user's ``system/`` folder.
        skip: ``fn(relative_path) -> bool`` for paths that are never synced (runtime folders).

    Returns:
        Relative paths of hand-edited files that were backed up before being replaced.
    """
    if not os.path.isdir(src_root):
        return []
    skip = skip or (lambda rel: False)
    manifest_path = os.path.join(dst_root, MANIFEST_NAME)
    manifest = _load_manifest(manifest_path)
    new_manifest: Dict[str, str] = {}
    backed_up: List[str] = []
    backup_root = os.path.join(dst_root, BACKUP_DIR, time.strftime("%Y%m%d-%H%M%S"))
    changed = False

    for rel in _template_files(src_root, skip):
        src = os.path.join(src_root, *rel.split("/"))
        dst = os.path.join(dst_root, *rel.split("/"))
        shipped = _sha256(src)
        new_manifest[rel] = shipped
        try:
            current = _sha256(dst) if os.path.isfile(dst) else None
            if current == shipped:
                continue
            if current is not None and manifest.get(rel) != current:
                backup = os.path.join(backup_root, *rel.split("/"))
                os.makedirs(os.path.dirname(backup), exist_ok=True)
                shutil.copy2(dst, backup)
                backed_up.append(rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            changed = True
        except OSError as e:
            logger.error(f"Could not update {dst}: {e}")
            if rel in manifest:
                new_manifest[rel] = manifest[rel]
            else:
                new_manifest.pop(rel, None)

    if changed or new_manifest != manifest:
        try:
            os.makedirs(dst_root, exist_ok=True)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(new_manifest, f, indent=2, sort_keys=True)
        except OSError as e:
            logger.error(f"Could not write {manifest_path}: {e}")

    if backed_up:
        logger.warning(f"Updated {len(backed_up)} file(s) you had edited in {dst_root}: "
                       f"{', '.join(backed_up)}. Old copies are in {backup_root}. "
                       f"Put your changes in user/ instead (it's looked up first).")
    return backed_up
