# Requirements Document

## Introduction

Данный документ описывает требования к Dify Data Source плагину для синхронизации документов из Git репозиториев. Плагин позволяет использовать Git репозитории (локальные, GitLab, Gitea, GitHub) как источник данных для Dify Knowledge Base с поддержкой инкрементальной синхронизации.

## Glossary

- **Git_Datasource_Plugin**: Dify плагин типа `online_drive`, обеспечивающий доступ к файлам Git репозитория
- **Knowledge_Base**: Хранилище документов Dify для RAG (Retrieval-Augmented Generation)
- **Incremental_Sync**: Процесс синхронизации только изменённых файлов с момента последнего sync
- **Full_Sync**: Процесс синхронизации всех файлов репозитория
- **Last_Browsed_SHA**: SHA коммита, на котором был выполнен последний browse (best-effort маркер для инкрементального sync)
- **Session_Storage**: Persistent key-value хранилище Dify для сохранения состояния между вызовами
- **Credentials**: Учётные данные для доступа к репозиторию (токен, SSH ключ)

## Requirements

### Requirement 1

**User Story:** As a Dify user, I want to connect a Git repository as a data source, so that I can import documents for RAG indexing.

#### Acceptance Criteria

1. WHEN a user provides a valid repository URL and credentials THEN the Git_Datasource_Plugin SHALL validate the connection and confirm access
2. WHEN a user configures the data source with an invalid URL THEN the Git_Datasource_Plugin SHALL return a clear error message describing the issue
3. WHEN a user configures the data source with invalid credentials THEN the Git_Datasource_Plugin SHALL return an authentication error without exposing sensitive data in logs

### Requirement 2

**User Story:** As a Dify user, I want to browse files in a Git repository, so that I can select documents for indexing.

#### Acceptance Criteria

1. WHEN a user requests file listing THEN the Git_Datasource_Plugin SHALL return a hierarchical list of files and folders from the repository
2. WHEN a user specifies a subdirectory filter THEN the Git_Datasource_Plugin SHALL return only files within that subdirectory
3. WHEN a user specifies file extension filters THEN the Git_Datasource_Plugin SHALL return only files matching those extensions
4. WHEN the file list exceeds the page size limit THEN the Git_Datasource_Plugin SHALL support pagination with next_page_parameters

### Requirement 3

**User Story:** As a Dify user, I want to download file content from a Git repository, so that Dify can index the documents.

#### Acceptance Criteria

1. WHEN a user requests file content THEN the Git_Datasource_Plugin SHALL return the file content as a blob with correct MIME type
2. WHEN a user requests content of a non-existent file THEN the Git_Datasource_Plugin SHALL return a file not found error
3. WHEN a file exceeds the maximum size limit THEN the Git_Datasource_Plugin SHALL skip the file and log a warning

### Requirement 4

**User Story:** As a Dify user, I want to perform initial sync of all documents, so that my Knowledge Base contains all repository files.

#### Acceptance Criteria

1. WHEN no Last_Browsed_SHA exists in Session_Storage THEN the Git_Datasource_Plugin SHALL perform Full_Sync and return all matching files
2. WHEN browse operation completes successfully AND at least one file was returned THEN the Git_Datasource_Plugin SHALL store the current HEAD SHA as Last_Browsed_SHA in Session_Storage
3. WHEN Full_Sync is performed THEN the Git_Datasource_Plugin SHALL traverse the repository tree at HEAD (no git history required beyond HEAD tree)
4. WHEN browse is called but no files match filters THEN the Git_Datasource_Plugin SHALL NOT update Last_Browsed_SHA to prevent data loss on next sync

**Note on Best-Effort Incremental Sync:** Dify may call `_browse_files()` for UI navigation without completing indexing. Therefore, incremental sync is best-effort and may skip files if Dify calls browse without completing indexing. For guaranteed sync, use external orchestration that calls Dify API after confirming indexing completion.

### Requirement 5

**User Story:** As a Dify user, I want to perform incremental sync, so that only changed documents are re-indexed.

#### Acceptance Criteria

1. WHEN Last_Browsed_SHA exists and is reachable from HEAD THEN the Git_Datasource_Plugin SHALL perform Incremental_Sync returning only changed files
2. WHEN Incremental_Sync detects added files THEN the Git_Datasource_Plugin SHALL include those files in the response
3. WHEN Incremental_Sync detects modified files THEN the Git_Datasource_Plugin SHALL include those files in the response
4. WHEN Incremental_Sync detects deleted files THEN the Git_Datasource_Plugin SHALL NOT include those files in the response (Dify MAY mark corresponding documents as orphaned)
5. WHEN Incremental_Sync detects renamed files THEN the Git_Datasource_Plugin SHALL treat them as delete of old path plus add of new path
6. WHEN Incremental_Sync completes successfully with files returned THEN the Git_Datasource_Plugin SHALL update Last_Browsed_SHA in Session_Storage

