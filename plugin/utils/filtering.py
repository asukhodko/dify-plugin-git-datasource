"""
File filtering utilities.
"""

from typing import Sequence


def parse_extensions(extensions_str: str) -> list[str]:
    """
    Parse comma-separated extensions string into list.

    Args:
        extensions_str: Comma-separated extensions (e.g., ".md,.txt,.rst")

    Returns:
        List of normalized extensions (lowercase, with leading dot)
    """
    if not extensions_str:
        return []

    extensions = []
    for ext in extensions_str.split(","):
        ext = ext.strip().lower()
        if ext:
            # Ensure leading dot
            if not ext.startswith("."):
                ext = "." + ext
            extensions.append(ext)

    return extensions


def filter_by_extensions(
    paths: Sequence[str],
    extensions: Sequence[str],
) -> list[str]:
    """
    Filter file paths by extensions.

    Args:
        paths: List of file paths
        extensions: List of allowed extensions (e.g., [".md", ".txt"])
                   Empty list means allow all files.

    Returns:
        List of paths matching the extensions filter
    """
    if not extensions:
        return list(paths)

    # Normalize extensions
    normalized_exts = [
        ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions
    ]

    result = []
    for path in paths:
        path_lower = path.lower()
        if any(path_lower.endswith(ext) for ext in normalized_exts):
            result.append(path)

    return result


def filter_by_subdir(
    paths: Sequence[str],
    subdir: str,
) -> list[str]:
    """
    Filter file paths by subdirectory prefix.

    Args:
        paths: List of file paths
        subdir: Subdirectory prefix (e.g., "docs/")
                Empty string means no filtering.

    Returns:
        List of paths within the subdirectory
    """
    if not subdir or not subdir.strip():
        return list(paths)

    # Normalize subdir - ensure no leading slash, has trailing slash
    subdir = subdir.strip().strip("/")
    if not subdir:
        return list(paths)

    subdir = subdir + "/"

    result = []
    for path in paths:
        # Normalize path - remove leading slash if present
        normalized_path = path.lstrip("/")
        if normalized_path.startswith(subdir):
            result.append(path)

    return result


def matches_extension(path: str, extensions: Sequence[str]) -> bool:
    """
    Check if a path matches any of the given extensions.

    Args:
        path: File path to check
        extensions: List of allowed extensions

    Returns:
        True if path matches any extension, or if extensions is empty
    """
    if not extensions:
        return True

    path_lower = path.lower()
    for ext in extensions:
        ext_lower = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
        if path_lower.endswith(ext_lower):
            return True

    return False


def matches_subdir(path: str, subdir: str) -> bool:
    """
    Check if a path is within the given subdirectory.

    Args:
        path: File path to check
        subdir: Subdirectory prefix

    Returns:
        True if path is within subdir, or if subdir is empty
    """
    if not subdir:
        return True

    # Normalize
    subdir = subdir.strip("/")
    if not subdir:
        return True

    subdir = subdir + "/"
    normalized_path = path.lstrip("/")

    return normalized_path.startswith(subdir)


def get_relative_path(path: str, subdir: str) -> str:
    """
    Get path relative to subdirectory.

    Args:
        path: Full file path
        subdir: Subdirectory prefix

    Returns:
        Path relative to subdir, or original path if not in subdir
    """
    if not subdir:
        return path

    # Normalize
    subdir = subdir.strip("/")
    if not subdir:
        return path

    subdir = subdir + "/"
    normalized_path = path.lstrip("/")

    if normalized_path.startswith(subdir):
        return normalized_path[len(subdir) :]

    return path
