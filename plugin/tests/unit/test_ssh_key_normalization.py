"""
Unit tests for SSH key normalization.

These tests ensure that SSH private keys are correctly normalized
regardless of how they are passed through the UI (which may mangle newlines).
"""

import os
import pytest

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from git_client import GitClient


# Sample RSA key structure (not a real key, just for format testing)
SAMPLE_RSA_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEoAIBAAJBAKj34GkxFhD90vcNLYLInFEX6Ppy1tPf9Cnzj4p4WGeKLs1Pt8Qu
KUpRKfFLfRYC9AIKjbJTWit+CqvjWYzvQwECAwEAAQJAIJLixBy2qpFoS4DSmoEm
o3qGy0t6z09AIJtH+5OeRV1be+N4cDYJKffGzDa88vQENZiRm0GRq6a+HPGQMd2k
TQIhAKMSvzIBnni7ot/OSie2TmJLY4SwTQAevXysE2RbFDYdAiEBCUEaRQnMnHRE
M/VDQIjByM0A5OdqfvD8WBSsLWUCoiMCIBSoGnls+Bczjnpu/Kl/3mH2H/MC3qoJ
e5QK7+IxtRJ1AiEAz0YhASM6l3NRSvj6VivhxGPL6zcU3LnWnXl8CuN/ovECIQCb
Z1/ENvmlJ/P7N9Exj2NCtEYxd0Q5cwBZ5NfZeMBpwQ==
-----END RSA PRIVATE KEY-----"""


class TestSSHKeyNormalization:
    """Tests for SSH key format normalization in GitClient."""

    def test_key_with_literal_backslash_n(self):
        """
        Key with literal \\n (two characters) should be converted to real newlines.
        This is how Dify UI passes multiline text through secret-input fields.
        """
        # Simulate how UI mangles the key
        mangled_key = SAMPLE_RSA_KEY.replace("\n", "\\n")
        
        client = GitClient(
            repo_url="git@github.com:user/repo.git",
            branch="main",
            credentials={"ssh_private_key": mangled_key},
        )
        
        # Call the normalization logic
        key_path = client._setup_ssh_environment()
        
        try:
            # Read the written key
            with open(key_path, "r") as f:
                written_key = f.read()
            
            # Should have real newlines
            assert "\\n" not in written_key
            assert written_key.startswith("-----BEGIN RSA PRIVATE KEY-----\n")
            assert written_key.strip().endswith("-----END RSA PRIVATE KEY-----")
            
            # Should have correct number of lines
            lines = written_key.strip().split("\n")
            assert len(lines) > 3  # At least BEGIN, content, END
        finally:
            client._cleanup_ssh_key(key_path)

    def test_key_with_windows_line_endings(self):
        """Key with Windows CRLF line endings should be normalized to Unix LF."""
        windows_key = SAMPLE_RSA_KEY.replace("\n", "\r\n")
        
        client = GitClient(
            repo_url="git@github.com:user/repo.git",
            branch="main",
            credentials={"ssh_private_key": windows_key},
        )
        
        key_path = client._setup_ssh_environment()
        
        try:
            with open(key_path, "r") as f:
                written_key = f.read()
            
            # Should not have CRLF
            assert "\r\n" not in written_key
            assert "\r" not in written_key
            # Should have Unix newlines
            assert "\n" in written_key
        finally:
            client._cleanup_ssh_key(key_path)

    def test_key_with_extra_whitespace(self):
        """Key with extra whitespace should be trimmed."""
        padded_key = "  \n\n" + SAMPLE_RSA_KEY + "\n\n  "
        
        client = GitClient(
            repo_url="git@github.com:user/repo.git",
            branch="main",
            credentials={"ssh_private_key": padded_key},
        )
        
        key_path = client._setup_ssh_environment()
        
        try:
            with open(key_path, "r") as f:
                written_key = f.read()
            
            # Should start with BEGIN (no leading whitespace)
            assert written_key.startswith("-----BEGIN")
            # Should end with newline after END
            assert written_key.endswith("-----END RSA PRIVATE KEY-----\n")
        finally:
            client._cleanup_ssh_key(key_path)

    def test_key_already_correct_format(self):
        """Key already in correct format should remain unchanged (except trailing newline)."""
        client = GitClient(
            repo_url="git@github.com:user/repo.git",
            branch="main",
            credentials={"ssh_private_key": SAMPLE_RSA_KEY},
        )
        
        key_path = client._setup_ssh_environment()
        
        try:
            with open(key_path, "r") as f:
                written_key = f.read()
            
            # Should be essentially the same
            assert written_key.strip() == SAMPLE_RSA_KEY.strip()
        finally:
            client._cleanup_ssh_key(key_path)

    def test_key_file_permissions(self):
        """Key file should have 0600 permissions (owner read/write only)."""
        client = GitClient(
            repo_url="git@github.com:user/repo.git",
            branch="main",
            credentials={"ssh_private_key": SAMPLE_RSA_KEY},
        )
        
        key_path = client._setup_ssh_environment()
        
        try:
            # Check permissions
            mode = os.stat(key_path).st_mode & 0o777
            assert mode == 0o600, f"Expected 0600, got {oct(mode)}"
        finally:
            client._cleanup_ssh_key(key_path)

    def test_no_key_returns_none(self):
        """When no SSH key is provided, should return None."""
        client = GitClient(
            repo_url="git@github.com:user/repo.git",
            branch="main",
            credentials={},
        )
        
        key_path = client._setup_ssh_environment()
        assert key_path is None

    def test_empty_key_returns_none(self):
        """When SSH key is empty string, should return None."""
        client = GitClient(
            repo_url="git@github.com:user/repo.git",
            branch="main",
            credentials={"ssh_private_key": ""},
        )
        
        key_path = client._setup_ssh_environment()
        assert key_path is None

    def test_cleanup_removes_file(self):
        """Cleanup should remove the temporary key file."""
        client = GitClient(
            repo_url="git@github.com:user/repo.git",
            branch="main",
            credentials={"ssh_private_key": SAMPLE_RSA_KEY},
        )
        
        key_path = client._setup_ssh_environment()
        assert os.path.exists(key_path)
        
        client._cleanup_ssh_key(key_path)
        assert not os.path.exists(key_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
