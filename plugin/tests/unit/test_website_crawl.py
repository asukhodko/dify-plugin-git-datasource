"""
Unit tests for GitWebsiteCrawlDatasource.

Tests path normalization, config_hash, and source_url generation.
"""

import pytest


class TestPathNormalization:
    """Tests for _normalize_path method."""
    
    @pytest.fixture
    def datasource(self):
        """Create datasource instance for testing."""
        from datasources.git_website_crawl import GitWebsiteCrawlDatasource
        # Create instance without runtime (we only test static methods)
        ds = object.__new__(GitWebsiteCrawlDatasource)
        return ds
    
    def test_posix_conversion(self, datasource):
        """Test backslash to forward slash conversion."""
        assert datasource._normalize_path("src\\main\\app.py") == "src/main/app.py"
        assert datasource._normalize_path("docs\\readme.md") == "docs/readme.md"
    
    def test_dot_slash_removal(self, datasource):
        """Test ./ prefix removal."""
        assert datasource._normalize_path("./src/main.py") == "src/main.py"
        assert datasource._normalize_path("././test.py") == "test.py"
        assert datasource._normalize_path("./") == ""
    
    def test_leading_slash_removal(self, datasource):
        """Test leading / removal."""
        assert datasource._normalize_path("/src/main.py") == "src/main.py"
        assert datasource._normalize_path("///test.py") == "test.py"
    
    def test_path_traversal_rejection(self, datasource):
        """Test .. as path component is rejected."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            datasource._normalize_path("../secret.txt")
        
        with pytest.raises(ValueError, match="Path traversal detected"):
            datasource._normalize_path("src/../../../etc/passwd")
        
        with pytest.raises(ValueError, match="Path traversal detected"):
            datasource._normalize_path("docs/..") 
    
    def test_double_dots_in_filename_allowed(self, datasource):
        """Test .. in filenames (not path components) is allowed."""
        # These should NOT raise - ".." is part of filename, not a path component
        assert datasource._normalize_path("notes..md") == "notes..md"
        assert datasource._normalize_path("file..backup.txt") == "file..backup.txt"
        assert datasource._normalize_path("src/config..json") == "src/config..json"
        assert datasource._normalize_path("test...py") == "test...py"
    
    def test_combined_normalization(self, datasource):
        """Test combined normalization scenarios."""
        assert datasource._normalize_path(".\\src\\main.py") == "src/main.py"
        assert datasource._normalize_path("./docs/readme.md") == "docs/readme.md"
        assert datasource._normalize_path("/./test.py") == "test.py"


class TestConfigHash:
    """Tests for _get_config_hash method."""
    
    @pytest.fixture
    def datasource(self):
        """Create datasource instance for testing."""
        from datasources.git_website_crawl import GitWebsiteCrawlDatasource
        ds = object.__new__(GitWebsiteCrawlDatasource)
        return ds
    
    def test_deterministic_hash(self, datasource):
        """Test hash is deterministic for same input."""
        params = {
            "repo_url": "https://github.com/user/repo.git",
            "branch": "main",
            "subdir": "docs",
            "extensions": ".md,.txt",
        }
        hash1 = datasource._get_config_hash(params)
        hash2 = datasource._get_config_hash(params)
        assert hash1 == hash2
        assert len(hash1) == 16  # First 16 chars of SHA256
    
    def test_extensions_canonicalization_order(self, datasource):
        """Test extensions are sorted for consistent hash."""
        params1 = {"repo_url": "https://example.com", "extensions": ".md,.txt,.rst"}
        params2 = {"repo_url": "https://example.com", "extensions": ".txt,.rst,.md"}
        params3 = {"repo_url": "https://example.com", "extensions": ".rst,.md,.txt"}
        
        hash1 = datasource._get_config_hash(params1)
        hash2 = datasource._get_config_hash(params2)
        hash3 = datasource._get_config_hash(params3)
        
        assert hash1 == hash2 == hash3
    
    def test_extensions_canonicalization_case(self, datasource):
        """Test extensions are lowercased for consistent hash."""
        params1 = {"repo_url": "https://example.com", "extensions": ".MD,.TXT"}
        params2 = {"repo_url": "https://example.com", "extensions": ".md,.txt"}
        params3 = {"repo_url": "https://example.com", "extensions": ".Md,.TxT"}
        
        hash1 = datasource._get_config_hash(params1)
        hash2 = datasource._get_config_hash(params2)
        hash3 = datasource._get_config_hash(params3)
        
        assert hash1 == hash2 == hash3
    
    def test_extensions_canonicalization_whitespace(self, datasource):
        """Test extensions are trimmed for consistent hash."""
        params1 = {"repo_url": "https://example.com", "extensions": ".md, .txt"}
        params2 = {"repo_url": "https://example.com", "extensions": ".md,.txt"}
        params3 = {"repo_url": "https://example.com", "extensions": " .md , .txt "}
        
        hash1 = datasource._get_config_hash(params1)
        hash2 = datasource._get_config_hash(params2)
        hash3 = datasource._get_config_hash(params3)
        
        assert hash1 == hash2 == hash3
    
    def test_different_params_different_hash(self, datasource):
        """Test different params produce different hashes."""
        params1 = {"repo_url": "https://github.com/user/repo1.git"}
        params2 = {"repo_url": "https://github.com/user/repo2.git"}
        
        hash1 = datasource._get_config_hash(params1)
        hash2 = datasource._get_config_hash(params2)
        
        assert hash1 != hash2
    
    def test_default_values(self, datasource):
        """Test default values are handled correctly."""
        params1 = {"repo_url": "https://example.com"}
        params2 = {"repo_url": "https://example.com", "branch": None, "subdir": None}
        params3 = {"repo_url": "https://example.com", "branch": "main", "subdir": ""}
        
        hash1 = datasource._get_config_hash(params1)
        hash2 = datasource._get_config_hash(params2)
        hash3 = datasource._get_config_hash(params3)
        
        # All should produce same hash (defaults applied)
        assert hash1 == hash2 == hash3


class TestSourceUrl:
    """Tests for _make_source_url method."""
    
    @pytest.fixture
    def datasource(self):
        """Create datasource instance for testing."""
        from datasources.git_website_crawl import GitWebsiteCrawlDatasource
        ds = object.__new__(GitWebsiteCrawlDatasource)
        return ds
    
    def test_source_url_format(self, datasource):
        """Test source_url has correct format."""
        url = datasource._make_source_url("abc123def456", "src/main.py")
        assert url == "git:abc123def456:src/main.py"
    
    def test_source_url_normalizes_path(self, datasource):
        """Test source_url normalizes the path."""
        url = datasource._make_source_url("abc123", "./src\\main.py")
        assert url == "git:abc123:src/main.py"
    
    def test_source_url_rejects_traversal(self, datasource):
        """Test source_url rejects path traversal."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            datasource._make_source_url("abc123", "../secret.txt")


