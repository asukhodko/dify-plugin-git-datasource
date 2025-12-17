"""
Integration tests for Git Datasource Plugin.

Tests the full flow: configure -> browse -> download.
Uses a real local git repository for testing.
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


class TestGitClientIntegration:
    """Integration tests using a real local git repository."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary git repository for testing."""
        from git import Repo

        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix="git_test_")

        # Initialize git repo
        repo = Repo.init(temp_dir)

        # Configure git user
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        # Create some files
        docs_dir = Path(temp_dir) / "docs"
        docs_dir.mkdir()

        (docs_dir / "readme.md").write_text("# Test Readme\n\nThis is a test file.")
        (docs_dir / "guide.txt").write_text("Test guide content")
        (Path(temp_dir) / "src" / "main.py").parent.mkdir(parents=True, exist_ok=True)
        (Path(temp_dir) / "src" / "main.py").write_text("print('hello')")

        # Commit
        repo.index.add(["docs/readme.md", "docs/guide.txt", "src/main.py"])
        repo.index.commit("Initial commit")

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def cache_dir(self):
        """Create a temporary cache directory."""
        temp_dir = tempfile.mkdtemp(prefix="git_cache_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_clone_and_list_files(self, temp_repo, cache_dir):
        """Test cloning a local repo and listing files."""
        from git_client import GitClient

        client = GitClient(
            repo_url=temp_repo,
            branch="master",  # git init creates 'master' by default
            cache_dir=cache_dir,
        )

        # Clone
        client.ensure_cloned()

        # List all files
        files = client.list_all_files()

        # Should have 3 files
        assert len(files) == 3

        # Check file paths
        paths = {f.path for f in files}
        assert "docs/readme.md" in paths
        assert "docs/guide.txt" in paths
        assert "src/main.py" in paths

    def test_filter_by_extension(self, temp_repo, cache_dir):
        """Test filtering files by extension."""
        from git_client import GitClient

        client = GitClient(repo_url=temp_repo, branch="master", cache_dir=cache_dir)

        client.ensure_cloned()

        # Filter by .md extension
        files = client.list_all_files(extensions=[".md"])

        assert len(files) == 1
        assert files[0].path == "docs/readme.md"

    def test_filter_by_subdir(self, temp_repo, cache_dir):
        """Test filtering files by subdirectory."""
        from git_client import GitClient

        client = GitClient(repo_url=temp_repo, branch="master", cache_dir=cache_dir)

        client.ensure_cloned()

        # Filter by docs/ subdirectory
        files = client.list_all_files(subdir="docs")

        assert len(files) == 2
        paths = {f.path for f in files}
        assert "docs/readme.md" in paths
        assert "docs/guide.txt" in paths

    def test_read_file_content(self, temp_repo, cache_dir):
        """Test reading file content."""
        from git_client import GitClient

        client = GitClient(repo_url=temp_repo, branch="master", cache_dir=cache_dir)

        client.ensure_cloned()

        # Read file
        content = client.read_file("docs/readme.md")

        assert b"# Test Readme" in content
        assert b"This is a test file" in content

    def test_file_not_found(self, temp_repo, cache_dir):
        """Test reading non-existent file."""
        from git_client import GitClient

        client = GitClient(repo_url=temp_repo, branch="master", cache_dir=cache_dir)

        client.ensure_cloned()

        # Try to read non-existent file
        with pytest.raises(FileNotFoundError):
            client.read_file("nonexistent.txt")

    def test_incremental_sync(self, temp_repo, cache_dir):
        """Test incremental sync after adding a file."""
        from git import Repo
        from git_client import GitClient

        client = GitClient(repo_url=temp_repo, branch="master", cache_dir=cache_dir)

        # Initial clone
        client.ensure_cloned()
        initial_sha = client.get_head_sha()

        # Add a new file to the source repo
        repo = Repo(temp_repo)
        new_file = Path(temp_repo) / "docs" / "new_file.md"
        new_file.write_text("# New File\n\nNew content")
        repo.index.add(["docs/new_file.md"])
        repo.index.commit("Add new file")

        # Fetch updates
        client.ensure_cloned()
        new_sha = client.get_head_sha()

        # SHAs should be different
        assert initial_sha != new_sha

        # Get changed files
        changeset = client.get_changed_files(initial_sha, new_sha)

        # Should have one added file
        assert "docs/new_file.md" in changeset.added
        assert len(changeset.modified) == 0
        assert len(changeset.deleted) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
