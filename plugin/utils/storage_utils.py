"""
Storage key generation utilities.
"""

import hashlib


def generate_storage_key(
    repo_url: str,
    branch: str,
    subdir: str = "",
    extensions: str = "",
) -> str:
    """
    Generate unique storage key for sync state.

    The key includes all configuration parameters to ensure
    different configurations get separate sync states.

    Args:
        repo_url: Repository URL
        branch: Branch name
        subdir: Subdirectory filter
        extensions: Extensions filter string

    Returns:
        Storage key in format "git_browse:{hash}"
    """
    # Normalize inputs
    repo_url = (repo_url or "").strip()
    branch = (branch or "main").strip()
    subdir = (subdir or "").strip().strip("/")
    extensions = (extensions or "").strip().lower()

    # Create unique key from all params
    key_parts = [
        repo_url,
        branch,
        subdir,
        extensions,
    ]
    key_string = ":".join(key_parts)

    # Hash for shorter key
    key_hash = hashlib.sha256(key_string.encode("utf-8")).hexdigest()[:16]

    return f"git_browse:{key_hash}"


def parse_storage_key(storage_key: str) -> dict:
    """
    Parse storage key to extract prefix and hash.

    Args:
        storage_key: Storage key string

    Returns:
        Dict with 'prefix' and 'hash' keys
    """
    if ":" in storage_key:
        prefix, key_hash = storage_key.split(":", 1)
        return {"prefix": prefix, "hash": key_hash}

    return {"prefix": "", "hash": storage_key}


def is_valid_storage_key(storage_key: str) -> bool:
    """
    Check if storage key has valid format.

    Args:
        storage_key: Storage key to validate

    Returns:
        True if key has valid format
    """
    if not storage_key:
        return False

    if not storage_key.startswith("git_browse:"):
        return False

    parts = storage_key.split(":")
    if len(parts) != 2:
        return False

    # Hash should be 16 hex characters
    key_hash = parts[1]
    if len(key_hash) != 16:
        return False

    try:
        int(key_hash, 16)
        return True
    except ValueError:
        return False
