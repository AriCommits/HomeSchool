from __future__ import annotations

from pathlib import Path, PurePath


def is_path_within_directory(path: Path, directory: Path) -> bool:
    """Return True when `path` resolves inside `directory`."""
    try:
        resolved_path = path.resolve(strict=False)
        resolved_directory = directory.resolve(strict=False)
        resolved_path.relative_to(resolved_directory)
        return True
    except (ValueError, RuntimeError, OSError):
        return False


def is_safe_relative_subpath(subpath: str) -> bool:
    """Validate a configured vault subpath."""
    if subpath is None:
        return False

    candidate = str(subpath).strip()
    if candidate == "":
        return True

    pure = PurePath(candidate)
    if pure.is_absolute():
        return False

    return ".." not in pure.parts
