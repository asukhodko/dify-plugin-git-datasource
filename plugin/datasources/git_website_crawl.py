"""
Git Website Crawl Datasource - full implementation.

Implements WebsiteCrawlDatasource for automatic import of all repository files.
"""

import hashlib
import json
import logging
from collections.abc import Generator
from typing import Any

from dify_plugin.entities.datasource import (
    DatasourceMessage,
    WebSiteInfo,
    WebSiteInfoDetail,
)
from dify_plugin.interfaces.datasource.website import WebsiteCrawlDatasource

logger = logging.getLogger(__name__)


class GitWebsiteCrawlDatasource(WebsiteCrawlDatasource):
    """
    Git Repository Data Source using website_crawl interface.
    
    Features:
    - Automatic import of all text files from repository
    - Incremental sync (delta-model) - only changed files
    - Streaming batches to avoid timeouts
    - Failed paths retry on next sync
    """

    BATCH_SIZE = 50  # Files per batch
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_FAILED_PATHS = 10000  # Limit stored failed paths
    
    # Binary file detection
    BINARY_MAGIC_BYTES = [
        b'\x89PNG',      # PNG
        b'\xff\xd8\xff', # JPEG
        b'GIF8',         # GIF
        b'PK\x03\x04',   # ZIP/DOCX/XLSX
        b'%PDF',         # PDF
        b'\x7fELF',      # ELF binary
        b'MZ',           # Windows executable
    ]

    def _get_website_crawl(
        self, 
        datasource_parameters: dict[str, Any]
    ) -> Generator[DatasourceMessage, None, None]:
        """
        Main entry point for website crawl.
        
        Args:
            datasource_parameters: Contains repo_url, branch, subdir, extensions
            
        Yields:
            DatasourceMessage created via self.create_crawl_message(web_info)
        """
        import sys
        def debug(msg):
            print(f"[GIT_DEBUG] {msg}", file=sys.stderr, flush=True)
        
        from git_client import GitClient
        from utils.filtering import parse_extensions
        
        # Get parameters from datasource_parameters
        repo_url = datasource_parameters.get("repo_url", "")
        branch = datasource_parameters.get("branch", "main") or "main"
        subdir = datasource_parameters.get("subdir", "") or ""
        extensions_str = datasource_parameters.get("extensions", "") or ""
        extensions = parse_extensions(extensions_str) if extensions_str else None
        
        debug(f"Starting website crawl for {repo_url} @ {branch}")
        debug(f"Filters: subdir={subdir}, extensions={extensions}")
        logger.info(f"Starting website crawl for {repo_url} @ {branch}")
        logger.info(f"Filters: subdir={subdir}, extensions={extensions}")
        
        # Get credentials from runtime
        credentials = dict(self.runtime.credentials)
        
        # Generate config hash
        config_hash = self._get_config_hash(datasource_parameters)
        debug(f"Config hash: {config_hash}")
        logger.info(f"Config hash: {config_hash}")
        
        # Get last SHA and failed paths from storage BEFORE git operations
        debug("Getting last_sha from storage...")
        last_sha = self._get_last_sha(config_hash)
        debug(f"last_sha from storage: {last_sha}")
        failed_paths = self._get_failed_paths(config_hash)
        debug(f"failed_paths count: {len(failed_paths)}")
        
        if last_sha:
            logger.info(f"Last synced SHA: {last_sha[:8]}, failed_paths: {len(failed_paths)}")
        else:
            logger.info("First sync (no previous SHA)")
        
        # Initialize git client
        debug("Initializing GitClient...")
        logger.info("Initializing GitClient...")
        client = GitClient(
            repo_url=repo_url,
            branch=branch,
            credentials=credentials,
            cache_dir="/tmp/git_datasource_cache",
        )
        
        # Check if we can skip git fetch entirely (repo already cloned, no failed paths)
        # This optimization avoids network calls when we might not need them
        import os
        cache_exists = os.path.exists(client._cache_path)
        debug(f"Cache path: {client._cache_path}")
        debug(f"Cache exists: {cache_exists}, last_sha: {last_sha is not None}, failed_paths: {len(failed_paths)}")
        logger.info(f"Cache exists: {cache_exists}, last_sha: {last_sha is not None}, failed_paths: {len(failed_paths)}")
        
        if cache_exists and last_sha and not failed_paths:
            # Try to get current SHA without fetching first
            debug("Checking local HEAD SHA before fetch...")
            logger.info("Checking local HEAD SHA before fetch...")
            try:
                local_sha = client.get_head_sha()
                debug(f"Local HEAD SHA: {local_sha[:8]}")
                logger.info(f"Local HEAD SHA: {local_sha[:8]}")
                
                # If local SHA matches last synced SHA, we can skip entirely
                # (no local changes, no failed paths to retry)
                if local_sha == last_sha:
                    debug("No changes detected (local SHA matches last synced), returning empty result")
                    logger.info("No changes detected (local SHA matches last synced), returning empty result")
                    yield self.create_crawl_message(
                        WebSiteInfo(
                            web_info_list=[],
                            status="completed",
                            total=0,
                            completed=0,
                        )
                    )
                    return
            except Exception as e:
                debug(f"Could not get local SHA: {e}, will fetch")
                logger.warning(f"Could not get local SHA: {e}, will fetch")
        
        # Ensure repo is cloned/fetched
        debug("Calling ensure_cloned()...")
        logger.info("Calling ensure_cloned()...")
        client.ensure_cloned()
        debug("ensure_cloned() completed")
        logger.info("ensure_cloned() completed")
        
        debug("Getting HEAD SHA...")
        current_sha = client.get_head_sha()
        debug(f"Current HEAD SHA: {current_sha[:8]}")
        logger.info(f"Current HEAD SHA: {current_sha[:8]}")
        
        # Early return if no changes (same SHA) after fetch
        if last_sha and last_sha == current_sha and not failed_paths:
            debug("No changes detected (same SHA after fetch), returning empty result")
            logger.info("No changes detected (same SHA after fetch), returning empty result")
            debug("Creating empty crawl message...")
            msg = self.create_crawl_message(
                WebSiteInfo(
                    web_info_list=[],
                    status="completed",
                    total=0,
                    completed=0,
                )
            )
            debug("Yielding empty crawl message...")
            yield msg
            debug("Empty crawl message yielded, returning")
            return
        
        # Determine sync mode
        debug("Determining sync mode...")
        is_full_sync = self._should_full_sync(client, last_sha, current_sha)
        debug(f"Sync mode: {'full' if is_full_sync else 'incremental'}")
        
        # Get file paths
        if is_full_sync:
            debug("Getting file paths (full sync)...")
            logger.info("Performing full sync")
            paths = self._get_file_paths_full(client, subdir, extensions)
        else:
            debug("Getting file paths (incremental sync)...")
            logger.info("Performing incremental sync")
            paths = self._get_file_paths_incremental(
                client, last_sha, current_sha, subdir, extensions, failed_paths
            )
        
        total = len(paths)
        debug(f"Files to process: {total}")
        logger.info(f"Files to process: {total}")
        
        # Handle empty case
        if total == 0:
            debug("No files to process, creating empty message...")
            logger.info("No files to process, yielding completed message with empty list")
            msg = self.create_crawl_message(
                WebSiteInfo(
                    web_info_list=[],
                    status="completed",
                    total=0,
                    completed=0,
                )
            )
            debug("Yielding empty message...")
            yield msg
            debug("Saving SHA...")
            # Save SHA even for empty result
            self._save_sha(config_hash, current_sha)
            debug("Saving failed_paths...")
            self._save_failed_paths(config_hash, [])
            debug("Empty sync completed")
            logger.info("Empty sync completed, state saved")
            return
        
        # Stream batches
        completed = 0
        all_failed = []
        
        debug(f"Starting to process {total} files in batches...")
        for batch, batch_failed, batch_attempted in self._process_files_streaming(
            client, paths, config_hash, repo_url, branch
        ):
            completed += batch_attempted
            all_failed.extend(batch_failed)
            is_last = (completed >= total)
            
            debug(f"Batch ready: {len(batch)} files, completed={completed}/{total}, creating message...")
            logger.info(f"Yielding batch: {len(batch)} files, completed={completed}/{total}")
            
            msg = self.create_crawl_message(
                WebSiteInfo(
                    web_info_list=batch,
                    status="completed" if is_last else "processing",
                    total=total,
                    completed=completed,
                )
            )
            debug(f"Yielding batch message...")
            yield msg
            debug(f"Batch yielded successfully")
        
        # Save state after successful sync
        debug("All batches done, saving SHA...")
        self._save_sha(config_hash, current_sha)
        debug("Saving failed_paths...")
        self._save_failed_paths(config_hash, all_failed)
        debug(f"Sync completed. SHA: {current_sha[:8]}, failed: {len(all_failed)}")
        logger.info(f"Sync completed. SHA saved: {current_sha[:8]}, failed_paths: {len(all_failed)}")
    
    def _get_config_hash(self, params: dict[str, Any]) -> str:
        """
        Generate config_hash for storage and source_url.
        
        Hash = sha256(repo_url:branch:subdir:canonicalized_extensions)[:16]
        Extensions are canonicalized: sorted, lowercase, trimmed.
        """
        repo_url = params.get("repo_url", "")
        branch = params.get("branch", "main") or "main"
        subdir = params.get("subdir", "") or ""
        extensions_str = params.get("extensions", "") or ""
        
        # Canonicalize extensions: sorted, lowercase, trimmed
        canonicalized_extensions = self._canonicalize_extensions(extensions_str)
        
        # Create hash input
        hash_input = f"{repo_url}:{branch}:{subdir}:{canonicalized_extensions}"
        
        # Generate SHA256 hash, take first 16 chars
        return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:16]
    
    def _canonicalize_extensions(self, extensions_str: str | None) -> str:
        """
        Canonicalize extensions string for consistent hashing.
        
        - Split by comma
        - Lowercase each
        - Strip whitespace
        - Sort alphabetically
        - Join with comma
        """
        if not extensions_str:
            return ""
        
        extensions = [ext.lower().strip() for ext in extensions_str.split(",") if ext.strip()]
        return ",".join(sorted(extensions))
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path to POSIX format.
        
        - Convert backslashes to forward slashes
        - Remove leading ./
        - Remove leading /
        - Reject path traversal (.. as path component)
        
        Note: ".." in filenames like "notes..md" is OK.
        """
        # Convert to POSIX format
        path = path.replace("\\", "/")
        
        # Remove leading /
        path = path.lstrip("/")
        
        # Remove leading ./ (may appear after removing /)
        while path.startswith("./"):
            path = path[2:]
        
        # Reject path traversal (.. as path component)
        parts = path.split("/")
        if ".." in parts:
            raise ValueError(f"Path traversal detected: {path}")
        
        return path
    
    def _make_source_url(self, config_hash: str, path: str) -> str:
        """
        Create unique source_url.
        
        Format: git:{config_hash}:{normalized_path}
        """
        normalized = self._normalize_path(path)
        return f"git:{config_hash}:{normalized}"
    
    def _get_sha_storage_key(self, config_hash: str) -> str:
        """Get storage key for SHA tracking."""
        return f"git_sha:{config_hash}"
    
    def _get_failed_storage_key(self, config_hash: str) -> str:
        """Get storage key for failed paths tracking."""
        return f"git_failed:{config_hash}"
    
    def _get_last_sha(self, config_hash: str) -> str | None:
        """Get last synced SHA from storage."""
        key = self._get_sha_storage_key(config_hash)
        try:
            # Add timeout protection - storage calls can hang
            import threading
            result = [None]
            error = [None]
            
            def check_storage():
                try:
                    if self.session.storage.exist(key):
                        result[0] = self.session.storage.get(key).decode("utf-8")
                except Exception as e:
                    error[0] = e
            
            thread = threading.Thread(target=check_storage)
            thread.start()
            thread.join(timeout=10)  # 10 second timeout
            
            if thread.is_alive():
                import sys
                print(f"Storage check timed out for key {key}", file=sys.stderr, flush=True)
                logger.warning(f"Storage check timed out for key {key}")
                return None
            
            if error[0]:
                logger.warning(f"Storage error: {error[0]}")
                return None
                
            return result[0]
        except Exception as e:
            logger.warning(f"Failed to get last SHA from storage: {e}")
            return None
    
    def _save_sha(self, config_hash: str, sha: str) -> None:
        """Save SHA to storage."""
        import sys
        key = self._get_sha_storage_key(config_hash)
        print(f"[GIT_DEBUG] _save_sha: starting for key {key}", file=sys.stderr, flush=True)
        try:
            import threading
            error = [None]
            
            def save_storage():
                try:
                    self.session.storage.set(key, sha.encode("utf-8"))
                except Exception as e:
                    error[0] = e
            
            thread = threading.Thread(target=save_storage)
            thread.start()
            thread.join(timeout=10)  # 10 second timeout
            
            if thread.is_alive():
                print(f"[GIT_DEBUG] _save_sha: TIMEOUT for key {key}", file=sys.stderr, flush=True)
                logger.warning(f"Storage save timed out for key {key}")
            elif error[0]:
                print(f"[GIT_DEBUG] _save_sha: error {error[0]}", file=sys.stderr, flush=True)
                logger.warning(f"Storage save error: {error[0]}")
            else:
                print(f"[GIT_DEBUG] _save_sha: success", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[GIT_DEBUG] _save_sha: exception {e}", file=sys.stderr, flush=True)
            logger.warning(f"Failed to save SHA to storage: {e}")
    
    def _get_failed_paths(self, config_hash: str) -> list[str]:
        """Get failed paths from storage."""
        import sys
        key = self._get_failed_storage_key(config_hash)
        print(f"[GIT_DEBUG] _get_failed_paths: starting for key {key}", file=sys.stderr, flush=True)
        try:
            import threading
            result = [[]]
            error = [None]
            
            def check_storage():
                try:
                    if self.session.storage.exist(key):
                        data = self.session.storage.get(key).decode("utf-8")
                        result[0] = json.loads(data)
                except json.JSONDecodeError:
                    result[0] = []
                except Exception as e:
                    error[0] = e
            
            thread = threading.Thread(target=check_storage)
            thread.start()
            thread.join(timeout=10)  # 10 second timeout
            
            if thread.is_alive():
                print(f"[GIT_DEBUG] _get_failed_paths: TIMEOUT for key {key}", file=sys.stderr, flush=True)
                logger.warning(f"Storage check timed out for key {key}")
                return []
            
            if error[0]:
                print(f"[GIT_DEBUG] _get_failed_paths: error {error[0]}", file=sys.stderr, flush=True)
                logger.warning(f"Storage error: {error[0]}")
                return []
            
            print(f"[GIT_DEBUG] _get_failed_paths: success, count={len(result[0])}", file=sys.stderr, flush=True)
            return result[0]
        except Exception as e:
            print(f"[GIT_DEBUG] _get_failed_paths: exception {e}", file=sys.stderr, flush=True)
            logger.warning(f"Failed to get failed paths from storage: {e}")
            return []
    
    def _save_failed_paths(self, config_hash: str, paths: list[str]) -> None:
        """Save failed paths to storage (limited to MAX_FAILED_PATHS)."""
        import sys
        key = self._get_failed_storage_key(config_hash)
        print(f"[GIT_DEBUG] _save_failed_paths: starting for key {key}, count={len(paths)}", file=sys.stderr, flush=True)
        try:
            import threading
            error = [None]
            
            def save_storage():
                try:
                    # Limit size
                    limited_paths = paths[:self.MAX_FAILED_PATHS]
                    self.session.storage.set(key, json.dumps(limited_paths).encode("utf-8"))
                except Exception as e:
                    error[0] = e
            
            thread = threading.Thread(target=save_storage)
            thread.start()
            thread.join(timeout=10)  # 10 second timeout
            
            if thread.is_alive():
                print(f"[GIT_DEBUG] _save_failed_paths: TIMEOUT for key {key}", file=sys.stderr, flush=True)
                logger.warning(f"Storage save timed out for key {key}")
            elif error[0]:
                print(f"[GIT_DEBUG] _save_failed_paths: error {error[0]}", file=sys.stderr, flush=True)
                logger.warning(f"Storage save error: {error[0]}")
            else:
                print(f"[GIT_DEBUG] _save_failed_paths: success", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[GIT_DEBUG] _save_failed_paths: exception {e}", file=sys.stderr, flush=True)
            logger.warning(f"Failed to save failed paths to storage: {e}")
    
    def _is_binary_content(self, content: bytes) -> bool:
        """
        Check if content is binary.
        
        - Check for null bytes in first 8KB
        - Check magic bytes for known binary formats
        """
        # Check magic bytes
        for magic in self.BINARY_MAGIC_BYTES:
            if content.startswith(magic):
                return True
        
        # Check for null bytes in first 8KB
        sample = content[:8192]
        if b'\x00' in sample:
            return True
        
        return False
    
    def _should_skip_file(
        self, 
        path: str, 
        size: int | None = None,
        is_symlink: bool = False
    ) -> tuple[bool, str | None]:
        """
        Check if file should be skipped.
        
        Returns:
            (should_skip, reason) - reason is None if not skipped
        """
        # Skip .git directory
        normalized = path.replace("\\", "/")
        if normalized.startswith(".git/") or "/.git/" in normalized:
            return True, "git_directory"
        
        # Skip symlinks
        if is_symlink:
            return True, "symlink"
        
        # Skip large files
        if size is not None and size > self.MAX_FILE_SIZE:
            return True, "too_large"
        
        return False, None

    def _get_file_paths_full(
        self,
        client,  # GitClient
        subdir: str,
        extensions: list[str] | None,
    ) -> list[str]:
        """
        Get all file paths for full sync.
        
        Args:
            client: GitClient instance
            subdir: Subdirectory filter
            extensions: Extension filter list
            
        Returns:
            List of file paths
        """
        files = client.list_all_files(subdir, extensions)
        return [f.path for f in files]
    
    def _get_file_paths_incremental(
        self,
        client,  # GitClient
        last_sha: str,
        current_sha: str,
        subdir: str,
        extensions: list[str] | None,
        failed_paths: list[str],
    ) -> list[str]:
        """
        Get changed file paths for incremental sync.
        
        Args:
            client: GitClient instance
            last_sha: Previous sync SHA
            current_sha: Current HEAD SHA
            subdir: Subdirectory filter
            extensions: Extension filter list
            failed_paths: Previously failed paths to retry
            
        Returns:
            List of file paths (added + modified + renamed new paths + failed)
        """
        changeset = client.get_changed_files(last_sha, current_sha, subdir, extensions)
        
        # Collect paths: added + modified + new paths from renames
        paths = set(changeset.added + changeset.modified)
        for old_path, new_path in changeset.renamed:
            paths.add(new_path)
        
        # Add failed paths for retry (filter by subdir/extensions)
        for path in failed_paths:
            # Check if path still matches filters
            if subdir and not path.startswith(subdir.strip("/") + "/"):
                continue
            if extensions and not any(path.lower().endswith(e.lower()) for e in extensions):
                continue
            paths.add(path)
        
        return list(paths)
    
    def _should_full_sync(
        self,
        client,  # GitClient
        last_sha: str | None,
        current_sha: str,
    ) -> bool:
        """
        Determine if full sync is needed.
        
        Returns True if:
        - No previous SHA (first sync)
        - Previous SHA not reachable (force push)
        - Too many commits between SHAs
        """
        MAX_COMMITS_FOR_INCREMENTAL = 1000
        
        # No previous SHA - first sync
        if not last_sha:
            return True
        
        # Check if last SHA is reachable (force push detection)
        if not client.is_sha_reachable(last_sha, current_sha):
            logger.info(f"Force push detected: {last_sha[:8]} not reachable from {current_sha[:8]}")
            return True
        
        # Check commit count threshold
        commit_count = client.get_commit_count(last_sha, current_sha)
        if commit_count > MAX_COMMITS_FOR_INCREMENTAL:
            logger.info(f"Too many commits ({commit_count}), doing full sync")
            return True
        
        return False

    def _read_file_content(
        self,
        client,  # GitClient
        path: str,
    ) -> tuple[str | None, str | None, bool]:
        """
        Read file content and decode as UTF-8.
        
        Args:
            client: GitClient instance
            path: File path
            
        Returns:
            (content, error_reason, is_transient)
            - content: UTF-8 string or None if failed
            - error_reason: Error description or None if success
            - is_transient: True if error is transient (should retry)
        """
        try:
            raw_content = client.read_file(path)
            
            # Check if binary
            if self._is_binary_content(raw_content):
                logger.debug(f"Skipping binary file: {path}")
                return None, "binary", False  # permanent skip
            
            # Decode UTF-8
            try:
                content = raw_content.decode("utf-8")
                return content, None, False
            except UnicodeDecodeError:
                logger.warning(f"Skipping non-UTF-8 file: {path}")
                return None, "non_utf8", False  # permanent skip
                
        except FileNotFoundError:
            logger.warning(f"File not found: {path}")
            return None, "not_found", False  # permanent skip (file deleted)
            
        except IOError as e:
            logger.warning(f"Failed to read file {path}: {e}")
            return None, str(e), True  # transient error
            
        except Exception as e:
            logger.warning(f"Unexpected error reading {path}: {e}")
            return None, str(e), True  # treat as transient
    
    def _process_files_streaming(
        self,
        client,  # GitClient
        paths: list[str],
        config_hash: str,
        repo_url: str,
        branch: str,
    ) -> Generator[tuple[list[WebSiteInfoDetail], list[str], int], None, None]:
        """
        Process files and yield batches.
        
        Args:
            client: GitClient instance
            paths: List of file paths to process
            config_hash: Config hash for source_url
            repo_url: Repository URL for description
            branch: Branch name for description
            
        Yields:
            (batch_of_details, failed_paths_in_batch, attempted_count)
        """
        batch = []
        batch_failed = []
        attempted = 0
        
        for path in paths:
            attempted += 1
            
            # Check if should skip (size, symlink, .git)
            # Note: We don't have size/symlink info here, so we check after reading
            # The _should_skip_file is mainly for pre-filtering if we have metadata
            
            # Normalize path
            try:
                normalized_path = self._normalize_path(path)
            except ValueError as e:
                logger.warning(f"Skipping invalid path {path}: {e}")
                continue  # permanent skip, don't add to failed
            
            # Read content
            content, error, is_transient = self._read_file_content(client, path)
            
            if content is None:
                if is_transient:
                    batch_failed.append(path)
                # permanent skips are not added to failed_paths
                continue
            
            # Check file size after reading
            if len(content.encode("utf-8")) > self.MAX_FILE_SIZE:
                logger.warning(f"Skipping large file: {path} ({len(content)} chars)")
                continue  # permanent skip
            
            # Create WebSiteInfoDetail
            detail = WebSiteInfoDetail(
                title=normalized_path,
                content=content,
                source_url=self._make_source_url(config_hash, normalized_path),
                description=f"Git: {repo_url} @ {branch}",
            )
            batch.append(detail)
            
            # Yield batch if full
            if len(batch) >= self.BATCH_SIZE:
                yield batch, batch_failed, attempted
                batch = []
                batch_failed = []
        
        # Yield remaining
        if batch or batch_failed or attempted > 0:
            yield batch, batch_failed, attempted
