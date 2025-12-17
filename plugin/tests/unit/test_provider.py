"""
Unit tests for GitDatasourceProvider.

Tests credential validation and connection testing.
"""

import pytest
from unittest.mock import patch, MagicMock

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


class TestCredentialValidation:
    """Tests for credential validation."""

    def test_missing_repo_url(self):
        """Should reject credentials without repo_url."""
        from provider.git_datasource import GitDatasourceProvider
        from dify_plugin.errors.tool import ToolProviderCredentialValidationError

        provider = GitDatasourceProvider()

        with pytest.raises(ToolProviderCredentialValidationError) as exc_info:
            provider._validate_credentials({})

        assert "Repository URL is required" in str(exc_info.value)

    def test_invalid_url_format(self):
        """Should reject invalid URL formats."""
        from provider.git_datasource import GitDatasourceProvider
        from dify_plugin.errors.tool import ToolProviderCredentialValidationError

        provider = GitDatasourceProvider()

        with pytest.raises(ToolProviderCredentialValidationError) as exc_info:
            provider._validate_credentials({"repo_url": "not-a-valid-url"})

        assert (
            "Invalid" in str(exc_info.value) or "format" in str(exc_info.value).lower()
        )

    def test_ssh_url_requires_key(self):
        """SSH URL should require SSH private key."""
        from provider.git_datasource import GitDatasourceProvider
        from dify_plugin.errors.tool import ToolProviderCredentialValidationError

        provider = GitDatasourceProvider()

        with pytest.raises(ToolProviderCredentialValidationError) as exc_info:
            provider._validate_credentials({"repo_url": "git@github.com:user/repo.git"})

        assert "SSH" in str(exc_info.value)

    def test_ssh_key_with_https_url(self):
        """SSH key with HTTPS URL should be rejected."""
        from provider.git_datasource import GitDatasourceProvider
        from dify_plugin.errors.tool import ToolProviderCredentialValidationError

        provider = GitDatasourceProvider()

        # Mock test_connection to avoid actual network call
        with patch.object(provider, "_test_connection"):
            with pytest.raises(ToolProviderCredentialValidationError) as exc_info:
                provider._validate_credentials(
                    {
                        "repo_url": "https://github.com/user/repo.git",
                        "ssh_private_key": "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
                    }
                )

        assert "SSH" in str(exc_info.value)

    def test_valid_https_credentials(self):
        """Valid HTTPS credentials should pass validation."""
        from provider.git_datasource import GitDatasourceProvider

        provider = GitDatasourceProvider()

        # Mock test_connection to avoid actual network call
        with patch.object(provider, "_test_connection") as mock_test:
            provider._validate_credentials(
                {
                    "repo_url": "https://github.com/user/repo.git",
                    "branch": "main",
                    "access_token": "test_token",
                }
            )

            mock_test.assert_called_once()

    def test_valid_local_credentials(self):
        """Valid local path credentials should pass validation."""
        from provider.git_datasource import GitDatasourceProvider

        provider = GitDatasourceProvider()

        # Mock test_connection to avoid actual filesystem access
        with patch.object(provider, "_test_connection") as mock_test:
            provider._validate_credentials(
                {"repo_url": "/home/user/repos/myrepo", "branch": "main"}
            )

            mock_test.assert_called_once()


class TestCredentialMaskingInErrors:
    """Tests for credential masking in error messages."""

    def test_token_masked_in_error(self):
        """Access token should be masked in error messages."""
        from provider.git_datasource import GitDatasourceProvider
        from dify_plugin.errors.tool import ToolProviderCredentialValidationError
        from git_client import GitClientError

        provider = GitDatasourceProvider()

        secret_token = "ghp_supersecrettoken123456789"

        # Mock test_connection to raise error containing token
        with patch.object(provider, "_test_connection") as mock_test:
            mock_test.side_effect = GitClientError(
                f"Connection failed with token {secret_token}"
            )

            with pytest.raises(ToolProviderCredentialValidationError) as exc_info:
                provider._validate_credentials(
                    {
                        "repo_url": "https://github.com/user/repo.git",
                        "access_token": secret_token,
                    }
                )

            # Token should not appear in error message
            assert secret_token not in str(exc_info.value)
            assert "***" in str(exc_info.value)


class TestConnectionTesting:
    """Tests for connection testing."""

    def test_connection_test_creates_client(self):
        """Connection test should create GitClient with correct params."""
        from provider.git_datasource import GitDatasourceProvider

        provider = GitDatasourceProvider()

        # Patch at the module where it's imported (inside the method)
        with patch("git_client.GitClient") as MockClient:
            mock_instance = MagicMock()
            MockClient.return_value = mock_instance

            credentials = {
                "repo_url": "https://github.com/user/repo.git",
                "branch": "develop",
                "access_token": "test_token",
            }

            provider._test_connection(credentials)

            # Verify GitClient was created with correct params
            MockClient.assert_called_once()
            call_kwargs = MockClient.call_args[1]
            assert call_kwargs["repo_url"] == "https://github.com/user/repo.git"
            assert call_kwargs["branch"] == "develop"
            assert "access_token" in call_kwargs["credentials"]

            # Verify test_connection was called
            mock_instance.test_connection.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