class TestBinaryDetection:
    """Tests for _is_binary_content method."""
    
    @pytest.fixture
    def datasource(self):
        """Create datasource instance for testing."""
        from datasources.git_website_crawl import GitWebsiteCrawlDatasource
        ds = object.__new__(GitWebsiteCrawlDatasource)
        return ds
    
    def test_text_content(self, datasource):
        """Test text content is not detected as binary."""
        assert not datasource._is_binary_content(b"Hello, world!")
        assert not datasource._is_binary_content(b"# Markdown\n\nSome text")
        assert not datasource._is_binary_content("Привет мир!".encode("utf-8"))
    
    def test_null_bytes_detected(self, datasource):
        """Test null bytes are detected as binary."""
        assert datasource._is_binary_content(b"Hello\x00World")
        assert datasource._is_binary_content(b"\x00\x01\x02\x03")
    
    def test_png_magic_bytes(self, datasource):
        """Test PNG magic bytes are detected."""
        png_header = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        assert datasource._is_binary_content(png_header)
    
    def test_jpeg_magic_bytes(self, datasource):
        """Test JPEG magic bytes are detected."""
        jpeg_header = b'\xff\xd8\xff\xe0' + b'\x00' * 100
        assert datasource._is_binary_content(jpeg_header)
    
    def test_pdf_magic_bytes(self, datasource):
        """Test PDF magic bytes are detected."""
        pdf_header = b'%PDF-1.4' + b'\x00' * 100
        assert datasource._is_binary_content(pdf_header)


