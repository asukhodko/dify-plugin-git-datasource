"""
Property-based tests for credential masking.

Tests Property 2 from design document.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from utils.masking import mask_credentials, mask_url, mask_token, mask_dict


# Strategies for generating test data
tokens = st.from_regex(r"[a-zA-Z0-9_-]{10,50}", fullmatch=True)
ssh_keys = st.from_regex(
    r"-----BEGIN [A-Z ]+ KEY-----\n[a-zA-Z0-9+/=\n]{50,200}\n-----END [A-Z ]+ KEY-----",
    fullmatch=True,
)
passwords = st.from_regex(r"[a-zA-Z0-9!@#$%^&*]{8,30}", fullmatch=True)

# Text that might contain credentials
text_with_placeholder = st.from_regex(
    r"Error: [a-zA-Z ]+ \{TOKEN\} [a-zA-Z ]+", fullmatch=True
)


# **Feature: git-datasource-plugin, Property 2: Credential Masking**
# **Validates: Requirements 1.3, 7.4**
@given(token=tokens, text_template=text_with_placeholder)
@settings(max_examples=200)
def test_credential_masking_token(token: str, text_template: str):
    """
    For any credentials (access_token) and any text,
    the credentials SHALL NOT appear in plain text in the output.
    """
    # Create text containing the token
    text = text_template.replace("{TOKEN}", token)

    # Mask credentials
    credentials = {"access_token": token}
    masked = mask_credentials(text, credentials)

    # Token should not appear in masked text
    assert token not in masked
    assert "***" in masked


# **Feature: git-datasource-plugin, Property 2: Credential Masking**
# **Validates: Requirements 1.3, 7.4**
@given(password=passwords)
@settings(max_examples=200)
def test_credential_masking_password(password: str):
    """
    For any password in credentials, it SHALL NOT appear in masked output.
    """
    text = f"Connection failed with password {password} for user admin"

    credentials = {"password": password}
    masked = mask_credentials(text, credentials)

    assert password not in masked
    assert "***" in masked


# **Feature: git-datasource-plugin, Property 2: Credential Masking - Multiple**
# **Validates: Requirements 1.3, 7.4**
@given(token=tokens, password=passwords)
@settings(max_examples=200)
def test_credential_masking_multiple(token: str, password: str):
    """
    When multiple credentials are present, ALL SHALL be masked.
    """
    assume(token != password)  # Ensure they're different

    text = f"Auth failed: token={token}, password={password}"

    credentials = {
        "access_token": token,
        "password": password,
    }
    masked = mask_credentials(text, credentials)

    assert token not in masked
    assert password not in masked


# **Feature: git-datasource-plugin, Property 2: Credential Masking - URL**
# **Validates: Requirements 1.3, 7.4**
@given(token=tokens)
@settings(max_examples=200)
def test_url_masking(token: str):
    """
    URLs with embedded credentials SHALL have credentials masked.
    """
    url = f"https://token:{token}@github.com/user/repo.git"

    masked = mask_url(url)

    # Token should not appear
    assert token not in masked
    # Should have masked format
    assert "***:***@" in masked
    # Should still be a valid-looking URL
    assert masked.startswith("https://")
    assert "github.com" in masked


# **Feature: git-datasource-plugin, Property 2: Credential Masking - URL with user:pass**
# **Validates: Requirements 1.3, 7.4**
@given(user=st.from_regex(r"[a-zA-Z0-9_-]{3,20}", fullmatch=True), password=passwords)
@settings(max_examples=200)
def test_url_masking_user_password(user: str, password: str):
    """
    URLs with user:password format SHALL have both masked.
    """
    url = f"https://{user}:{password}@gitlab.com/org/repo.git"

    masked = mask_url(url)

    # Neither user nor password should appear
    assert user not in masked
    assert password not in masked
    assert "***:***@" in masked


# **Feature: git-datasource-plugin, Credential Masking - Empty**
# **Validates: Requirements 1.3, 7.4**
def test_credential_masking_empty():
    """
    Empty text or credentials should be handled gracefully.
    """
    assert mask_credentials("", {}) == ""
    assert mask_credentials("some text", {}) == "some text"
    assert mask_credentials("", {"token": "secret"}) == ""


# **Feature: git-datasource-plugin, Credential Masking - No Match**
# **Validates: Requirements 1.3, 7.4**
@given(token=tokens)
@settings(max_examples=100)
def test_credential_masking_no_match(token: str):
    """
    Text without credentials should remain unchanged.
    """
    text = "This text has no credentials"
    credentials = {"access_token": token}

    masked = mask_credentials(text, credentials)

    assert masked == text


# **Feature: git-datasource-plugin, Token Masking Display**
# **Validates: Requirements 7.4**
@given(token=tokens)
@settings(max_examples=200)
def test_token_masking_display(token: str):
    """
    Token masking for display should show only partial token.
    """
    masked = mask_token(token)

    if len(token) <= 8:
        assert masked == "***"
    else:
        # Should show first 4 and last 4 chars
        assert masked.startswith(token[:4])
        assert masked.endswith(token[-4:])
        assert "****" in masked
        # Full token should not be recoverable
        assert masked != token


# **Feature: git-datasource-plugin, Dict Masking**
# **Validates: Requirements 1.3, 7.4**
@given(token=tokens, password=passwords)
@settings(max_examples=200)
def test_dict_masking(token: str, password: str):
    """
    Dictionaries with sensitive keys should have values masked.
    """
    data = {
        "repo_url": "https://github.com/user/repo.git",
        "access_token": token,
        "password": password,
        "branch": "main",
    }

    masked = mask_dict(data)

    # Sensitive values should be masked
    assert masked["access_token"] == "***"
    assert masked["password"] == "***"

    # Non-sensitive values should remain
    assert masked["repo_url"] == data["repo_url"]
    assert masked["branch"] == data["branch"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
