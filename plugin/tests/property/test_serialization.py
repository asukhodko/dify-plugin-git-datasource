"""
Property-based tests for serialization round-trips.

Tests Properties 14, 15 from design document.
"""

import pytest
from hypothesis import given, strategies as st, settings

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from utils.models import FileInfo, ChangeSet


# Strategies for generating test data
file_names = st.from_regex(r"[a-zA-Z0-9_-]+\.[a-z]{1,4}", fullmatch=True)
file_paths = st.from_regex(
    r"[a-zA-Z0-9_-]+(/[a-zA-Z0-9_-]+)*\.[a-z]{1,4}", fullmatch=True
)
valid_shas = st.from_regex(r"[0-9a-f]{40}", fullmatch=True)

file_infos = st.builds(
    FileInfo,
    path=file_paths,
    name=file_names,
    size=st.integers(min_value=0, max_value=10_000_000),
    type=st.sampled_from(["file", "folder"]),
)

changesets = st.builds(
    ChangeSet,
    added=st.lists(file_paths, max_size=10),
    modified=st.lists(file_paths, max_size=10),
    deleted=st.lists(file_paths, max_size=10),
    renamed=st.lists(st.tuples(file_paths, file_paths), max_size=5),
)


# **Feature: git-datasource-plugin, Property 15: FileInfo Serialization Round-Trip**
# **Validates: Requirements 9.3**
@given(file_info=file_infos)
@settings(max_examples=200)
def test_fileinfo_serialization_roundtrip(file_info: FileInfo):
    """
    For any valid FileInfo object, serializing to JSON and deserializing back
    SHALL produce an equivalent FileInfo object.
    """
    # Serialize to JSON
    json_str = file_info.to_json()

    # Deserialize back
    restored = FileInfo.from_json(json_str)

    # Should be equivalent
    assert restored.path == file_info.path
    assert restored.name == file_info.name
    assert restored.size == file_info.size
    assert restored.type == file_info.type


# **Feature: git-datasource-plugin, Property 15: FileInfo Serialization Round-Trip (dict)**
# **Validates: Requirements 9.3**
@given(file_info=file_infos)
@settings(max_examples=200)
def test_fileinfo_dict_roundtrip(file_info: FileInfo):
    """
    For any valid FileInfo object, converting to dict and back
    SHALL produce an equivalent FileInfo object.
    """
    # Convert to dict
    data = file_info.to_dict()

    # Convert back
    restored = FileInfo.from_dict(data)

    # Should be equivalent
    assert restored == file_info


# **Feature: git-datasource-plugin, Property 14: SHA Serialization Round-Trip**
# **Validates: Requirements 9.1, 9.2**
@given(sha=valid_shas)
@settings(max_examples=200)
def test_sha_serialization_roundtrip(sha: str):
    """
    For any valid SHA string, serializing it to bytes (UTF-8) and deserializing back
    SHALL produce the original SHA string.
    """
    # Serialize to bytes
    sha_bytes = sha.encode("utf-8")

    # Deserialize back
    restored = sha_bytes.decode("utf-8")

    # Should be identical
    assert restored == sha


# **Feature: git-datasource-plugin, ChangeSet Serialization Round-Trip**
# **Validates: Requirements 9.3**
@given(changeset=changesets)
@settings(max_examples=200)
def test_changeset_serialization_roundtrip(changeset: ChangeSet):
    """
    For any valid ChangeSet object, serializing to JSON and deserializing back
    SHALL produce an equivalent ChangeSet object.
    """
    # Serialize to JSON
    json_str = changeset.to_json()

    # Deserialize back
    restored = ChangeSet.from_json(json_str)

    # Should be equivalent
    assert restored.added == changeset.added
    assert restored.modified == changeset.modified
    assert restored.deleted == changeset.deleted
    assert restored.renamed == changeset.renamed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
