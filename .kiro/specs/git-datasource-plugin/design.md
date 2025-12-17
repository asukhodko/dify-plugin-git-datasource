# Design Document: Git Datasource Plugin

## Overview

Git Datasource Plugin — это Dify плагин типа `online_drive`, который позволяет использовать Git репозитории как источник данных для Knowledge Base. Плагин реализует интерфейс `OnlineDriveDatasource` с двумя основными методами: `_browse_files()` для навигации по файлам и `_download_file()` для получения содержимого.

Ключевая особенность — поддержка инкрементальной синхронизации через отслеживание SHA коммитов в `session.storage`.

## Architecture

```mermaid
graph TB
    subgraph "Dify Platform"
        UI[Dify UI]
        KB[Knowledge Base]
        PS[Plugin System]
    end
    
    subgraph "Git Datasource Plugin"
        Provider[GitDatasourceProvider]
        DS[GitDataSource]
        GC[GitClient]
        Cache[Repository Cache]
        Storage[Session Storage]
    end
    
    subgraph "Git Repositories"
        HTTPS[HTTPS Repos]
        SSH[SSH Repos]
        Local[Local Repos]
    end
    
    UI --> PS
    PS --> Provider
    PS --> DS
    DS --> GC
    DS --> Storage
    GC --> Cache
    GC --> HTTPS
    GC --> SSH
    GC --> Local
    DS --> KB
```

### Компоненты

1. **GitDatasourceProvider** — валидация credentials при настройке источника
2. **GitDataSource** — основная логика browse/download, реализует `OnlineDriveDatasource`
3. **GitClient** — абстракция над Git операциями (clone, fetch, diff, read)
4. **Repository Cache** — локальный кэш клонированных репозиториев
5. **Session Storage** — хранение `last_synced_sha` между вызовами

### Поток данных

```mermaid
sequenceDiagram
    participant Dify
    participant Plugin
    participant GitClient
    participant Storage
    participant Repo
    
    Dify->>Plugin: _browse_files(request)
    Plugin->>Storage: get(last_synced_sha)
    Storage-->>Plugin: sha or None
    Plugin->>GitClient: ensure_cloned()
    GitClient->>Repo: clone/fetch
    Repo-->>GitClient: ok
    Plugin->>GitClient: get_head_sha()
    GitClient-->>Plugin: current_sha
    
    alt First Sync
        Plugin->>GitClient: list_all_files()
    else Incremental Sync
        Plugin->>GitClient: get_changed_files(old_sha, new_sha)
    end
    
    GitClient-->>Plugin: files[]
    Plugin->>Storage: set(last_synced_sha, current_sha)
    Plugin-->>Dify: OnlineDriveBrowseFilesResponse
```

## Components and Interfaces

### GitDataSource (OnlineDriveDatasource)

```python
class GitDataSource(OnlineDriveDatasource):
    """
    Основной класс datasource.
    Реализует интерфейс OnlineDriveDatasource.
    """
    
    def _browse_files(self, request: OnlineDriveBrowseFilesRequest) -> OnlineDriveBrowseFilesResponse:
        """
        Получение списка файлов для индексации.
        
        Логика:
        1. Получить last_synced_sha из storage
        2. Обеспечить наличие локального клона (clone/fetch)
        3. Определить тип sync (full/incremental)
        4. Получить список файлов
        5. Сохранить новый SHA
        6. Вернуть отфильтрованный список
        """
        pass
    
    def _download_file(self, request: OnlineDriveDownloadFileRequest) -> Generator[DatasourceMessage, None, None]:
        """
        Скачивание содержимого файла.
        
        Логика:
        1. Получить путь файла из request.id
        2. Прочитать содержимое из репозитория
        3. Определить MIME тип
        4. Вернуть blob message
        """
        pass
```

### GitClient

```python
class GitClient:
    """
    Абстракция над Git операциями.
    
    Выбор библиотеки:
    - MVP: GitPython (требует системный git, проще API)
    - Production: Dulwich (pure Python, лучшая портативность)
    
    Критерии выбора:
    - Наличие git в контейнере плагина
    - Поддержка SSH аутентификации
    - Производительность на больших репозиториях
    """
    
    def __init__(self, repo_url: str, branch: str, credentials: dict, cache_dir: str):
        pass
    
    def ensure_cloned(self) -> None:
        """Клонировать репозиторий если не существует, иначе fetch."""
        pass
    
    def get_head_sha(self) -> str:
        """Получить SHA текущего HEAD для указанной ветки."""
        pass
    
    def is_sha_reachable(self, old_sha: str, new_sha: str) -> bool:
        """Проверить достижимость old_sha из new_sha."""
        pass
    
    def list_all_files(self, subdir: str, extensions: list[str]) -> list[FileInfo]:
        """Получить список всех файлов (для full sync)."""
        pass
    
    def get_changed_files(self, old_sha: str, new_sha: str, subdir: str, extensions: list[str]) -> ChangeSet:
        """Получить изменения между коммитами (для incremental sync)."""
        pass
    
    def read_file(self, file_path: str) -> bytes:
        """Прочитать содержимое файла."""
        pass
```

