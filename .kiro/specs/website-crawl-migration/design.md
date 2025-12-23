# Design Document: Website Crawl Migration

## Overview

Миграция Git Datasource плагина с `OnlineDriveDatasource` на `WebsiteCrawlDatasource` для автоматической загрузки всех файлов репозитория без ручного выбора.

Ключевые изменения:
- Новый класс `GitWebsiteCrawlDatasource` вместо `GitDataSource`
- Метод `_get_website_crawl` вместо `_browse_files`/`_download_file`
- Streaming батчинг результатов через generator
- Delta-модель синхронизации (только изменённые файлы)

## Design Decisions

### DD1: Dify Sync Semantics

**Assumption:** website_crawl ingest обновляет/создаёт документы по `source_url` и не удаляет отсутствующие (upsert-only).

**Validation step:** Интеграционный тест в Dify 1.11.1:
1. Full sync → все файлы
2. Delta sync (1 изменённый файл) → проверить, что остальные документы не стали orphaned

**Fallback:** Если Dify делает snapshot-diff, нужно будет переключиться на snapshot-модель.

### DD2: Delta-Model Limitations

В delta-режиме плагин может:
- **Добавить** — вернуть новый файл
- **Обновить** — вернуть файл с тем же `source_url`, но новым `content`
- **Переименование** — это add нового пути; старый путь останется как "лишний" документ

**Ограничение:** Удаление файла из Git не приводит к удалению документа в Dify (без snapshot выдачи Dify не узнает об удалении).

### DD3: source_url Uniqueness

Для защиты от коллизий при подключении нескольких репозиториев:
- `title`: относительный путь файла (для UI)
- `source_url`: `git:{config_hash}:{path}` — уникальный идентификатор
- `config_hash` = `sha256(repo_url:branch:subdir:canonicalized_extensions)[:16]`
- Extensions канонизируются: sorted, lowercase, trimmed, joined with `,`

### DD4: SHA Update Policy

**last_sha сохраняем только если:**
1. Crawl завершился успешно (нет фатальных ошибок)
2. Все файлы из changeset были обработаны (или явно пропущены по фильтрам)

**При ошибках чтения файлов:**
- Сохраняем список `failed_paths` в storage
- На следующем sync пытаемся переимпортировать failed_paths даже если они не changed

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Dify Platform                         │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │ Knowledge Base  │◄───│ Plugin Daemon   │                 │
│  │   (Documents)   │    │                 │                 │
│  └─────────────────┘    └────────┬────────┘                 │
└──────────────────────────────────┼──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │   Git Datasource Plugin     │
                    │                             │
                    │  ┌───────────────────────┐  │
                    │  │ GitDatasourceProvider │  │
                    │  │ _validate_credentials │  │
                    │  └───────────┬───────────┘  │
                    │              │              │
                    │  ┌───────────▼───────────┐  │
                    │  │ GitWebsiteCrawlDS     │  │
                    │  │ _get_website_crawl()  │  │
                    │  └───────────┬───────────┘  │
                    │              │              │
                    │  ┌───────────▼───────────┐  │
                    │  │     GitClient         │  │
                    │  │ (clone/fetch/read)    │  │
                    │  └───────────┬───────────┘  │
                    │              │              │
                    │  ┌───────────▼───────────┐  │
                    │  │   session.storage     │  │
                    │  │ (SHA + failed_paths)  │  │
                    │  └───────────────────────┘  │
                    └─────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │      Git Repository         │
                    │  (HTTPS/SSH/Local)          │
                    └─────────────────────────────┘
```

## Components and Interfaces

### 1. GitDatasourceProvider (существующий, минимальные изменения)

```python
class GitDatasourceProvider(DatasourceProvider):
    """
    Provider для валидации credentials.
    
    Credentials (секреты, хранятся зашифрованно):
    - access_token: для HTTPS
    - ssh_private_key: для SSH
    
    Datasource parameters (не секреты):
    - repo_url, branch, subdir, extensions
    """
    
    def _validate_credentials(self, credentials: Mapping[str, Any]):
        """
        Валидация при настройке источника:
        1. Проверка формата URL
        2. Проверка соответствия: SSH URL ↔ есть ключ / HTTPS ↔ есть токен
        3. Тест-подключение (ls-remote)
        4. Маскирование секретов в ошибках
        """
        pass
```

### 2. GitWebsiteCrawlDatasource (новый класс)

```python
from dify_plugin.interfaces.datasource.website_crawl import WebsiteCrawlDatasource
from dify_plugin.entities.datasource import (
    WebSiteInfo,
    WebSiteInfoDetail,
    DatasourceMessage,
)