**Note on Deletion Handling:** Dify online_drive datasource does not provide explicit deletion API. When files are removed from Git, they will not appear in browse results. Dify MAY mark corresponding documents as "orphaned" (exact behavior to be verified in task 1.2). Users may need to manually remove orphaned documents, or use external process with Dify API.

### Requirement 6

**User Story:** As a Dify user, I want to connect to repositories using different authentication methods, so that I can access both public and private repositories.

#### Acceptance Criteria

1. WHEN a user provides an HTTPS URL without credentials THEN the Git_Datasource_Plugin SHALL connect to public repositories
2. WHEN a user provides an HTTPS URL with an access token THEN the Git_Datasource_Plugin SHALL authenticate using the token
3. WHEN a user provides an SSH URL with a private key THEN the Git_Datasource_Plugin SHALL authenticate using SSH key authentication
4. WHEN a user provides a local filesystem path THEN the Git_Datasource_Plugin SHALL access the repository directly without network operations

### Requirement 7

**User Story:** As a Dify user, I want the plugin to handle edge cases gracefully, so that sync operations are reliable.

#### Acceptance Criteria

1. WHEN Last_Browsed_SHA is not reachable from HEAD (force push scenario) THEN the Git_Datasource_Plugin SHALL fall back to Full_Sync
2. WHEN the number of commits between syncs exceeds a threshold THEN the Git_Datasource_Plugin SHALL fall back to Full_Sync for performance
3. WHEN a repository clone or fetch operation times out THEN the Git_Datasource_Plugin SHALL return a timeout error with retry guidance
4. WHEN credentials contain sensitive data THEN the Git_Datasource_Plugin SHALL mask them in all error messages and logs
5. WHEN authenticated URL is constructed with embedded token THEN the Git_Datasource_Plugin SHALL NEVER log or include this URL in error messages

### Requirement 8

**User Story:** As a Dify user, I want to configure repository caching, so that sync operations are faster.

#### Acceptance Criteria

1. WHEN a repository is accessed for the first time THEN the Git_Datasource_Plugin SHALL clone it to a local cache directory
2. WHEN a cached repository exists THEN the Git_Datasource_Plugin SHALL perform fetch instead of full clone
3. WHEN shallow clone is used AND incremental sync requires unreachable history THEN the Git_Datasource_Plugin SHALL fall back to Full_Sync instead of failing

**Note on Shallow Clone:** Shallow clone (depth=1) saves disk space but limits incremental sync capability. If Last_Synced_SHA is not in shallow history, the plugin falls back to full sync. For repositories with frequent syncs, full clone is recommended.

### Requirement 9

**User Story:** As a developer, I want the plugin to serialize and deserialize file metadata correctly, so that sync state is preserved.

#### Acceptance Criteria

1. WHEN storing Last_Synced_SHA THEN the Git_Datasource_Plugin SHALL serialize it as UTF-8 encoded bytes
2. WHEN retrieving Last_Synced_SHA THEN the Git_Datasource_Plugin SHALL deserialize it correctly from Session_Storage
3. WHEN serializing file metadata THEN the Git_Datasource_Plugin SHALL produce valid JSON that can be round-tripped without data loss

### Requirement 10

**User Story:** As a developer, I want stable file identifiers, so that Dify can correctly track document updates without creating duplicates.

#### Acceptance Criteria

1. WHEN generating file ID for OnlineDriveFile THEN the Git_Datasource_Plugin SHALL use the file path relative to repository root as the stable identifier
2. WHEN the same file is returned in multiple browse calls THEN the Git_Datasource_Plugin SHALL return the same ID value
3. WHEN file ID is generated THEN the Git_Datasource_Plugin SHALL NOT include commit SHA or other volatile data in the ID

### Requirement 11

**User Story:** As a developer, I want the storage key to include all configuration parameters, so that different configurations do not share sync state.

#### Acceptance Criteria

1. WHEN generating storage key THEN the Git_Datasource_Plugin SHALL include repo_url, branch, subdir, and extensions in the key hash
2. WHEN any configuration parameter changes THEN the Git_Datasource_Plugin SHALL generate a different storage key resulting in fresh Full_Sync
