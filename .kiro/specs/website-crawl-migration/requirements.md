# Requirements Document

## Introduction

Миграция Git Datasource плагина с типа `online_drive` на `website_crawl` для автоматической загрузки всех файлов репозитория без ручного выбора пользователем.

**Модель синхронизации:** Delta-модель — плагин возвращает только добавленные/изменённые файлы. Удаления не отслеживаются автоматически (ограничение API). Это будет явно задокументировано.

## Glossary

- **Plugin**: Dify плагин для импорта данных из Git репозитория
- **WebsiteCrawlDatasource**: Базовый класс SDK для плагинов типа website_crawl
- **WebSiteInfo**: Структура данных для возврата результатов краулинга
- **WebSiteInfoDetail**: Структура данных для одного документа (файла)
- **GitClient**: Существующий класс для работы с Git репозиториями
- **Delta_Model**: Модель синхронизации, при которой возвращаются только изменённые файлы
- **Batch**: Порция файлов, отправляемая через generator для избежания таймаутов
- **config_hash**: Уникальный хеш конфигурации `sha256(repo_url:branch:subdir:canonicalized_extensions)[:16]`, где extensions канонизированы (sorted, lowercase, trimmed)
- **transient_error**: Временная ошибка (IOError, network), файл будет повторно обработан
- **permanent_skip**: Постоянный пропуск (binary, non-UTF-8, too large, symlink), файл не будет повторно обработан

## Requirements

### Requirement 1: Изменение типа провайдера

**User Story:** Как разработчик, я хочу изменить тип плагина на website_crawl, чтобы Dify автоматически загружал все файлы без ручного выбора.

#### Acceptance Criteria

1. (R1.AC1) THE Plugin SHALL use `provider_type: website_crawl` in provider YAML configuration
2. (R1.AC2) THE Plugin SHALL inherit from `WebsiteCrawlDatasource` class instead of `OnlineDriveDatasource`
3. (R1.AC3) THE Plugin SHALL implement `_get_website_crawl` method as the main entry point
4. (R1.AC4) THE manifest.yaml SHALL specify `minimum_dify_version: 1.11.1`

### Requirement 2: Полная загрузка репозитория с батчингом

**User Story:** Как пользователь Dify, я хочу подключить Git репозиторий и автоматически получить все файлы в базу знаний.

#### Acceptance Criteria

1. (R2.AC1) WHEN the plugin is invoked, THE Plugin SHALL clone the repository if not cached
2. (R2.AC2) WHEN the repository is already cached, THE Plugin SHALL fetch latest changes
3. (R2.AC3) THE Plugin SHALL recursively traverse all directories and collect text files
4. (R2.AC4) FOR EACH text file, THE Plugin SHALL create a WebSiteInfoDetail with title, content, and source_url
5. (R2.AC5) THE Plugin SHALL stream results in batches (configurable, default 50 files per batch)
6. (R2.AC6) WHILE streaming batches, THE Plugin SHALL emit status="processing" for intermediate batches
7. (R2.AC7) WHEN all files processed, THE Plugin SHALL emit final batch with status="completed"
8. (R2.AC8) THE Plugin SHALL use normalized file path as unique identifier (source_url) for document tracking

### Requirement 3: Инкрементальная синхронизация (Delta-модель)

**User Story:** Как пользователь, я хочу обновлять базу знаний при изменениях в репозитории нажатием кнопки Sync.

#### Acceptance Criteria

1. (R3.AC1) WHEN sync is triggered, THE Plugin SHALL fetch latest changes from remote
2. (R3.AC2) THE Plugin SHALL track last synced SHA in session.storage
3. (R3.AC3) WHEN last SHA exists and is reachable, THE Plugin SHALL return only added/modified files since last SHA
4. (R3.AC4) WHEN last SHA is not reachable (force push), THE Plugin SHALL perform full sync
5. (R3.AC5) WHEN no last SHA exists (first sync), THE Plugin SHALL return all files
6. (R3.AC6) THE Plugin SHALL update stored SHA after successful sync
7. (R3.AC7) THE Plugin SHALL NOT track deletions (documented limitation of Delta-model)

### Requirement 4: Аутентификация

**User Story:** Как пользователь, я хочу подключать приватные репозитории с различными методами аутентификации.

#### Acceptance Criteria