### Data Structures

```python
@dataclass
class FileInfo:
    """Информация о файле."""
    path: str           # Полный путь от корня репозитория
    name: str           # Имя файла
    size: int           # Размер в байтах
    type: str           # "file" или "folder"

@dataclass
class ChangeSet:
    """Набор изменений между коммитами."""
    added: list[str]    # Добавленные файлы
    modified: list[str] # Изменённые файлы
    deleted: list[str]  # Удалённые файлы
    renamed: list[tuple[str, str]]  # (old_path, new_path)
```

### GitDatasourceProvider

```python
class GitDatasourceProvider(DatasourceProvider):
    """
    Провайдер для валидации credentials.
    """
    
    def _validate_credentials(self, credentials: Mapping[str, Any]) -> None:
        """
        Валидация учётных данных.
        
        Проверки:
        1. Наличие repo_url
        2. Корректность формата URL
        3. Соответствие auth type и URL (SSH URL требует SSH key)
        4. Тестовое подключение к репозиторию
        """
        pass
```

## Data Models

### Credentials Schema (YAML)

```yaml
credentials_schema:
  - name: repo_url
    type: text-input
    required: true
    
  - name: branch
    type: text-input
    required: false
    default: main
    
  - name: access_token
    type: secret-input
    required: false
    
  - name: ssh_private_key
    type: secret-input
    required: false
    
  - name: subdir
    type: text-input
    required: false
    
  - name: extensions
    type: text-input
    required: false
    placeholder: ".md,.txt,.rst"
```

### Storage Keys

| Key Pattern | Value | Description |
|-------------|-------|-------------|
| `git_browse:{hash}` | SHA string (UTF-8 bytes) | Last browsed commit SHA (best-effort marker) |

Где `{hash}` = `sha256(repo_url:branch:subdir:extensions)[:16]`

**Важно:** 
- Ключ включает все параметры конфигурации, чтобы изменение фильтров приводило к новому full sync
- `Last_Browsed_SHA` — это best-effort маркер, т.к. Dify может вызывать browse без завершения индексации

### File ID Strategy

File ID должен быть **стабильным** и **не содержать volatile данных**:

```python
# ✅ Правильно: путь относительно корня репозитория
file_id = "docs/guide/getting-started.md"

# ❌ Неправильно: включает SHA (создаст дубли при каждом коммите)
file_id = f"{commit_sha}:{file_path}"
```

### OnlineDriveFile Mapping

| Git File | OnlineDriveFile |
|----------|-----------------|
| path | id |
| basename | name |
| blob size | size |
| tree/blob | type ("folder"/"file") |



## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Based on the prework analysis, the following correctness properties have been identified:

### Property 1: Invalid URL Rejection

