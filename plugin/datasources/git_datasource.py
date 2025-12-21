"""
Git Datasource - main implementation of OnlineDriveDatasource.
"""

import os
from collections.abc import Generator

from dify_plugin.entities.datasource import (
    DatasourceMessage,
    OnlineDriveBrowseFilesRequest,
    OnlineDriveBrowseFilesResponse,
    OnlineDriveDownloadFileRequest,
    OnlineDriveFile,
    OnlineDriveFileBucket,
)
from dify_plugin.interfaces.datasource.online_drive import OnlineDriveDatasource


class GitDataSource(OnlineDriveDatasource):
    """
    Git Repository Data Source.

    Implements OnlineDriveDatasource interface for:
    - Browsing files/folders in repository
    - Downloading file content
    - Incremental sync via session.storage
    """

    def _get_storage_key(self) -> str:
        """
        Generate unique storage key for last_browsed_sha.

        Includes all config params to ensure different configs get fresh sync.
        """
        from utils.storage_utils import generate_storage_key

        repo_url = self.runtime.credentials.get("repo_url", "")
        branch = self.runtime.credentials.get("branch", "main")
        subdir = self.runtime.credentials.get("subdir", "")
        extensions = self.runtime.credentials.get("extensions", "")

        return generate_storage_key(repo_url, branch, subdir, extensions)

    def _get_last_browsed_sha(self) -> str | None:
        """Get last browsed SHA from storage."""
        storage_key = self._get_storage_key()
        if self.session.storage.exist(storage_key):
            return self.session.storage.get(storage_key).decode("utf-8")
        return None

    def _save_last_browsed_sha(self, sha: str) -> None:
        """Save last browsed SHA to storage."""
        storage_key = self._get_storage_key()
        self.session.storage.set(storage_key, sha.encode("utf-8"))

    def _browse_files(
        self, request: OnlineDriveBrowseFilesRequest
    ) -> OnlineDriveBrowseFilesResponse:
        """
        Get list of files for indexing.

        Logic:
        1. Get last_browsed_sha from storage
        2. Ensure local clone exists (clone/fetch)
        3. Determine sync type (full/incremental)
        4. Get file list
        5. Save new SHA (only if files returned)
        6. Return filtered list with pagination
        """
        from git_client import GitClient
        from utils.filtering import (
            parse_extensions,
        )

        # Get credentials
        repo_url = self.runtime.credentials.get("repo_url", "")
        branch = self.runtime.credentials.get("branch", "main")
        subdir = self.runtime.credentials.get("subdir", "")
        extensions_str = self.runtime.credentials.get("extensions", "")
        extensions = parse_extensions(extensions_str)

        # Request params
        max_keys = request.max_keys or 100

        # Initialize git client
        client = GitClient(
            repo_url=repo_url,
            branch=branch,
            credentials=dict(self.runtime.credentials),
            cache_dir="/tmp/git_datasource_cache",
        )

        # Ensure repo is cloned/fetched
        client.ensure_cloned()
        current_sha = client.get_head_sha()

        # Get last browsed SHA
        last_sha = self._get_last_browsed_sha()

        # Determine sync mode
        if self._should_full_sync(client, last_sha, current_sha):
            # Full sync - all files
            files = client.list_all_files(subdir, extensions)
        else:
            # Incremental sync - only changed files
            changeset = client.get_changed_files(
                last_sha, current_sha, subdir, extensions
            )
            # Return added + modified files (deleted are excluded automatically)
            files = []
            for path in changeset.added + changeset.modified:
                file_info = client.get_file_info(path)
                if file_info:
                    files.append(file_info)
            # Handle renames: new paths are in added, old paths excluded
            for old_path, new_path in changeset.renamed:
                file_info = client.get_file_info(new_path)
                if file_info:
                    files.append(file_info)

        # Convert to OnlineDriveFile format
        drive_files = []
        for f in files:
            drive_files.append(
                OnlineDriveFile(
                    id=f.path,  # Stable ID = file path
                    name=f.name,
                    size=f.size,
                    type=f.type,
                )
            )

        # Sort: folders first, then by name
        drive_files.sort(key=lambda x: (0 if x.type == "folder" else 1, x.name.lower()))

        # Pagination
        is_truncated = len(drive_files) > max_keys
        if is_truncated:
            drive_files = drive_files[:max_keys]

        # Save SHA only if we have files (prevent data loss)
        if drive_files:
            self._save_last_browsed_sha(current_sha)

        file_bucket = OnlineDriveFileBucket(
            bucket=None,
            files=drive_files,
            is_truncated=is_truncated,
            next_page_parameters=None,
        )

        return OnlineDriveBrowseFilesResponse(result=[file_bucket])

    def _should_full_sync(self, client, last_sha: str | None, current_sha: str) -> bool:
        """Determine if full sync is needed."""
        # No previous SHA - first sync
        if not last_sha:
            return True

        # Same SHA - no changes, but still show all files for browsing
        # (user may want to re-select files)
        if last_sha == current_sha:
            return True

        # Check if last SHA is reachable (force push detection)
        if not client.is_sha_reachable(last_sha, current_sha):
            return True

        # Check commit count threshold (fallback for large diffs)
        MAX_COMMITS_FOR_INCREMENTAL = 1000
        commit_count = client.get_commit_count(last_sha, current_sha)
        if commit_count > MAX_COMMITS_FOR_INCREMENTAL:
            return True

        return False

    def _download_file(
        self, request: OnlineDriveDownloadFileRequest
    ) -> Generator[DatasourceMessage, None, None]:
        """
        Download file content.
        """
        from git_client import GitClient
        from utils.mime_utils import get_mime_type

        repo_url = self.runtime.credentials.get("repo_url", "")
        branch = self.runtime.credentials.get("branch", "main")
        file_path = request.id

        client = GitClient(
            repo_url=repo_url,
            branch=branch,
            credentials=dict(self.runtime.credentials),
            cache_dir="/tmp/git_datasource_cache",
        )

        # Read file content
        content = client.read_file(file_path)

        # Determine MIME type
        mime_type = get_mime_type(file_path)

        yield self.create_blob_message(
            content,
            meta={
                "file_name": os.path.basename(file_path),
                "mime_type": mime_type,
            },
        )
