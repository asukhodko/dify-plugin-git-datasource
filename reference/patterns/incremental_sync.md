# Паттерн инкрементальной синхронизации

## Обзор

Инкрементальная синхронизация позволяет обновлять только измененные документы,
вместо полной переиндексации всего репозитория.

## Ключевые концепции

### 1. Маркер состояния (State Marker)

Для Git репозитория используем **SHA коммита** как маркер состояния:

```
last_synced_sha = "abc123def456..."
```

Преимущества:
- Уникально идентифицирует состояние репозитория
- Позволяет вычислить diff между состояниями
- Не зависит от времени

### 2. Стабильный ID документа

Каждый документ должен иметь стабильный ID для:
- Определения "тот же документ или новый"
- Обновления существующих документов
- Удаления документов

Формат ID для Git:
```
{repo_hash}::{ref}::{file_path}
```

Пример:
```
a1b2c3d4e5f6::main::docs/guide/getting-started.md
```

### 3. Change Detection

Определение изменений между `old_sha` и `new_sha`:

| Тип изменения | Действие в Dify |
|---------------|-----------------|
| Added (A) | Создать новый документ |
| Modified (M) | Обновить существующий документ |
| Deleted (D) | Удалить документ |
| Renamed (R) | Удалить старый + создать новый |

## Алгоритм синхронизации

```
┌─────────────────────────────────────────────────────────────┐
│                    SYNC ALGORITHM                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Получить current_sha = HEAD(ref)                        │
│                                                             │
│  2. Получить last_synced_sha из хранилища                   │
│                                                             │
│  3. IF last_synced_sha is None OR not reachable:            │
│        → FULL SYNC (все файлы)                              │
│     ELSE:                                                   │
│        → INCREMENTAL SYNC (только изменения)                │
│                                                             │
│  4. Выполнить sync actions                                  │
│                                                             │
│  5. Сохранить current_sha как last_synced_sha               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Реализация

### Full Sync

```python
def full_sync(repo_path: str, ref: str, config: dict) -> list[DataSourceItem]:
    """
    Полная синхронизация — возвращает все файлы.
    """
    items = []
    
    for file_info in list_files(repo_path, ref, config):
        item = DataSourceItem(
            id=make_item_id(repo_path, ref, file_info.path),
            name=file_info.name,
            type="file",
            size=file_info.size,
            updated_at=file_info.last_commit_time,
            metadata={
                "path": file_info.path,
                "ref": ref,
                "commit_sha": file_info.last_commit_sha,
            }
        )
        items.append(item)
    
    return items
```

### Incremental Sync

```python
def incremental_sync(
    repo_path: str,
    ref: str,
    last_synced_sha: str,
    current_sha: str,
    config: dict,
) -> tuple[list[DataSourceItem], list[str]]:
    """
    Инкрементальная синхронизация.
    
    Returns:
        (items_to_upsert, item_ids_to_delete)
    """
    # Получаем изменения
    changes = get_changes(repo_path, last_synced_sha, current_sha)
    
    items_to_upsert = []
    item_ids_to_delete = []
    
    # Обрабатываем добавленные и измененные
    for path in changes.added + changes.modified:
        file_info = get_file_info(repo_path, ref, path)
        item = DataSourceItem(
            id=make_item_id(repo_path, ref, path),
            name=file_info.name,
            type="file",
            size=file_info.size,
            updated_at=file_info.last_commit_time,
            metadata={
                "path": path,
                "ref": ref,
                "commit_sha": current_sha,
            }
        )
        items_to_upsert.append(item)
    
    # Обрабатываем удаленные
    for path in changes.deleted:
        item_id = make_item_id(repo_path, ref, path)
        item_ids_to_delete.append(item_id)
    
    # Обрабатываем переименования как delete + add
    for old_path, new_path in changes.renamed:
        # Удаляем старый
        old_id = make_item_id(repo_path, ref, old_path)
        item_ids_to_delete.append(old_id)
        
        # Добавляем новый
        file_info = get_file_info(repo_path, ref, new_path)
        item = DataSourceItem(
            id=make_item_id(repo_path, ref, new_path),
            name=file_info.name,
            type="file",
            size=file_info.size,
            updated_at=file_info.last_commit_time,
            metadata={
                "path": new_path,
                "ref": ref,
                "commit_sha": current_sha,
            }
        )
        items_to_upsert.append(item)
    
    return items_to_upsert, item_ids_to_delete
