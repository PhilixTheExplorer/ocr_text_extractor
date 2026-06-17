"""OS-appropriate locations for Lexo's data, config, cache, and bundled assets.

Runtime data lives in the per-OS data dir (via platformdirs), never the CWD -
fixing v1's habit of writing wherever it happened to run.
"""

from __future__ import annotations

import shutil
import tempfile
from importlib import resources
from pathlib import Path

from platformdirs import PlatformDirs

_dirs = PlatformDirs(appname="lexo", appauthor=False)

# Prefix for the per-session working directories the GUI creates in the system
# temp dir. Each holds working copies of the open document; they are removed on a
# clean exit, but a crash or kill can leave them behind to accumulate.
TEMP_PREFIX = "lexo_"


def data_dir() -> Path:
    p = Path(_dirs.user_data_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_dir() -> Path:
    p = Path(_dirs.user_config_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_dir() -> Path:
    p = Path(_dirs.user_cache_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    return data_dir() / "lexo.db"


def artifacts_dir() -> Path:
    p = data_dir() / "artifacts"
    p.mkdir(parents=True, exist_ok=True)
    return p


def new_session_tmpdir(root: Path | None = None) -> Path:
    """Create a fresh working directory for one GUI session.

    `root` defaults to the system temp dir; tests pass an isolated directory.
    """
    return Path(tempfile.mkdtemp(prefix=TEMP_PREFIX, dir=str(root) if root else None))


def stale_session_tmpdirs(exclude: Path | None = None, root: Path | None = None) -> list[Path]:
    """Leftover GUI working directories from other or dead sessions.

    Returns every ``lexo_*`` directory under `root` (the system temp dir by
    default) except `exclude` (the caller's own live session).
    """
    base = root if root is not None else Path(tempfile.gettempdir())
    skip = exclude.resolve() if exclude is not None else None
    found: list[Path] = []
    for child in base.glob(f"{TEMP_PREFIX}*"):
        if not child.is_dir():
            continue
        if skip is not None and child.resolve() == skip:
            continue
        found.append(child)
    return found


def dir_size(path: Path) -> int:
    """Total size in bytes of all files under `path` (best effort)."""
    total = 0
    for child in path.rglob("*"):
        try:
            if child.is_file() and not child.is_symlink():
                total += child.stat().st_size
        except OSError:
            continue
    return total


def purge_session_tmpdirs(exclude: Path | None = None, root: Path | None = None) -> tuple[int, int]:
    """Remove stale GUI working directories. Returns (folders removed, bytes freed)."""
    removed = 0
    freed = 0
    for directory in stale_session_tmpdirs(exclude, root=root):
        size = dir_size(directory)
        shutil.rmtree(directory, ignore_errors=True)
        if not directory.exists():
            removed += 1
            freed += size
    return removed, freed


def bundled_font(filename: str) -> Path:
    """Filesystem path to a bundled Myanmar font (package data)."""
    return Path(str(resources.files("lexo.assets.fonts").joinpath(filename)))


def bundled_asset(filename: str) -> Path:
    """Filesystem path to a bundled asset, e.g. the app logo (package data)."""
    return Path(str(resources.files("lexo.assets").joinpath(filename)))


def bundled_icon(filename: str) -> Path:
    """Filesystem path to a bundled icon resource (the Material Icons font/codepoints)."""
    return Path(str(resources.files("lexo.assets.icons").joinpath(filename)))