class GitWebsiteCrawlDatasource(WebsiteCrawlDatasource):
    """Git Repository Data Source using website_crawl interface."""
    
    BATCH_SIZE = 50  # Files per batch
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
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
            
        Note:
            Credentials (access_token, ssh_private_key) are accessed via
            self.runtime.credentials, NOT datasource_parameters.
        """
        pass
    
    def _get_storage_key(self, params: dict) -> str:
        """
        Generate config_hash for storage and source_url.
        
        Hash = sha256(repo_url:branch:subdir:canonicalized_extensions)[:16]
        Extensions are canonicalized: sorted, lowercase, trimmed.
        """
        pass
    
    def _get_file_paths(
        self, 
        client: GitClient, 
        last_sha: str | None,
        current_sha: str,
        failed_paths: list[str]
    ) -> tuple[list[str], int]:
        """
        Get list of file paths to process (cheap operation).
        
        Returns:
            (paths_to_process, total_count)
        """
        pass
    
    def _process_files_streaming(
        self,
        client: GitClient,
        paths: list[str],
        storage_key: str
    ) -> Generator[tuple[list[WebSiteInfoDetail], list[str]], None, None]:
        """
        Process files and yield batches.
        
        Yields:
            (batch_of_details, failed_paths_in_batch)
        """
        pass
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path to POSIX format.
        - Always use /
        - Remove ./
        - Reject path traversal (.. as path component, NOT in filenames)
        """
        pass
    
    def _make_source_url(self, config_hash: str, path: str) -> str:
        """Create unique source_url: git:{config_hash}:{path}"""
        pass
```

### 3. GitClient (существующий, без изменений)

Переиспользуется полностью:
- `ensure_cloned()` - clone/fetch
- `get_head_sha()` - текущий SHA
- `list_all_files()` - все файлы (возвращает пути/размеры)
- `get_changed_files()` - изменённые файлы (возвращает пути)
- `read_file()` - чтение содержимого
- `is_sha_reachable()` - проверка force push

### 4. Provider YAML (изменения)

```yaml
# provider/git_datasource.yaml
identity:
  author: dify-community
  name: git_datasource
  label:
    en_US: Git Repository
  icon: icon.svg

provider_type: website_crawl  # CHANGED from online_drive

credentials_schema:
  # Credentials for authentication (stored encrypted)
  - name: access_token
    type: secret-input
    required: false
    label:
      en_US: Access Token
      
  - name: ssh_private_key
    type: secret-input
    required: false
    label:
      en_US: SSH Private Key (PEM format)

datasources:
  - datasources/git_datasource.yaml

extra:
  python:
    source: provider/git_datasource.py
```

### 5. Datasource YAML (изменения)

```yaml
# datasources/git_datasource.yaml
identity:
  name: git_datasource
  author: dify-community
  label:
    en_US: Git Repository

description:
  en_US: Import all files from Git repository automatically

# Parameters for each sync (not credentials)
parameters:
  - name: repo_url
    type: text-input
    required: true
    label:
      en_US: Repository URL
      
  - name: branch
    type: text-input
    required: false
    default: main
    label:
      en_US: Branch
      
  - name: subdir
    type: text-input
    required: false
    label:
      en_US: Subdirectory
      
  - name: extensions
    type: text-input
    required: false
    label:
      en_US: File Extensions

# Output schema for website_crawl
output_schema:
  type: object
  properties:
    title:
      type: string
      description: File path (relative)
    content:
      type: string
      description: File content (UTF-8)
    description:
      type: string
      description: Repository metadata
    source_url:
      type: string
      description: Unique identifier (git:key:path)

extra:
  python:
    source: datasources/git_datasource.py
```

## Data Models

### WebSiteInfo (SDK)

```python
class WebSiteInfo:
    web_info_list: list[WebSiteInfoDetail]  # Files in this batch
    status: str  # "processing" | "completed"
    total: int   # Total files (known upfront)
    completed: int  # Files processed so far
```

### WebSiteInfoDetail (SDK)

```python
class WebSiteInfoDetail:
    title: str       # Relative file path (e.g., "src/main.py")
    content: str     # File content (UTF-8 text)
    source_url: str  # Unique ID: "git:{storage_key}:{path}"
    description: str # "Git: {repo_url} @ {branch}"
```

### Storage Keys

```
# config_hash calculation
config_hash = sha256(f"{repo_url}:{branch}:{subdir}:{canonicalized_extensions}")[:16]
# where canonicalized_extensions = ",".join(sorted([ext.lower().strip() for ext in extensions]))

# SHA tracking
git_sha:{config_hash}

