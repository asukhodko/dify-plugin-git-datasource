"""
MIME type detection utilities.
"""

import mimetypes
from typing import Optional


# Additional MIME types not in standard library
EXTRA_MIME_TYPES = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".rst": "text/x-rst",
    ".yaml": "text/yaml",
    ".yml": "text/yaml",
    ".toml": "text/toml",
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
    ".tsx": "text/typescript-jsx",
    ".jsx": "text/javascript-jsx",
    ".vue": "text/x-vue",
    ".svelte": "text/x-svelte",
    ".astro": "text/x-astro",
    ".mdx": "text/mdx",
}

# Default MIME type for unknown files
DEFAULT_MIME_TYPE = "text/plain"


def get_mime_type(file_path: str) -> str:
    """
    Get MIME type for a file based on its extension.

    Args:
        file_path: Path to file (only extension is used)

    Returns:
        MIME type string (e.g., "text/markdown")
    """
    if not file_path:
        return DEFAULT_MIME_TYPE

    # Get extension
    ext = ""
    if "." in file_path:
        ext = "." + file_path.rsplit(".", 1)[-1].lower()

    # Check our extra types first
    if ext in EXTRA_MIME_TYPES:
        return EXTRA_MIME_TYPES[ext]

    # Use standard library
    mime_type, _ = mimetypes.guess_type(file_path)

    if mime_type:
        return mime_type

    return DEFAULT_MIME_TYPE


def is_text_file(file_path: str) -> bool:
    """
    Check if a file is likely a text file based on MIME type.

    Args:
        file_path: Path to file

    Returns:
        True if file is likely text-based
    """
    mime_type = get_mime_type(file_path)

    # Text types
    if mime_type.startswith("text/"):
        return True

    # Common text-based application types
    text_application_types = {
        "application/json",
        "application/xml",
        "application/javascript",
        "application/x-javascript",
        "application/typescript",
        "application/x-sh",
        "application/x-ndjson",
    }

    return mime_type in text_application_types


def get_extension_for_mime(mime_type: str) -> Optional[str]:
    """
    Get file extension for a MIME type.

    Args:
        mime_type: MIME type string

    Returns:
        File extension (with dot) or None if unknown
    """
    # Check our extra types
    for ext, mt in EXTRA_MIME_TYPES.items():
        if mt == mime_type:
            return ext

    # Use standard library
    ext = mimetypes.guess_extension(mime_type)
    return ext