1. (R4.AC1) THE Plugin SHALL support HTTPS URLs with access token authentication
2. (R4.AC2) THE Plugin SHALL support SSH URLs with private key authentication
3. (R4.AC3) THE Plugin SHALL support local repository paths without authentication
4. (R4.AC4) THE Plugin SHALL normalize SSH keys (handle literal \n, Windows line endings)
5. (R4.AC5) IF authentication fails, THEN THE Plugin SHALL return descriptive error message
6. (R4.AC6) THE Plugin SHALL store repo_url, branch, subdir, extensions as datasource parameters (not provider credentials)

### Requirement 5: Фильтрация файлов

**User Story:** Как пользователь, я хочу контролировать какие файлы из репозитория попадут в базу знаний.

#### Acceptance Criteria

1. (R5.AC1) THE Plugin SHALL support subdirectory filter parameter
2. (R5.AC2) THE Plugin SHALL support file extensions filter parameter
3. (R5.AC3) THE Plugin SHALL exclude binary files by default
4. (R5.AC4) THE Plugin SHALL exclude .git directory
5. (R5.AC5) THE Plugin SHALL skip files larger than configurable limit (default 5MB)
6. (R5.AC6) THE Plugin SHALL NOT follow symlinks (security: prevent path traversal)
7. (R5.AC7) WHEN file is not valid UTF-8, THE Plugin SHALL skip it and log warning

### Requirement 6: Формат выходных данных

**User Story:** Как система Dify, я хочу получать данные в формате WebSiteInfo для корректной индексации.

#### Acceptance Criteria

1. (R6.AC1) THE Plugin SHALL return WebSiteInfo object with web_info_list, status, total, completed fields
2. (R6.AC2) FOR EACH file, THE Plugin SHALL create WebSiteInfoDetail with:
   - title: relative file path
   - content: file text content (UTF-8)
   - source_url: unique identifier (git:{hash}:{path})
   - description: optional metadata (repo URL, branch)
3. (R6.AC3) WHILE processing, THE Plugin SHALL set status to "processing"
4. (R6.AC4) WHEN finished, THE Plugin SHALL set status to "completed"
5. (R6.AC5) THE Plugin SHALL set total to number of paths attempted (known upfront after filtering)
6. (R6.AC6) THE Plugin SHALL set completed to number of paths attempted so far (including skipped and failed)

### Requirement 7: Обработка ошибок

**User Story:** Как пользователь, я хочу получать понятные сообщения об ошибках при проблемах с подключением.

#### Acceptance Criteria

1. (R7.AC1) IF repository URL is invalid, THEN THE Plugin SHALL raise fatal error with message "Invalid repository URL"
2. (R7.AC2) IF authentication fails, THEN THE Plugin SHALL raise fatal error with message "Authentication failed"
3. (R7.AC3) IF repository not found, THEN THE Plugin SHALL raise fatal error with message "Repository not found"
4. (R7.AC4) IF single file read fails with transient error (IOError, network), THEN THE Plugin SHALL skip file, add to failed_paths, and log warning (non-fatal)
5. (R7.AC5) IF file is binary or non-UTF-8 (permanent skip), THEN THE Plugin SHALL skip file WITHOUT adding to failed_paths
6. (R7.AC6) THE Plugin SHALL mask credentials in all error messages

### Requirement 8: Совместимость с существующим кодом

**User Story:** Как разработчик, я хочу переиспользовать существующий GitClient и утилиты.

#### Acceptance Criteria

1. (R8.AC1) THE Plugin SHALL reuse existing GitClient class for Git operations
2. (R8.AC2) THE Plugin SHALL reuse existing credential handling (SSH key normalization)
3. (R8.AC3) THE Plugin SHALL reuse existing filtering utilities
4. (R8.AC4) THE Plugin SHALL maintain existing test coverage where applicable
5. (R8.AC5) THE Plugin SHALL disable (not delete) OnlineDriveDatasource implementation after migration

### Requirement 9: Документация ограничений

**User Story:** Как пользователь, я хочу понимать ограничения плагина.

#### Acceptance Criteria

1. (R9.AC1) THE README SHALL document that deletions are not automatically tracked (Delta-model limitation)
2. (R9.AC2) THE README SHALL document that users may need to manually remove orphaned documents in Dify UI if files are deleted from repository
3. (R9.AC3) THE README SHALL document supported authentication methods
4. (R9.AC4) THE README SHALL document file size and type limitations
5. (R9.AC5) THE manifest.yaml SHALL include `resource.permission.storage` for session storage access