# Failed paths tracking (transient errors only)
git_failed:{config_hash}
```

## Sync Flow

### Streaming Architecture

```python
def _get_website_crawl(self, params):
    # 1. Get file paths (cheap, gives us total)
    paths, total = self._get_file_paths(client, last_sha, current_sha, failed_paths)
    
    # 2. Handle empty case
    if total == 0:
        yield self.create_crawl_message(WebSiteInfo(
            web_info_list=[],
            status="completed",
            total=0,
            completed=0
        ))
        return
    
    # 3. Stream batches
    completed = 0
    all_failed = []
    
    for batch, batch_failed in self._process_files_streaming(client, paths, config_hash):
        completed += len(batch) + len(batch_failed)  # count attempted, not successful
        all_failed.extend(batch_failed)
        is_last = (completed >= total)
        
        yield self.create_crawl_message(WebSiteInfo(
            web_info_list=batch,
            status="completed" if is_last else "processing",
            total=total,
            completed=completed
        ))
    
    # 4. Update storage (only on success)
    self._save_sha(storage_key, current_sha)
    self._save_failed_paths(storage_key, all_failed)
```

### First Sync (no stored SHA)

```
1. Clone repository
2. Get current HEAD SHA
3. Get all file paths (filtered) → know total upfront
4. For each path (streaming):
   - Check size < MAX_FILE_SIZE
   - Check not symlink
   - Normalize path (POSIX, no ..)
   - Read content (UTF-8, skip on error)
   - Create WebSiteInfoDetail
5. Yield batches (50 files each) with status="processing"
6. Yield final batch with status="completed"
7. Store current SHA and failed_paths
```

### Incremental Sync (stored SHA exists)

```
1. Fetch repository
2. Get current HEAD SHA
3. Load stored SHA and failed_paths
4. Check if stored SHA is reachable
   - If not reachable (force push): do full sync
5. Get changed files since stored SHA
6. Add failed_paths to list (retry)
7. For each path (streaming):
   - Read content
   - Create WebSiteInfoDetail
8. Yield batches with status="processing"
9. Yield final batch with status="completed"
10. Store current SHA and new failed_paths
```

## Path Normalization

All paths are normalized to ensure stability:

```python
def _normalize_path(self, path: str) -> str:
    # Convert to POSIX format
    path = path.replace("\\", "/")
    
    # Remove leading ./
    while path.startswith("./"):
        path = path[2:]
    
    # Reject path traversal (.. as path component)
    # Note: ".." in filenames like "notes..md" is OK
    parts = path.split("/")
    if ".." in parts:
        raise ValueError(f"Path traversal detected: {path}")
    
    # Remove leading /
    path = path.lstrip("/")
    
    return path
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do.*

### Property 1: WebSiteInfoDetail Structure Completeness

*For any* text file in the repository, the generated WebSiteInfoDetail SHALL contain:
- title equal to the normalized relative file path
- content equal to the file's UTF-8 text content
- source_url in format `git:{storage_key}:{normalized_path}`
- description containing repository URL and branch

**Validates: Requirements 2.4, 2.8, 6.2**

### Property 2: Batching and Status Correctness

*For any* collection of N files where N > 0:
- Files SHALL be grouped into batches of at most BATCH_SIZE
- All batches except the last SHALL have status="processing"
- The last batch SHALL have status="completed"
- The sum of files across all batches SHALL equal N
- The `completed` field SHALL monotonically increase across batches (counts attempted paths, not successful)
- The `total` field SHALL be known upfront and constant across batches

**Validates: Requirements 2.5, 2.6, 2.7, 6.3, 6.4, 6.5, 6.6**

### Property 3: Empty Result Handling

*For any* sync where no files match filters:
- Plugin SHALL yield exactly one message
- Message SHALL have status="completed"
- Message SHALL have total=0 and completed=0
- Message SHALL have empty web_info_list

**Validates: Requirements 2.7, 6.4**

### Property 4: File Filtering Correctness

*For any* repository with mixed file types:
- Binary files SHALL NOT appear in results (detected via null bytes or magic bytes)
- Files in .git directory SHALL NOT appear in results
- Files larger than MAX_FILE_SIZE SHALL NOT appear in results
- Symlinks SHALL NOT be followed or included
- Non-UTF-8 files SHALL NOT appear in results
- Paths with ".." SHALL be rejected

**Validates: Requirements 5.3, 5.4, 5.5, 5.6, 5.7**

### Property 5: Path Normalization

*For any* file path:
- source_url and title SHALL use POSIX format (/)
- Paths SHALL NOT contain "./" prefix
- Paths SHALL NOT contain ".."
- Paths SHALL NOT have leading "/"

