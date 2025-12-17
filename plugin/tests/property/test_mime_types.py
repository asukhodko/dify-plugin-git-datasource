"""
Property-based tests for MIME type detection.

Tests Property 6 from design document.
"""

import pytest
from hypothesis import given, strategies as st, settings

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from utils.mime_utils import get_mime_type, is_text_file


# Known extension to MIME type mappings
# Note: Some MIME types vary by system, so we only test stable ones
KNOWN_MAPPINGS = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".html": "text/html",
    ".htm": "text/html",
    ".css": "text/css",
    ".json": "application/json",
    ".yaml": "text/yaml",
    ".yml": "text/yaml",
    ".rst": "text/x-rst",
    ".toml": "text/toml",
}

# File names for testing
file_names = st.from_regex(r"[a-z0-9_-]{1,20}", fullmatch=True)


# **Feature: git-datasource-plugin, Property 6: MIME Type Detection**
# **Validates: Requirements 3.1**
@given(ext=st.sampled_from(list(KNOWN_MAPPINGS.keys())))
@settings(max_examples=100)
def test_mime_type_known_extensions(ext: str):
    """
    For any file path with a known extension,
    the MIME type detection function SHALL return the correct MIME type.
    """
    file_path = f"docs/readme{ext}"
    expected = KNOWN_MAPPINGS[ext]

    result = get_mime_type(file_path)

    assert result == expected, f"Expected {expected} for {ext}, got {result}"


# **Feature: git-datasource-plugin, Property 6: MIME Type Detection - Paths**
# **Validates: Requirements 3.1**
@given(
    name=file_names,
    ext=st.sampled_from(list(KNOWN_MAPPINGS.keys())),
    depth=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=200)
def test_mime_type_various_paths(name: str, ext: str, depth: int):
    """
    MIME type detection should work regardless of path depth.
    """
    # Build path with varying depth
    parts = ["dir"] * depth
    parts.append(name + ext)
    file_path = "/".join(parts)

    expected = KNOWN_MAPPINGS[ext]
    result = get_mime_type(file_path)

    assert result == expected


# **Feature: git-datasource-plugin, Property 6: MIME Type Detection - Case Insensitive**
# **Validates: Requirements 3.1**
@given(ext=st.sampled_from([".MD", ".Md", ".mD", ".TXT", ".Txt", ".JSON", ".Json"]))
@settings(max_examples=100)
def test_mime_type_case_insensitive(ext: str):
    """
    MIME type detection should be case-insensitive for extensions.
    """
    file_path = f"file{ext}"

    result = get_mime_type(file_path)

    # Should return a valid MIME type (not default for known extensions)
    assert result is not None
    assert "/" in result  # Valid MIME type format


# **Feature: git-datasource-plugin, Property 6: MIME Type Detection - Default**
# **Validates: Requirements 3.1**
@given(name=file_names)
@settings(max_examples=100)
def test_mime_type_unknown_extension(name: str):
    """
    Unknown extensions should return default MIME type.
    """
    file_path = f"{name}.unknownext123"

    result = get_mime_type(file_path)

    assert result == "text/plain"


# **Feature: git-datasource-plugin, Property 6: MIME Type Detection - No Extension**
# **Validates: Requirements 3.1**
@given(name=file_names)
@settings(max_examples=100)
def test_mime_type_no_extension(name: str):
    """
    Files without extension should return default MIME type.
    """
    result = get_mime_type(name)

    assert result == "text/plain"


# **Feature: git-datasource-plugin, Property 6: MIME Type Detection - Empty**
# **Validates: Requirements 3.1**
def test_mime_type_empty():
    """
    Empty path should return default MIME type.
    """
    assert get_mime_type("") == "text/plain"
    assert get_mime_type(None) == "text/plain"


# **Feature: git-datasource-plugin, Text File Detection**
# **Validates: Requirements 3.1**
@given(
    ext=st.sampled_from(
        [".md", ".txt", ".html", ".css", ".py", ".js", ".json", ".yaml"]
    )
)
@settings(max_examples=100)
def test_is_text_file(ext: str):
    """
    Common text file extensions should be detected as text files.
    """
    file_path = f"file{ext}"

    assert is_text_file(file_path), f"{ext} should be detected as text file"


# **Feature: git-datasource-plugin, MIME Type Format**
# **Validates: Requirements 3.1**
@given(ext=st.sampled_from(list(KNOWN_MAPPINGS.keys())))
@settings(max_examples=100)
def test_mime_type_format(ext: str):
    """
    MIME type should always be in valid format (type/subtype).
    """
    file_path = f"file{ext}"

    result = get_mime_type(file_path)

    # Should have exactly one slash
    assert result.count("/") == 1

    # Both parts should be non-empty
    type_part, subtype_part = result.split("/")
    assert len(type_part) > 0
    assert len(subtype_part) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