class TestFileSkipping:
    """Tests for _should_skip_file method."""
    
    @pytest.fixture
    def datasource(self):
        """Create datasource instance for testing."""
        from datasources.git_website_crawl import GitWebsiteCrawlDatasource
        ds = object.__new__(GitWebsiteCrawlDatasource)
        return ds
    
    def test_git_directory_skipped(self, datasource):
        """Test .git directory is skipped."""
        skip, reason = datasource._should_skip_file(".git/config")
        assert skip
        assert reason == "git_directory"
        
        skip, reason = datasource._should_skip_file("src/.git/objects/abc")
        assert skip
        assert reason == "git_directory"
    
    def test_symlink_skipped(self, datasource):
        """Test symlinks are skipped."""
        skip, reason = datasource._should_skip_file("link.txt", is_symlink=True)
        assert skip
        assert reason == "symlink"
    
    def test_large_file_skipped(self, datasource):
        """Test large files are skipped."""
        skip, reason = datasource._should_skip_file("big.bin", size=10 * 1024 * 1024)
        assert skip
        assert reason == "too_large"
    
    def test_normal_file_not_skipped(self, datasource):
        """Test normal files are not skipped."""
        skip, reason = datasource._should_skip_file("src/main.py", size=1000)
        assert not skip
        assert reason is None


class TestStorageKeys:
    """Tests for storage key generation."""
    
    @pytest.fixture
    def datasource(self):
        """Create datasource instance for testing."""
        from datasources.git_website_crawl import GitWebsiteCrawlDatasource
        ds = object.__new__(GitWebsiteCrawlDatasource)
        return ds
    
    def test_sha_storage_key_format(self, datasource):
        """Test SHA storage key has correct format."""
        key = datasource._get_sha_storage_key("abc123def456")
        assert key == "git_sha:abc123def456"
    
    def test_failed_storage_key_format(self, datasource):
        """Test failed paths storage key has correct format."""
        key = datasource._get_failed_storage_key("abc123def456")
        assert key == "git_failed:abc123def456"
    
    def test_storage_keys_use_config_hash(self, datasource):
        """Test storage keys are based on config_hash."""
        params = {"repo_url": "https://example.com", "branch": "main"}
        config_hash = datasource._get_config_hash(params)
        
        sha_key = datasource._get_sha_storage_key(config_hash)
        failed_key = datasource._get_failed_storage_key(config_hash)
        
        assert config_hash in sha_key
        assert config_hash in failed_key


class TestExtensionsCanonicalization:
    """Tests for extensions canonicalization."""
    
    @pytest.fixture
    def datasource(self):
        """Create datasource instance for testing."""
        from datasources.git_website_crawl import GitWebsiteCrawlDatasource
        ds = object.__new__(GitWebsiteCrawlDatasource)
        return ds
    
    def test_empty_extensions(self, datasource):
        """Test empty extensions string."""
        assert datasource._canonicalize_extensions("") == ""
        assert datasource._canonicalize_extensions(None) == ""
    
    def test_single_extension(self, datasource):
        """Test single extension."""
        assert datasource._canonicalize_extensions(".md") == ".md"
        assert datasource._canonicalize_extensions(".MD") == ".md"
    
    def test_multiple_extensions_sorted(self, datasource):
        """Test multiple extensions are sorted."""
        result = datasource._canonicalize_extensions(".txt,.md,.rst")
        assert result == ".md,.rst,.txt"
    
    def test_whitespace_trimmed(self, datasource):
        """Test whitespace is trimmed."""
        result = datasource._canonicalize_extensions(" .md , .txt ")
        assert result == ".md,.txt"
    
    def test_empty_parts_ignored(self, datasource):
        """Test empty parts are ignored."""
        result = datasource._canonicalize_extensions(".md,,,.txt,")
        assert result == ".md,.txt"