**Validates: Requirements 2.8, 6.2**

### Property 6: SHA Storage Round-Trip

*For any* successful sync operation:
- The current HEAD SHA SHALL be stored in session.storage
- On next sync, the stored SHA SHALL be retrievable
- The storage key SHALL be deterministic based on repo_url, branch, subdir, extensions

**Validates: Requirements 3.2, 3.6**

### Property 7: Failed Paths Retry

*For any* sync where some files failed to read:
- Failed paths SHALL be stored in session.storage
- On next sync, failed paths SHALL be included in paths to process
- Successfully processed paths SHALL be removed from failed list

**Validates: Requirements 3.3, 7.4**

### Property 8: Incremental Sync Correctness

*For any* sync where last SHA exists and is reachable:
- Only files in the changeset (added/modified) plus failed_paths SHALL be returned
- Files unchanged since last SHA (and not in failed_paths) SHALL NOT be returned

**Validates: Requirements 3.3**

### Property 9: Full Sync Fallback

*For any* sync where last SHA is not reachable (force push) OR no last SHA exists:
- All files matching filters SHALL be returned
- The sync SHALL complete successfully

**Validates: Requirements 3.4, 3.5**

### Property 10: Credential Masking in Errors

*For any* error message containing repository URL or credentials:
- Access tokens SHALL be masked (replaced with ***)
- SSH keys SHALL NOT appear in error messages
- Passwords SHALL be masked

**Validates: Requirements 7.5** (existing tests cover this)

## Error Handling

### Fatal Errors (stop sync)

| Condition | Error Message | Action |
|-----------|---------------|--------|
| Invalid URL format | "Invalid repository URL: {masked_url}" | Raise exception |
| Auth failure | "Authentication failed for {masked_url}" | Raise exception |
| Repo not found | "Repository not found: {masked_url}" | Raise exception |
| Network error | "Network error: {details}" | Raise exception |
| Path traversal | "Path traversal detected: {path}" | Raise exception |

### Non-Fatal Errors (skip and continue)

| Condition | Action | Logging | Add to failed_paths? |
|-----------|--------|---------|---------------------|
| File too large | Skip file | Warning: "Skipping large file: {path} ({size} bytes)" | NO (permanent) |
| Binary file | Skip file | Debug: "Skipping binary file: {path}" | NO (permanent) |
| Non-UTF-8 file | Skip file | Warning: "Skipping non-UTF-8 file: {path}" | NO (permanent) |
| Symlink | Skip file | Debug: "Skipping symlink: {path}" | NO (permanent) |
| IOError/network | Skip file | Warning: "Failed to read file: {path}: {error}" | YES (transient) |

## Testing Strategy

### Unit Tests

1. **Configuration Tests**
   - Verify provider YAML has `provider_type: website_crawl`
   - Verify manifest has `minimum_dify_version: 1.11.1`
   - Verify datasource YAML has correct parameters

2. **Class Structure Tests**
   - Verify `GitWebsiteCrawlDatasource` inherits from `WebsiteCrawlDatasource`
   - Verify `_get_website_crawl` method exists

3. **Path Normalization Tests**
   - Test POSIX conversion
   - Test "./" removal
   - Test ".." rejection
   - Test leading "/" removal

4. **Error Handling Tests**
   - Test invalid URL error message
   - Test auth failure error message
   - Test repo not found error message

### Property-Based Tests

Using `hypothesis` library with minimum 100 iterations per test.

1. **Property 1: WebSiteInfoDetail Structure**
   - Generate random file paths and contents
   - Verify all required fields are present and correct format

2. **Property 2: Batching Correctness**
   - Generate random number of files (1-500)
   - Verify batch sizes, status values, and monotonic completed

3. **Property 3: Empty Result**
   - Test with empty file list
   - Verify single completed message

4. **Property 4: File Filtering**
   - Generate mixed file types (text, binary, symlinks)
   - Verify only valid text files are included

5. **Property 5: Path Normalization**
   - Generate random paths with various formats
   - Verify normalized output

6. **Property 6: SHA Storage**
   - Generate random SHAs
   - Verify storage round-trip

7. **Property 7: Failed Paths Retry**
   - Generate random failed paths
   - Verify retry on next sync

### Integration Tests

1. **Full Sync Flow**
   - Clone test repository
   - Verify all files returned
   - Verify SHA stored

2. **Incremental Sync Flow**
   - Modify test repository
   - Verify only changed files returned

3. **Dify Semantics Validation** (DD1)
   - Full sync → delta sync
   - Verify unchanged documents not orphaned

4. **Authentication Tests**
   - Test HTTPS with token
   - Test SSH with key
   - Test local path
