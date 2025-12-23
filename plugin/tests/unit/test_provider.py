"""
Unit tests for GitDatasourceProvider.

Tests credential validation for plugin authorization.
"""

import pytest
from unittest.mock import patch, MagicMock

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


class TestCredentialValidation:
    """Tests for credential validation at plugin authorization stage."""

    def test_empty_credentials_accepted(self):
        """Empty credentials should be accepted (for public repos)."""
        from provider.git_datasource import GitDatasourceProvider

        provider = GitDatasourceProvider()
        
        # Should not raise - empty credentials are OK for public repos
        provider._validate_credentials({})
        provider._validate_credentials({"access_token": "", "ssh_private_key": ""})

    def test_valid_access_token_accepted(self):
        """Valid access token should be accepted."""
        from provider.git_datasource import GitDatasourceProvider

        provider = GitDatasourceProvider()
        
        # Should not raise
        provider._validate_credentials({"access_token": "ghp_xxxxxxxxxxxx"})
        provider._validate_credentials({"access_token": "glpat-xxxxxxxxxxxx"})

    def test_access_token_with_newlines_rejected(self):
        """Access token with newlines should be rejected."""
        from provider.git_datasource import GitDatasourceProvider
        from dify_plugin.errors.tool import ToolProviderCredentialValidationError

        provider = GitDatasourceProvider()

        with pytest.raises(ToolProviderCredentialValidationError) as exc_info:
            provider._validate_credentials({"access_token": "token\nwith\nnewlines"})

        assert "newlines" in str(exc_info.value).lower()

    def test_whitespace_only_token_rejected(self):
        """Whitespace-only access token should be rejected."""
        from provider.git_datasource import GitDatasourceProvider
        from dify_plugin.errors.tool import ToolProviderCredentialValidationError

        provider = GitDatasourceProvider()

        with pytest.raises(ToolProviderCredentialValidationError) as exc_info:
            provider._validate_credentials({"access_token": "   "})

        assert "empty" in str(exc_info.value).lower() or "whitespace" in str(exc_info.value).lower()


class TestSSHKeyValidation:
    """Tests for SSH key format validation."""

    def test_valid_rsa_key_accepted(self):
        """Valid RSA private key should be accepted."""
        from provider.git_datasource import GitDatasourceProvider

        provider = GitDatasourceProvider()
        
        valid_key = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MaXV
-----END RSA PRIVATE KEY-----"""
        
        # Should not raise
        provider._validate_credentials({"ssh_private_key": valid_key})

    def test_valid_openssh_key_accepted(self):
        """Valid OpenSSH private key should be accepted."""
        from provider.git_datasource import GitDatasourceProvider

        provider = GitDatasourceProvider()
        
        valid_key = """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAAB
-----END OPENSSH PRIVATE KEY-----"""
        
        # Should not raise
        provider._validate_credentials({"ssh_private_key": valid_key})

    def test_valid_ec_key_accepted(self):
        """Valid EC private key should be accepted."""
        from provider.git_datasource import GitDatasourceProvider

        provider = GitDatasourceProvider()
        
        valid_key = """-----BEGIN EC PRIVATE KEY-----
MHQCAQEEIBYu7jrN
-----END EC PRIVATE KEY-----"""
        
        # Should not raise
        provider._validate_credentials({"ssh_private_key": valid_key})

    def test_key_with_escaped_newlines_accepted(self):
        """Key with escaped newlines (\\n) should be accepted."""
        from provider.git_datasource import GitDatasourceProvider

        provider = GitDatasourceProvider()
        
        # This is how keys often come from UI - with literal \n
        valid_key = "-----BEGIN RSA PRIVATE KEY-----\\nMIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn\\n-----END RSA PRIVATE KEY-----"
        
        # Should not raise
        provider._validate_credentials({"ssh_private_key": valid_key})

    def test_invalid_key_no_header_rejected(self):
        """Key without proper header should be rejected."""
        from provider.git_datasource import GitDatasourceProvider
        from dify_plugin.errors.tool import ToolProviderCredentialValidationError

        provider = GitDatasourceProvider()

        with pytest.raises(ToolProviderCredentialValidationError) as exc_info:
            provider._validate_credentials({"ssh_private_key": "not a valid key"})

        assert "PEM format" in str(exc_info.value)

    def test_truncated_key_rejected(self):
        """Truncated key (missing END marker) should be rejected."""
        from provider.git_datasource import GitDatasourceProvider
        from dify_plugin.errors.tool import ToolProviderCredentialValidationError

        provider = GitDatasourceProvider()
        
        truncated_key = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MaXV"""

        with pytest.raises(ToolProviderCredentialValidationError) as exc_info:
            provider._validate_credentials({"ssh_private_key": truncated_key})

        assert "truncated" in str(exc_info.value).lower()

    def test_public_key_rejected(self):
        """Public key (not private) should be rejected."""
        from provider.git_datasource import GitDatasourceProvider
        from dify_plugin.errors.tool import ToolProviderCredentialValidationError

        provider = GitDatasourceProvider()
        
        public_key = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA
-----END PUBLIC KEY-----"""

        with pytest.raises(ToolProviderCredentialValidationError) as exc_info:
            provider._validate_credentials({"ssh_private_key": public_key})

        assert "PEM format" in str(exc_info.value) or "PRIVATE KEY" in str(exc_info.value)


class TestBothCredentials:
    """Tests for providing both credentials."""

    def test_both_credentials_accepted(self):
        """Both access token and SSH key can be provided."""
        from provider.git_datasource import GitDatasourceProvider

        provider = GitDatasourceProvider()
        
        valid_key = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn
-----END RSA PRIVATE KEY-----"""
        
        # Should not raise - user might have both for different repos
        provider._validate_credentials({
            "access_token": "ghp_xxxxxxxxxxxx",
            "ssh_private_key": valid_key,
        })


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
