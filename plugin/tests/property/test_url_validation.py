"""
Property-based tests for URL validation.

Tests Properties 1, 10, 11 from design document.
"""

import pytest
from hypothesis import given, strategies as st, settings

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from utils.url_utils import validate_repo_url, get_url_type, build_auth_url


# Strategies for generating test data
valid_https_urls = st.sampled_from(
    [
        "https://github.com/user/repo.git",
        "https://github.com/user/repo",
        "https://gitlab.com/user/project.git",
        "https://gitea.example.com/org/repo.git",
        "https://git.example.com:8443/user/repo.git",
        "http://localhost/user/repo.git",
    ]
)

valid_ssh_urls = st.sampled_from(
    [
        "git@github.com:user/repo.git",
        "git@gitlab.com:user/project.git",
        "git@git.example.com:org/repo.git",
        "ssh://git@github.com/user/repo.git",
        "ssh://git@gitlab.com:22/user/repo.git",
    ]
)

valid_local_paths = st.sampled_from(
    [
        "/home/user/repos/myrepo",
        "/var/git/repo.git",
        "file:///home/user/repos/myrepo",
        "/tmp/test-repo",
    ]
)

invalid_urls = st.sampled_from(
    [
        "",
        "not-a-url",
        "ftp://example.com/repo.git",
        "git://github.com/user/repo.git",  # git:// not supported
        "github.com/user/repo",  # missing protocol
        "user@host",  # incomplete SSH
    ]
)

# Random strings that are unlikely to be valid URLs
random_strings = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)), min_size=1, max_size=50
).filter(
    lambda s: not s.startswith(
        ("https://", "http://", "git@", "ssh://", "/", "file://")
    )
)

access_tokens = st.from_regex(r"[a-zA-Z0-9_-]{20,50}", fullmatch=True)


# **Feature: git-datasource-plugin, Property 1: Invalid URL Rejection**
# **Validates: Requirements 1.2**
@given(url=invalid_urls)
@settings(max_examples=100)
def test_invalid_url_rejection_known_invalid(url: str):
    """
    For known invalid URLs, validation SHALL reject them.
    """
    is_valid, error_msg = validate_repo_url(url)
    assert not is_valid
    assert error_msg  # Should have error message


# **Feature: git-datasource-plugin, Property 1: Invalid URL Rejection**
# **Validates: Requirements 1.2**
@given(url=random_strings)
@settings(max_examples=200)
def test_invalid_url_rejection_random(url: str):
    """
    For random strings that don't match valid patterns,
    validation SHALL reject them with an error message.
    """
    is_valid, error_msg = validate_repo_url(url)
    assert not is_valid
    assert error_msg  # Should have error message


# **Feature: git-datasource-plugin, Valid HTTPS URLs**
# **Validates: Requirements 1.2**
@given(url=valid_https_urls)
@settings(max_examples=100)
def test_valid_https_urls_accepted(url: str):
    """
    Valid HTTPS URLs SHALL be accepted.
    """
    is_valid, error_msg = validate_repo_url(url)
    assert is_valid
    assert error_msg == ""


# **Feature: git-datasource-plugin, Valid SSH URLs**
# **Validates: Requirements 1.2**
@given(url=valid_ssh_urls)
@settings(max_examples=100)
def test_valid_ssh_urls_accepted(url: str):
    """
    Valid SSH URLs SHALL be accepted.
    """
    is_valid, error_msg = validate_repo_url(url)
    assert is_valid
    assert error_msg == ""


# **Feature: git-datasource-plugin, Property 11: Local Path Detection**
# **Validates: Requirements 6.4**
@given(path=valid_local_paths)
@settings(max_examples=100)
def test_local_path_detection(path: str):
    """
    For any path starting with "/" or "file://",
    the URL type detection function SHALL classify it as a local repository.
    """
    url_type = get_url_type(path)
    assert url_type == "local"


# **Feature: git-datasource-plugin, Property 11: Local Path Detection**
# **Validates: Requirements 6.4**
@given(path=st.from_regex(r"/[a-zA-Z0-9_/-]+", fullmatch=True))
@settings(max_examples=200)
def test_local_path_detection_generated(path: str):
    """
    For any generated path starting with "/",
    the URL type detection function SHALL classify it as local.
    """
    url_type = get_url_type(path)
    assert url_type == "local"


# **Feature: git-datasource-plugin, HTTPS URL Type Detection**
# **Validates: Requirements 6.2**
@given(url=valid_https_urls)
@settings(max_examples=100)
def test_https_url_type_detection(url: str):
    """
    HTTPS URLs SHALL be classified as "https" type.
    """
    url_type = get_url_type(url)
    assert url_type == "https"


# **Feature: git-datasource-plugin, SSH URL Type Detection**
# **Validates: Requirements 6.3**
@given(url=valid_ssh_urls)
@settings(max_examples=100)
def test_ssh_url_type_detection(url: str):
    """
    SSH URLs SHALL be classified as "ssh" type.
    """
    url_type = get_url_type(url)
    assert url_type == "ssh"


# **Feature: git-datasource-plugin, Property 10: Token URL Construction**
# **Validates: Requirements 6.2, 7.4**
@given(url=valid_https_urls, token=access_tokens)
@settings(max_examples=200)
def test_token_url_construction(url: str, token: str):
    """
    For any HTTPS URL and access token, the constructed authenticated URL
    SHALL contain the token in the correct position and SHALL be a valid URL.
    """
    auth_url = build_auth_url(url, token)

    # Should contain token
    assert token in auth_url

    # Should have correct format: https://token:TOKEN@host/...
    assert "token:" in auth_url
    assert "@" in auth_url

    # Should still be HTTPS
    assert auth_url.startswith("https://") or auth_url.startswith("http://")


# **Feature: git-datasource-plugin, Property 10: Token URL Construction - No Token**
# **Validates: Requirements 6.2**
@given(url=valid_https_urls)
@settings(max_examples=100)
def test_token_url_construction_no_token(url: str):
    """
    When no token is provided, the URL SHALL remain unchanged.
    """
    auth_url = build_auth_url(url, None)
    assert auth_url == url

    auth_url = build_auth_url(url, "")
    assert auth_url == url


# **Feature: git-datasource-plugin, Token URL Construction - Non-HTTPS**
# **Validates: Requirements 6.2**
@given(url=valid_ssh_urls, token=access_tokens)
@settings(max_examples=100)
def test_token_url_construction_non_https(url: str, token: str):
    """
    For non-HTTPS URLs, token embedding SHALL not modify the URL.
    """
    auth_url = build_auth_url(url, token)
    assert auth_url == url  # Should be unchanged


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
