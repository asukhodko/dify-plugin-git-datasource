"""
Property-based tests for file filtering.

Tests Properties 3, 4 from design document.
"""

import pytest
from hypothesis import given, strategies as st, settings

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from utils.filtering import (
    filter_by_subdir,
    filter_by_extensions,
    parse_extensions,
)


# Strategies for generating test data
file_extensions = st.sampled_from(
    [".md", ".txt", ".rst", ".py", ".js", ".html", ".json"]
)
file_names = st.from_regex(r"[a-z0-9_-]{1,20}", fullmatch=True)
dir_names = st.from_regex(r"[a-z0-9_-]{1,15}", fullmatch=True)


# Generate file paths
@st.composite
def file_paths(draw):
    """Generate realistic file paths."""
    depth = draw(st.integers(min_value=0, max_value=4))
    parts = [draw(dir_names) for _ in range(depth)]
    name = draw(file_names)
    ext = draw(file_extensions)

    if parts:
        return "/".join(parts) + "/" + name + ext
    return name + ext


# Generate lists of file paths
file_path_lists = st.lists(file_paths(), min_size=0, max_size=20)


# **Feature: git-datasource-plugin, Property 3: Subdirectory Filtering**
# **Validates: Requirements 2.2**
@given(paths=file_path_lists, subdir=dir_names)
@settings(max_examples=200)
def test_subdirectory_filtering(paths: list[str], subdir: str):
    """
    For any list of file paths and any subdirectory filter,
    all files returned by the filter function SHALL have paths
    that start with the specified subdirectory prefix.
    """
    filtered = filter_by_subdir(paths, subdir)

    # All filtered paths should start with subdir
    normalized_subdir = subdir.strip("/") + "/"
    for path in filtered:
        normalized_path = path.lstrip("/")
        assert normalized_path.startswith(normalized_subdir), (
            f"Path '{path}' does not start with '{subdir}/'"
        )


# **Feature: git-datasource-plugin, Property 3: Subdirectory Filtering - Empty**
# **Validates: Requirements 2.2**
@given(paths=file_path_lists)
@settings(max_examples=100)
def test_subdirectory_filtering_empty(paths: list[str]):
    """
    When subdirectory filter is empty, all paths should be returned.
    """
    filtered = filter_by_subdir(paths, "")
    assert filtered == paths

    filtered = filter_by_subdir(paths, "  ")
    assert filtered == paths


# **Feature: git-datasource-plugin, Property 3: Subdirectory Filtering - Subset**
# **Validates: Requirements 2.2**
@given(paths=file_path_lists, subdir=dir_names)
@settings(max_examples=200)
def test_subdirectory_filtering_subset(paths: list[str], subdir: str):
    """
    Filtered result should be a subset of original paths.
    """
    filtered = filter_by_subdir(paths, subdir)

    for path in filtered:
        assert path in paths


# **Feature: git-datasource-plugin, Property 4: Extension Filtering**
# **Validates: Requirements 2.3**
@given(
    paths=file_path_lists, extensions=st.lists(file_extensions, min_size=1, max_size=3)
)
@settings(max_examples=200)
def test_extension_filtering(paths: list[str], extensions: list[str]):
    """
    For any list of file paths and any set of extension filters,
    all files returned by the filter function SHALL have extensions
    matching one of the specified filters.
    """
    filtered = filter_by_extensions(paths, extensions)

    # Normalize extensions for comparison
    normalized_exts = [ext.lower() for ext in extensions]

    for path in filtered:
        path_lower = path.lower()
        matches = any(path_lower.endswith(ext) for ext in normalized_exts)
        assert matches, f"Path '{path}' does not match any extension in {extensions}"


# **Feature: git-datasource-plugin, Property 4: Extension Filtering - Empty**
# **Validates: Requirements 2.3**
@given(paths=file_path_lists)
@settings(max_examples=100)
def test_extension_filtering_empty(paths: list[str]):
    """
    When extension filter is empty, all paths should be returned.
    """
    filtered = filter_by_extensions(paths, [])
    assert filtered == paths


# **Feature: git-datasource-plugin, Property 4: Extension Filtering - Subset**
# **Validates: Requirements 2.3**
@given(
    paths=file_path_lists, extensions=st.lists(file_extensions, min_size=1, max_size=3)
)
@settings(max_examples=200)
def test_extension_filtering_subset(paths: list[str], extensions: list[str]):
    """
    Filtered result should be a subset of original paths.
    """
    filtered = filter_by_extensions(paths, extensions)

    for path in filtered:
        assert path in paths


# **Feature: git-datasource-plugin, Extension Parsing**
# **Validates: Requirements 2.3**
def test_parse_extensions():
    """
    Extension parsing should normalize extensions correctly.
    """
    # With dots
    assert parse_extensions(".md,.txt") == [".md", ".txt"]

    # Without dots
    assert parse_extensions("md,txt") == [".md", ".txt"]

    # Mixed
    assert parse_extensions(".md,txt,.rst") == [".md", ".txt", ".rst"]

    # With spaces
    assert parse_extensions(" .md , .txt ") == [".md", ".txt"]

    # Empty
    assert parse_extensions("") == []
    assert parse_extensions("  ") == []


# **Feature: git-datasource-plugin, Extension Parsing - Case**
# **Validates: Requirements 2.3**
@given(ext=file_extensions)
@settings(max_examples=100)
def test_parse_extensions_case(ext: str):
    """
    Extension parsing should be case-insensitive.
    """
    upper = ext.upper()
    lower = ext.lower()

    parsed_upper = parse_extensions(upper)
    parsed_lower = parse_extensions(lower)

    # Both should produce lowercase
    assert parsed_upper == parsed_lower
    assert all(e.islower() or e == "." for e in parsed_upper[0])


# **Feature: git-datasource-plugin, Combined Filtering**
# **Validates: Requirements 2.2, 2.3**
@given(
    paths=file_path_lists,
    subdir=dir_names,
    extensions=st.lists(file_extensions, min_size=1, max_size=3),
)
@settings(max_examples=200)
def test_combined_filtering(paths: list[str], subdir: str, extensions: list[str]):
    """
    Combined filtering should satisfy both constraints.
    """
    # Apply both filters
    filtered_subdir = filter_by_subdir(paths, subdir)
    filtered_both = filter_by_extensions(filtered_subdir, extensions)

    # All results should match both filters
    normalized_subdir = subdir.strip("/") + "/"
    normalized_exts = [ext.lower() for ext in extensions]

    for path in filtered_both:
        # Should match subdir
        normalized_path = path.lstrip("/")
        assert normalized_path.startswith(normalized_subdir)

        # Should match extension
        path_lower = path.lower()
        assert any(path_lower.endswith(ext) for ext in normalized_exts)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
