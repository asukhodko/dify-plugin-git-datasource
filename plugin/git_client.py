"""
Git Client - abstraction over Git operations.

Uses GitPython for MVP. Can be replaced with Dulwich for better portability.
"""

import hashlib
import logging
import os
import tempfile
from typing import Optional

from git import Repo, GitCommandError
from git.exc import InvalidGitRepositoryError

from utils.models import FileInfo, ChangeSet
from utils.url_utils import get_url_type, build_auth_url
from utils.filtering import filter_by_subdir, filter_by_extensions
from utils.masking import mask_url

logger = logging.getLogger(__name__)


class GitClientError(Exception):
    """Base exception for GitClient errors."""

    pass


class GitClient:
    """
    Git repository client.

    Handles clone, fetch, file listing, and change detection.
    """

    def __init__(
        self,
        repo_url: str,
        branch: str = "main",
        credentials: Optional[dict] = None,
        cache_dir: str = "/tmp/git_datasource_cache",
    ):
        """
        Initialize GitClient.

        Args:
            repo_url: Repository URL (HTTPS, SSH, or local path)
            branch: Branch name
            credentials: Dict with access_token, ssh_private_key, etc.
            cache_dir: Directory for caching cloned repositories
        """
        self.repo_url = repo_url
        self.branch = branch
        self.credentials = credentials or {}
        self.cache_dir = cache_dir
        self._repo: Optional[Repo] = None

        # Determine URL type
        self.url_type = get_url_type(repo_url)

        # Prepare cache path
        self._cache_path = self._get_cache_path()

    def _get_cache_path(self) -> str:
        """
        Get deterministic cache path for this repository.

        Returns:
            Path to cached repository directory
        """
        # Create hash from URL and branch for unique cache path
        key = f"{self.repo_url}:{self.branch}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]

        return os.path.join(self.cache_dir, key_hash)

    def _prepare_auth_url(self) -> str:
        """
        Prepare URL with embedded credentials for HTTPS auth.

        WARNING: The returned URL contains credentials and should NEVER be logged!

        Returns:
            URL with embedded token (for HTTPS) or original URL
        """
        if self.url_type != "https":
            return self.repo_url

        token = self.credentials.get("access_token")
        if not token:
            return self.repo_url

        return build_auth_url(self.repo_url, token)

    def _setup_ssh_environment(self) -> Optional[str]:
        """
        Set up SSH environment for authentication.

        Returns:
            Path to temporary key file (caller must clean up) or None
        """
        ssh_key = self.credentials.get("ssh_private_key")
        if not ssh_key:
            return None

        # Create temporary file for SSH key
        fd, key_path = tempfile.mkstemp(suffix=".key", prefix="git_")
        try:
            os.write(fd, ssh_key.encode())
            os.close(fd)
            os.chmod(key_path, 0o600)

            # Set GIT_SSH_COMMAND
            ssh_cmd = f"ssh -i {key_path} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
            os.environ["GIT_SSH_COMMAND"] = ssh_cmd

            return key_path
        except Exception:
            os.close(fd)
            os.unlink(key_path)
            raise

    def _cleanup_ssh_key(self, key_path: Optional[str]) -> None:
        """Clean up temporary SSH key file."""
        if key_path and os.path.exists(key_path):
            try:
                # Overwrite with zeros before deleting
                with open(key_path, "wb") as f:
                    f.write(b"\x00" * 1000)
                os.unlink(key_path)
            except Exception:
                pass

            # Restore environment
            os.environ.pop("GIT_SSH_COMMAND", None)

    def ensure_cloned(self) -> None:
        """
        Ensure repository is cloned locally.

        Clones if not exists, fetches if exists.
        """
        if os.path.exists(self._cache_path):
            self._fetch_repo()
        else:
            self._clone_repo()

    def _clone_repo(self) -> None:
        """Clone repository to cache."""
        logger.info(f"Cloning repository to {self._cache_path}")

        # Create cache directory
        os.makedirs(self.cache_dir, exist_ok=True)

        ssh_key_path = None
        try:
            # Set up SSH if needed
            if self.url_type == "ssh":
                ssh_key_path = self._setup_ssh_environment()

            # Prepare URL (with token for HTTPS)
            clone_url = self._prepare_auth_url()

            # Clone
            self._repo = Repo.clone_from(
                clone_url,
                self._cache_path,
                branch=self.branch,
            )

            logger.info("Repository cloned successfully")

        except GitCommandError as e:
            # Mask credentials in error
            error_msg = mask_url(str(e))
            raise GitClientError(f"Failed to clone repository: {error_msg}") from e
        finally:
            self._cleanup_ssh_key(ssh_key_path)

    def _fetch_repo(self) -> None:
        """Fetch updates for existing repository."""
        logger.info(f"Fetching updates for {mask_url(self.repo_url)}")

        ssh_key_path = None
        try:
            # Open existing repo
            self._repo = Repo(self._cache_path)

            # Set up SSH if needed
            if self.url_type == "ssh":
                ssh_key_path = self._setup_ssh_environment()

            # Update remote URL (in case token changed)
            if self.url_type == "https":
                fetch_url = self._prepare_auth_url()
                self._repo.remotes.origin.set_url(fetch_url)

            # Fetch
            self._repo.remotes.origin.fetch()

            logger.info("Repository fetched successfully")

        except (GitCommandError, InvalidGitRepositoryError) as e:
            error_msg = mask_url(str(e))
            raise GitClientError(f"Failed to fetch repository: {error_msg}") from e
        finally:
            self._cleanup_ssh_key(ssh_key_path)

    def test_connection(self) -> None:
        """
        Test connection to repository.

        Uses git ls-remote to verify access without cloning.
        """
        from git import cmd

        ssh_key_path = None
        try:
            if self.url_type == "ssh":
                ssh_key_path = self._setup_ssh_environment()

            test_url = self._prepare_auth_url()

            git = cmd.Git()
            git.ls_remote("--heads", test_url, self.branch)

        except GitCommandError as e:
            error_msg = mask_url(str(e))
            raise GitClientError(f"Connection test failed: {error_msg}") from e
        finally:
            self._cleanup_ssh_key(ssh_key_path)

    def get_head_sha(self) -> str:
        """
        Get SHA of HEAD for the configured branch.

        Returns:
            40-character SHA string
        """
        if not self._repo:
            self._repo = Repo(self._cache_path)

        # Get remote branch ref
        remote_ref = f"origin/{self.branch}"
        try:
            commit = self._repo.commit(remote_ref)
            return commit.hexsha
        except Exception:
            # Try local branch
            commit = self._repo.commit(self.branch)
            return commit.hexsha

    def is_sha_reachable(self, old_sha: str, new_sha: str) -> bool:
        """
        Check if old_sha is reachable from new_sha.

        Used to detect force pushes.

        Args:
            old_sha: Previous SHA
            new_sha: Current SHA

        Returns:
            True if old_sha is an ancestor of new_sha
        """
        if not self._repo:
            self._repo = Repo(self._cache_path)

        try:
            # Check if old_sha is ancestor of new_sha
            self._repo.git.merge_base("--is-ancestor", old_sha, new_sha)
            return True
        except GitCommandError:
            return False

    def get_commit_count(self, old_sha: str, new_sha: str) -> int:
        """
        Get number of commits between two SHAs.

        Args:
            old_sha: Start SHA
            new_sha: End SHA

        Returns:
            Number of commits
        """
        if not self._repo:
            self._repo = Repo(self._cache_path)

        try:
            commits = list(self._repo.iter_commits(f"{old_sha}..{new_sha}"))
            return len(commits)
        except Exception:
            return 0

    def list_all_files(
        self,
        subdir: str = "",
        extensions: Optional[list[str]] = None,
    ) -> list[FileInfo]:
        """
        List all files in repository.

        Args:
            subdir: Subdirectory filter
            extensions: Extension filter list

        Returns:
            List of FileInfo objects
        """
        if not self._repo:
            self._repo = Repo(self._cache_path)

        # Get tree at HEAD
        remote_ref = f"origin/{self.branch}"
        try:
            commit = self._repo.commit(remote_ref)
        except Exception:
            commit = self._repo.commit(self.branch)

        files = []

        def walk_tree(tree, path=""):
            for item in tree:
                full_path = f"{path}/{item.name}" if path else item.name

                if item.type == "tree":
                    # Directory - recurse
                    walk_tree(item, full_path)
                elif item.type == "blob":
                    # File
                    files.append(
                        FileInfo(
                            path=full_path,
                            name=item.name,
                            size=item.size,
                            type="file",
                        )
                    )

        walk_tree(commit.tree)

        # Apply filters
        paths = [f.path for f in files]

        if subdir:
            paths = filter_by_subdir(paths, subdir)

        if extensions:
            paths = filter_by_extensions(paths, extensions)

        # Filter files list
        path_set = set(paths)
        return [f for f in files if f.path in path_set]

    def get_file_info(self, file_path: str) -> Optional[FileInfo]:
        """
        Get info for a specific file.

        Args:
            file_path: Path to file

        Returns:
            FileInfo or None if not found
        """
        if not self._repo:
            self._repo = Repo(self._cache_path)

        remote_ref = f"origin/{self.branch}"
        try:
            commit = self._repo.commit(remote_ref)
        except Exception:
            commit = self._repo.commit(self.branch)

        try:
            blob = commit.tree / file_path
            return FileInfo(
                path=file_path,
                name=os.path.basename(file_path),
                size=blob.size,
                type="file",
            )
        except KeyError:
            return None

    def get_changed_files(
        self,
        old_sha: str,
        new_sha: str,
        subdir: str = "",
        extensions: Optional[list[str]] = None,
    ) -> ChangeSet:
        """
        Get files changed between two commits.

        Args:
            old_sha: Previous commit SHA
            new_sha: Current commit SHA
            subdir: Subdirectory filter
            extensions: Extension filter list

        Returns:
            ChangeSet with added, modified, deleted, renamed files
        """
        if not self._repo:
            self._repo = Repo(self._cache_path)

        old_commit = self._repo.commit(old_sha)
        new_commit = self._repo.commit(new_sha)

        diff = old_commit.diff(new_commit)

        added = []
        modified = []
        deleted = []
        renamed = []

        for d in diff:
            if d.new_file:
                added.append(d.b_path)
            elif d.deleted_file:
                deleted.append(d.a_path)
            elif d.renamed:
                renamed.append((d.a_path, d.b_path))
            else:
                modified.append(d.a_path or d.b_path)

        # Apply filters
        def filter_paths(paths: list[str]) -> list[str]:
            result = paths
            if subdir:
                result = filter_by_subdir(result, subdir)
            if extensions:
                result = filter_by_extensions(result, extensions)
            return result

        added = filter_paths(added)
        modified = filter_paths(modified)
        deleted = filter_paths(deleted)

        # Filter renamed - both old and new must match filters
        filtered_renamed = []
        for old_path, new_path in renamed:
            old_matches = (
                not subdir or old_path.startswith(subdir.strip("/") + "/")
            ) and (
                not extensions
                or any(old_path.lower().endswith(e.lower()) for e in extensions)
            )
            new_matches = (
                not subdir or new_path.startswith(subdir.strip("/") + "/")
            ) and (
                not extensions
                or any(new_path.lower().endswith(e.lower()) for e in extensions)
            )

            if old_matches or new_matches:
                filtered_renamed.append((old_path, new_path))

        return ChangeSet(
            added=added,
            modified=modified,
            deleted=deleted,
            renamed=filtered_renamed,
        )

    def read_file(self, file_path: str) -> bytes:
        """
        Read file content from repository.

        Args:
            file_path: Path to file

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not self._repo:
            self._repo = Repo(self._cache_path)

        remote_ref = f"origin/{self.branch}"
        try:
            commit = self._repo.commit(remote_ref)
        except Exception:
            commit = self._repo.commit(self.branch)

        try:
            blob = commit.tree / file_path
            return blob.data_stream.read()
        except KeyError:
            raise FileNotFoundError(f"File not found: {file_path}")
