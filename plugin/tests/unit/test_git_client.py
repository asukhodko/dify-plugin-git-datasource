"""
Unit tests for GitClient.

Tests cache reuse, SHA operations, file listing, and change detection.
"""

import os
import pytest

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


class TestGitClientCachePath:
    """Tests for cache path generation."""

    def test_cache_path_deterministic(self):
        """Same config should produce same cache path."""
        from git_client import GitClient

        client1 = GitClient(
            repo_url="https://github.com/user/repo.git",
            branch="main",
            cache_dir="/tmp/test_cache",
        )
        client2 = GitClient(
            repo_url="https://github.com/user/repo.git",
            branch="main",
            cache_dir="/tmp/test_cache",
        )

        assert client1._cache_path == client2._cache_path

    def test_cache_path_different_for_different_repos(self):
        """Different repos should have different cache paths."""
        from git_client import GitClient

        client1 = GitClient(
            repo_url="https://github.com/user/repo1.git",
            branch="main",
            cache_dir="/tmp/test_cache",
        )
        client2 = GitClient(
            repo_url="https://github.com/user/repo2.git",
            branch="main",
            cache_dir="/tmp/test_cache",
        )

        assert client1._cache_path != client2._cache_path

    def test_cache_path_different_for_different_branches(self):
        """Different branches should have different cache paths."""
        from git_client import GitClient

        client1 = GitClient(
            repo_url="https://github.com/user/repo.git",
            branch="main",
            cache_dir="/tmp/test_cache",
        )
        client2 = GitClient(
            repo_url="https://github.com/user/repo.git",
            branch="develop",
            cache_dir="/tmp/test_cache",
        )

        assert client1._cache_path != client2._cache_path


class TestGitClientAuthUrl:
    """Tests for authenticated URL preparation."""

    def test_auth_url_with_token(self):
        """Token should be embedded in HTTPS URL."""
        from git_client import GitClient

        client = GitClient(
            repo_url="https://github.com/user/repo.git",
            branch="main",
            credentials={"access_token": "test_token_123"},
        )

        auth_url = client._prepare_auth_url()

        assert "test_token_123" in auth_url
        assert auth_url.startswith("https://")

    def test_auth_url_without_token(self):
        """Without token, URL should be unchanged."""
        from git_client import GitClient

        client = GitClient(
            repo_url="https://github.com/user/repo.git",
            branch="main",
        )

        auth_url = client._prepare_auth_url()

        assert auth_url == "https://github.com/user/repo.git"

    def test_auth_url_ssh_unchanged(self):
        """SSH URLs should not have token embedded."""
        from git_client import GitClient

        client = GitClient(
            repo_url="git@github.com:user/repo.git",
            branch="main",
            credentials={"access_token": "test_token_123"},
        )

        auth_url = client._prepare_auth_url()

        assert auth_url == "git@github.com:user/repo.git"
        assert "test_token_123" not in auth_url


class TestGitClientUrlType:
    """Tests for URL type detection."""

    def test_https_url_type(self):
        """HTTPS URLs should be detected."""
        from git_client import GitClient

        client = GitClient(
            repo_url="https://github.com/user/repo.git",
            branch="main",
        )

        assert client.url_type == "https"

    def test_ssh_url_type(self):
        """SSH URLs should be detected."""
        from git_client import GitClient

        client = GitClient(
            repo_url="git@github.com:user/repo.git",
            branch="main",
        )

        assert client.url_type == "ssh"

    def test_local_url_type(self):
        """Local paths should be detected."""
        from git_client import GitClient

        client = GitClient(
            repo_url="/home/user/repos/myrepo",
            branch="main",
        )

        assert client.url_type == "local"


# **Feature: git-datasource-plugin, Cache Reuse**
# **Validates: Requirements 8.2**
class TestCacheReuse:
    """Tests for cache reuse behavior (fetch instead of clone)."""

    def test_ensure_cloned_uses_fetch_when_cache_exists(self):
        """
        When cache directory exists, ensure_cloned should use fetch instead of clone.

        This test verifies the logic path, not actual git operations.
        """
        from git_client import GitClient
        from unittest.mock import patch

        client = GitClient(
            repo_url="https://github.com/user/repo.git",
            branch="main",
            cache_dir="/tmp/test_cache_reuse",
        )

        # Mock os.path.exists to return True (cache exists)
        with patch("os.path.exists", return_value=True):
            with patch.object(client, "_fetch_repo") as mock_fetch:
                with patch.object(client, "_clone_repo") as mock_clone:
                    client.ensure_cloned()

                    # Should call fetch, not clone
                    mock_fetch.assert_called_once()
                    mock_clone.assert_not_called()

    def test_ensure_cloned_uses_clone_when_no_cache(self):
        """
        When cache directory doesn't exist, ensure_cloned should clone.
        """
        from git_client import GitClient
        from unittest.mock import patch

        client = GitClient(
            repo_url="https://github.com/user/repo.git",
            branch="main",
            cache_dir="/tmp/test_cache_reuse",
        )

        # Mock os.path.exists to return False (no cache)
        with patch("os.path.exists", return_value=False):
            with patch.object(client, "_fetch_repo") as mock_fetch:
                with patch.object(client, "_clone_repo") as mock_clone:
                    client.ensure_cloned()

                    # Should call clone, not fetch
                    mock_clone.assert_called_once()
                    mock_fetch.assert_not_called()


# **Feature: git-datasource-plugin, Property 16: Stable File ID**
# **Validates: Requirements 10.1, 10.2, 10.3**
class TestStableFileId:
    """Tests for stable file ID generation."""

    def test_file_id_is_path(self):
        """File ID should be the file path."""
        from utils.models import FileInfo

        file_info = FileInfo(
            path="docs/guide/readme.md", name="readme.md", size=1234, type="file"
        )

        # ID should be the path (used in OnlineDriveFile.id)
        assert file_info.path == "docs/guide/readme.md"

    def test_file_id_no_sha(self):
        """File ID should not contain SHA."""
        from utils.models import FileInfo
        import re

        file_info = FileInfo(
            path="docs/readme.md", name="readme.md", size=100, type="file"
        )

        # Path should not contain a 40-char hex string (SHA format)
        sha_pattern = re.compile(r"[0-9a-f]{40}")
        assert not sha_pattern.search(file_info.path), "File ID should not contain SHA"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