*For any* string that does not match valid Git URL patterns (https://, http://, git@, ssh://, file://, or absolute path), the URL validation function SHALL reject it with an appropriate error message.

**Validates: Requirements 1.2**

### Property 2: Credential Masking

*For any* credentials (access_token, ssh_private_key, password) and any error message or log output, the credentials SHALL NOT appear in plain text in the output.

**Validates: Requirements 1.3, 7.4**

### Property 3: Subdirectory Filtering

*For any* list of file paths and any subdirectory filter, all files returned by the filter function SHALL have paths that start with the specified subdirectory prefix.

**Validates: Requirements 2.2**

### Property 4: Extension Filtering

*For any* list of file paths and any set of extension filters, all files returned by the filter function SHALL have extensions matching one of the specified filters.

**Validates: Requirements 2.3**

### Property 5: Pagination Correctness

*For any* list of files with length greater than max_keys, the browse response SHALL have is_truncated=true and the returned files list SHALL have length equal to max_keys.

**Validates: Requirements 2.4**

### Property 6: MIME Type Detection

*For any* file path with a known extension, the MIME type detection function SHALL return the correct MIME type for that extension.

**Validates: Requirements 3.1**

### Property 7: Full Sync Mode Selection

*For any* browse request where Session_Storage does not contain a last_synced_sha, the plugin SHALL perform full sync (return all matching files).

**Validates: Requirements 4.1**

### Property 8: SHA Storage After Browse

*For any* successful browse operation that returns at least one file, the current HEAD SHA SHALL be stored in Session_Storage as last_browsed_sha. If no files match filters, SHA SHALL NOT be updated.

**Validates: Requirements 4.2, 4.4, 5.6**

### Property 9: Changeset Handling

*For any* changeset with added, modified, deleted, and renamed files:
- All added files SHALL be included in the response
- All modified files SHALL be included in the response  
- All deleted files SHALL be excluded from the response
- For renamed files (old_path, new_path): old_path SHALL be excluded and new_path SHALL be included

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

### Property 10: Token URL Construction

*For any* HTTPS URL and access token, the constructed authenticated URL SHALL contain the token in the correct position (https://token:{token}@host/...) and SHALL be a valid URL. The authenticated URL SHALL NEVER be logged or included in error messages.

**Validates: Requirements 6.2, 7.4**

### Property 11: Local Path Detection

*For any* path starting with "/" or "file://", the URL type detection function SHALL classify it as a local repository.

**Validates: Requirements 6.4**

### Property 12: Sync Fallback Conditions

*For any* scenario where last_synced_sha is not reachable from HEAD OR the commit count between SHAs exceeds the threshold, the plugin SHALL fall back to full sync mode.

**Validates: Requirements 7.1, 7.2**

### Property 13: Cache Reuse

*For any* repository URL that has been previously cloned to cache, subsequent access SHALL perform fetch instead of full clone.

**Validates: Requirements 8.2**

### Property 14: SHA Serialization Round-Trip

*For any* valid SHA string, serializing it to bytes (UTF-8) and deserializing back SHALL produce the original SHA string.

**Validates: Requirements 9.1, 9.2**

### Property 15: FileInfo Serialization Round-Trip

*For any* valid FileInfo object, serializing to JSON and deserializing back SHALL produce an equivalent FileInfo object.

**Validates: Requirements 9.3**

### Property 16: Stable File ID

*For any* file path, the generated file ID SHALL be equal to the file path relative to repository root, without any commit SHA or volatile data.

**Validates: Requirements 10.1, 10.2, 10.3**

### Property 17: Storage Key Uniqueness

*For any* two configurations with different values of (repo_url, branch, subdir, extensions), the generated storage keys SHALL be different.

**Validates: Requirements 11.1, 11.2**

## Error Handling

### Error Categories

| Category | HTTP-like Code | Description | User Action |
|----------|---------------|-------------|-------------|
| ValidationError | 400 | Invalid configuration | Fix configuration |
| AuthenticationError | 401 | Invalid credentials | Update credentials |
| NotFoundError | 404 | File/repo not found | Check path/URL |
| TimeoutError | 408 | Operation timeout | Retry later |
| InternalError | 500 | Unexpected error | Contact support |

### Error Message Format

```python
class PluginError(Exception):
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
```

### Credential Masking

All error messages MUST mask sensitive data:

```python
def mask_credentials(text: str, credentials: dict) -> str:
    """Replace credential values with '***' in text."""
    result = text
    for key in ['access_token', 'ssh_private_key', 'password']:
        if key in credentials and credentials[key]:
            result = result.replace(credentials[key], '***')
    return result
```

## Testing Strategy

### Dual Testing Approach

This plugin uses both unit tests and property-based tests:

1. **Unit Tests** — verify specific examples and edge cases
2. **Property-Based Tests** — verify universal properties across random inputs

### Property-Based Testing Framework

**Library:** `hypothesis` (Python)

**Configuration:**
- Minimum iterations: 100
- Max examples: 200
- Deadline: 5000ms (for slower operations)

### Test Organization

```
tests/
├── unit/
│   ├── test_provider.py      # Credential validation
│   ├── test_datasource.py    # Browse/download logic
│   ├── test_git_client.py    # Git operations
│   └── test_utils.py         # Utility functions
├── property/
│   ├── test_url_validation.py    # Property 1
│   ├── test_credential_masking.py # Property 2
│   ├── test_filtering.py         # Properties 3, 4
│   ├── test_pagination.py        # Property 5
│   ├── test_mime_types.py        # Property 6
│   ├── test_sync_mode.py         # Properties 7, 12
│   ├── test_storage.py           # Property 8
│   ├── test_changeset.py         # Property 9
│   ├── test_url_construction.py  # Properties 10, 11
│   ├── test_cache.py             # Property 13
│   └── test_serialization.py     # Properties 14, 15
└── integration/
    └── test_full_flow.py     # End-to-end tests
```

### Property Test Annotation Format

Each property-based test MUST include a comment referencing the design document:

```python
# **Feature: git-datasource-plugin, Property 1: Invalid URL Rejection**
# **Validates: Requirements 1.2**
@given(st.text())
def test_invalid_url_rejection(url: str):
    ...
```

### Generators (Hypothesis Strategies)

```python
# Valid Git URLs
valid_https_urls = st.from_regex(
    r'https://[a-z0-9.-]+/[a-z0-9_-]+/[a-z0-9_-]+\.git',
    fullmatch=True
)

# Valid SHA strings
valid_shas = st.from_regex(r'[0-9a-f]{40}', fullmatch=True)

# File paths
file_paths = st.from_regex(r'[a-z0-9_-]+(/[a-z0-9_-]+)*\.[a-z]+', fullmatch=True)

# FileInfo objects
file_infos = st.builds(
    FileInfo,
    path=file_paths,
    name=st.from_regex(r'[a-z0-9_-]+\.[a-z]+', fullmatch=True),
    size=st.integers(min_value=0, max_value=10_000_000),
    type=st.sampled_from(['file', 'folder'])
)

# Changesets
changesets = st.builds(
    ChangeSet,
    added=st.lists(file_paths, max_size=10),
    modified=st.lists(file_paths, max_size=10),
    deleted=st.lists(file_paths, max_size=10),
    renamed=st.lists(st.tuples(file_paths, file_paths), max_size=5)
)
```