class TestBatching:
    """Tests for batching behavior in _process_files_streaming."""
    
    @pytest.fixture
    def datasource(self):
        """Create datasource instance for testing."""
        from datasources.git_website_crawl import GitWebsiteCrawlDatasource
        ds = object.__new__(GitWebsiteCrawlDatasource)
        return ds
    
    @pytest.fixture
    def mock_client(self):
        """Create mock GitClient."""
        class MockGitClient:
            def __init__(self, files_content: dict[str, bytes]):
                self.files_content = files_content
            
            def read_file(self, path: str) -> bytes:
                if path not in self.files_content:
                    raise FileNotFoundError(path)
                return self.files_content[path]
        
        return MockGitClient
    
    def test_batch_size_respected(self, datasource, mock_client):
        """Test batches don't exceed BATCH_SIZE."""
        # Create 120 files (should produce 3 batches: 50, 50, 20)
        files = {f"file{i}.txt": f"content {i}".encode() for i in range(120)}
        client = mock_client(files)
        paths = list(files.keys())
        
        batches = list(datasource._process_files_streaming(
            client, paths, "abc123", "https://example.com", "main"
        ))
        
        # Should have 3 batches
        assert len(batches) == 3
        
        # First two batches should be BATCH_SIZE
        assert len(batches[0][0]) == 50
        assert len(batches[1][0]) == 50
        
        # Last batch should have remaining
        assert len(batches[2][0]) == 20
    
    def test_attempted_count_monotonic(self, datasource, mock_client):
        """Test attempted count increases monotonically."""
        files = {f"file{i}.txt": f"content {i}".encode() for i in range(75)}
        client = mock_client(files)
        paths = list(files.keys())
        
        batches = list(datasource._process_files_streaming(
            client, paths, "abc123", "https://example.com", "main"
        ))
        
        # Check attempted counts
        attempted_counts = [b[2] for b in batches]
        
        # Should be monotonically increasing
        for i in range(1, len(attempted_counts)):
            assert attempted_counts[i] > attempted_counts[i-1]
        
        # Final count should equal total paths
        assert attempted_counts[-1] == 75
    
    def test_failed_paths_collected(self, datasource, mock_client):
        """Test transient failures are collected in failed_paths."""
        class FailingClient:
            def __init__(self):
                self.call_count = 0
            
            def read_file(self, path: str) -> bytes:
                self.call_count += 1
                # Every 3rd file fails with IOError (transient)
                if self.call_count % 3 == 0:
                    raise IOError("Network error")
                return b"content"
        
        client = FailingClient()
        paths = [f"file{i}.txt" for i in range(9)]
        
        batches = list(datasource._process_files_streaming(
            client, paths, "abc123", "https://example.com", "main"
        ))
        
        # Collect all failed paths
        all_failed = []
        for batch, failed, _ in batches:
            all_failed.extend(failed)
        
        # Should have 3 failed (every 3rd)
        assert len(all_failed) == 3
    
    def test_permanent_skips_not_in_failed(self, datasource, mock_client):
        """Test permanent skips (binary, non-UTF-8) are NOT in failed_paths."""
        files = {
            "text.txt": b"normal text",
            "binary.bin": b'\x89PNG\r\n\x1a\n' + b'\x00' * 100,  # PNG
            "utf8.txt": b"more text",
        }
        client = mock_client(files)
        paths = list(files.keys())
        
        batches = list(datasource._process_files_streaming(
            client, paths, "abc123", "https://example.com", "main"
        ))
        
        # Collect all failed paths
        all_failed = []
        for batch, failed, _ in batches:
            all_failed.extend(failed)
        
        # Binary file should NOT be in failed (permanent skip)
        assert "binary.bin" not in all_failed
        assert len(all_failed) == 0


class TestEmptyResult:
    """Tests for empty result handling."""
    
    @pytest.fixture
    def datasource(self):
        """Create datasource instance for testing."""
        from datasources.git_website_crawl import GitWebsiteCrawlDatasource
        ds = object.__new__(GitWebsiteCrawlDatasource)
        return ds
    
    @pytest.fixture
    def mock_client(self):
        """Create mock GitClient."""
        class MockGitClient:
            def read_file(self, path: str) -> bytes:
                raise FileNotFoundError(path)
        
        return MockGitClient()
    
    def test_empty_paths_yields_empty_batch(self, datasource, mock_client):
        """Test empty paths list yields one empty batch."""
        paths = []
        
        batches = list(datasource._process_files_streaming(
            mock_client, paths, "abc123", "https://example.com", "main"
        ))
        
        # Should yield nothing for empty paths (handled in _get_website_crawl)
        assert len(batches) == 0
    
    def test_all_files_skipped_yields_batch(self, datasource):
        """Test when all files are skipped, still yields a batch."""
        class AllFailClient:
            def read_file(self, path: str) -> bytes:
                raise FileNotFoundError(path)
        
        client = AllFailClient()
        paths = ["missing1.txt", "missing2.txt"]
        
        batches = list(datasource._process_files_streaming(
            client, paths, "abc123", "https://example.com", "main"
        ))
        
        # Should yield one batch with empty content but attempted count
        assert len(batches) == 1
        batch, failed, attempted = batches[0]
        assert len(batch) == 0  # No successful files
        assert attempted == 2  # But we attempted 2
