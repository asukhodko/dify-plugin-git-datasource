"""
Property-based tests for storage key generation.

Tests Property 17 from design document.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from utils.storage_utils import generate_storage_key, is_valid_storage_key


# Strategies for generating test data
repo_urls = st.sampled_from(
    [
        "https://github.com/user/repo.git",
        "https://gitlab.com/org/project.git",
        "git@github.com:user/repo.git",
        "/home/user/repos/local",
    ]
)

branches = st.sampled_from(["main", "master", "develop", "feature/test", "v1.0"])
subdirs = st.sampled_from(["", "docs", "src/main", "content/posts"])
extensions = st.sampled_from(["", ".md", ".md,.txt", ".md,.txt,.rst"])


# **Feature: git-datasource-plugin, Property 17: Storage Key Uniqueness**
# **Validates: Requirements 11.1, 11.2**
@given(
    url1=repo_urls,
    url2=repo_urls,
    branch1=branches,
    branch2=branches,
    subdir1=subdirs,
    subdir2=subdirs,
    ext1=extensions,
    ext2=extensions,
)
@settings(max_examples=500)
def test_storage_key_uniqueness(
    url1: str,
    url2: str,
    branch1: str,
    branch2: str,
    subdir1: str,
    subdir2: str,
    ext1: str,
    ext2: str,
):
    """
    For any two configurations with different values of
    (repo_url, branch, subdir, extensions),
    the generated storage keys SHALL be different.
    """
    # Skip if all params are the same
    same_config = (
        url1 == url2 and branch1 == branch2 and subdir1 == subdir2 and ext1 == ext2
    )
    assume(not same_config)

    key1 = generate_storage_key(url1, branch1, subdir1, ext1)
    key2 = generate_storage_key(url2, branch2, subdir2, ext2)

    assert key1 != key2, (
        f"Keys should be different for different configs:\n"
        f"Config 1: url={url1}, branch={branch1}, subdir={subdir1}, ext={ext1}\n"
        f"Config 2: url={url2}, branch={branch2}, subdir={subdir2}, ext={ext2}\n"
        f"Key 1: {key1}\n"
        f"Key 2: {key2}"
    )


# **Feature: git-datasource-plugin, Property 17: Storage Key Consistency**
# **Validates: Requirements 11.1, 11.2**
@given(url=repo_urls, branch=branches, subdir=subdirs, ext=extensions)
@settings(max_examples=200)
def test_storage_key_consistency(url: str, branch: str, subdir: str, ext: str):
    """
    Same configuration should always produce the same key.
    """
    key1 = generate_storage_key(url, branch, subdir, ext)
    key2 = generate_storage_key(url, branch, subdir, ext)

    assert key1 == key2


# **Feature: git-datasource-plugin, Storage Key Format**
# **Validates: Requirements 11.1**
@given(url=repo_urls, branch=branches, subdir=subdirs, ext=extensions)
@settings(max_examples=200)
def test_storage_key_format(url: str, branch: str, subdir: str, ext: str):
    """
    Storage key should have valid format.
    """
    key = generate_storage_key(url, branch, subdir, ext)

    # Should start with prefix
    assert key.startswith("git_browse:")

    # Should be valid
    assert is_valid_storage_key(key)

    # Hash part should be 16 hex chars
    hash_part = key.split(":")[1]
    assert len(hash_part) == 16
    int(hash_part, 16)  # Should not raise


# **Feature: git-datasource-plugin, Storage Key - URL Change**
# **Validates: Requirements 11.2**
@given(branch=branches, subdir=subdirs, ext=extensions)
@settings(max_examples=100)
def test_storage_key_url_change(branch: str, subdir: str, ext: str):
    """
    Changing repo_url should produce different key.
    """
    key1 = generate_storage_key(
        "https://github.com/user/repo1.git", branch, subdir, ext
    )
    key2 = generate_storage_key(
        "https://github.com/user/repo2.git", branch, subdir, ext
    )

    assert key1 != key2


# **Feature: git-datasource-plugin, Storage Key - Branch Change**
# **Validates: Requirements 11.2**
@given(url=repo_urls, subdir=subdirs, ext=extensions)
@settings(max_examples=100)
def test_storage_key_branch_change(url: str, subdir: str, ext: str):
    """
    Changing branch should produce different key.
    """
    key1 = generate_storage_key(url, "main", subdir, ext)
    key2 = generate_storage_key(url, "develop", subdir, ext)

    assert key1 != key2


# **Feature: git-datasource-plugin, Storage Key - Subdir Change**
# **Validates: Requirements 11.2**
@given(url=repo_urls, branch=branches, ext=extensions)
@settings(max_examples=100)
def test_storage_key_subdir_change(url: str, branch: str, ext: str):
    """
    Changing subdir should produce different key.
    """
    key1 = generate_storage_key(url, branch, "", ext)
    key2 = generate_storage_key(url, branch, "docs", ext)

    assert key1 != key2


# **Feature: git-datasource-plugin, Storage Key - Extensions Change**
# **Validates: Requirements 11.2**
@given(url=repo_urls, branch=branches, subdir=subdirs)
@settings(max_examples=100)
def test_storage_key_extensions_change(url: str, branch: str, subdir: str):
    """
    Changing extensions should produce different key.
    """
    key1 = generate_storage_key(url, branch, subdir, "")
    key2 = generate_storage_key(url, branch, subdir, ".md")

    assert key1 != key2


# **Feature: git-datasource-plugin, Storage Key - Normalization**
# **Validates: Requirements 11.1**
def test_storage_key_normalization():
    """
    Storage key should normalize inputs.
    """
    # Trailing slashes in subdir should be normalized
    key1 = generate_storage_key("https://github.com/u/r.git", "main", "docs", "")
    key2 = generate_storage_key("https://github.com/u/r.git", "main", "docs/", "")
    key3 = generate_storage_key("https://github.com/u/r.git", "main", "/docs/", "")

    assert key1 == key2 == key3

    # Whitespace should be normalized
    key4 = generate_storage_key("https://github.com/u/r.git", "main", "  docs  ", "")
    assert key1 == key4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