```

## Хранение состояния

### Вариант 1: В metadata Dify (рекомендуется)

Если Dify поддерживает хранение state для datasource:

```python
def get_last_synced_sha(dify_state: dict) -> str | None:
    return dify_state.get("last_synced_sha")

def save_last_synced_sha(dify_state: dict, sha: str):
    dify_state["last_synced_sha"] = sha
```

### Вариант 2: В updated_at файлов

Используем `updated_at` = время последнего коммита файла.
Dify сам определит изменения по `updated_at`.

```python
def get_file_updated_at(repo, ref, path) -> datetime:
    """Время последнего коммита, затрагивающего файл."""
    commits = list(repo.iter_commits(ref, paths=path, max_count=1))
    if commits:
        return commits[0].committed_datetime
    return datetime.now()
```

### Вариант 3: Локальный файл

```python
import json
from pathlib import Path

STATE_FILE = Path(".git_datasource_state.json")

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def get_last_synced_sha(repo_id: str) -> str | None:
    state = load_state()
    return state.get(repo_id, {}).get("last_synced_sha")

def save_last_synced_sha(repo_id: str, sha: str):
    state = load_state()
    if repo_id not in state:
        state[repo_id] = {}
    state[repo_id]["last_synced_sha"] = sha
    save_state(state)
```

## Edge Cases

### 1. Force Push / History Rewrite

Если `last_synced_sha` больше не достижим из `current_sha`:

```python
def is_sha_reachable(repo, old_sha: str, new_sha: str) -> bool:
    """Проверка что old_sha достижим из new_sha."""
    try:
        # Пробуем получить merge-base
        repo.git.merge_base(old_sha, new_sha)
        return True
    except Exception:
        return False
```

Решение: выполнить full sync.

### 2. Слишком много изменений

Если между коммитами слишком много изменений, incremental sync может быть медленнее full sync.

```python
MAX_COMMITS_FOR_INCREMENTAL = 1000

def should_full_sync(repo, old_sha: str, new_sha: str) -> bool:
    commits = list(repo.iter_commits(
        f"{old_sha}..{new_sha}",
        max_count=MAX_COMMITS_FOR_INCREMENTAL + 1
    ))
    return len(commits) > MAX_COMMITS_FOR_INCREMENTAL
```

### 3. Смена ветки

Если пользователь сменил ветку в конфигурации:

```python
def detect_branch_change(config: dict, state: dict) -> bool:
    current_ref = config.get("ref", "main")
    last_ref = state.get("last_synced_ref")
    return current_ref != last_ref
```

Решение: выполнить full sync и сохранить новый ref.

### 4. Большие файлы

Пропускаем файлы больше лимита:

```python
MAX_FILE_SIZE = 1024 * 1024  # 1 MB

def should_skip_file(file_info) -> bool:
    return file_info.size > MAX_FILE_SIZE
```

## Оптимизации

### 1. Batch Processing

Обрабатываем файлы пачками:

```python
BATCH_SIZE = 100

def process_in_batches(items: list, batch_size: int = BATCH_SIZE):
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        yield batch
```

### 2. Parallel Content Fetching

Параллельное чтение содержимого файлов:

```python
from concurrent.futures import ThreadPoolExecutor

def fetch_contents_parallel(repo, ref: str, paths: list[str]) -> dict[str, str]:
    def fetch_one(path):
        return path, read_file(repo, ref, path)
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(fetch_one, paths)
    
    return dict(results)
```

### 3. Shallow Clone для больших репозиториев

```python
def clone_shallow(url: str, target: str, depth: int = 1):
    """Shallow clone — только последние N коммитов."""
    Repo.clone_from(url, target, depth=depth)
```

Ограничение: incremental sync не будет работать если `last_synced_sha` не в shallow history.

## Метрики и логирование

```python
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class SyncMetrics:
    started_at: datetime
    finished_at: datetime | None = None
    sync_type: str = "unknown"  # "full" or "incremental"
    files_added: int = 0
    files_updated: int = 0
    files_deleted: int = 0
    files_skipped: int = 0
    errors: int = 0

def log_sync_result(metrics: SyncMetrics):
    duration = (metrics.finished_at - metrics.started_at).total_seconds()
    logger.info(
        f"Sync completed: type={metrics.sync_type}, "
        f"added={metrics.files_added}, updated={metrics.files_updated}, "
        f"deleted={metrics.files_deleted}, skipped={metrics.files_skipped}, "
        f"errors={metrics.errors}, duration={duration:.2f}s"
    )
```
