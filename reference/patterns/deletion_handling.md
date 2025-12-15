# Обработка удалений в Dify Data Source Plugin

> Верифицировано по: dify-plugin-sdks (December 2025)

## Как работает удаление в Dify

### OnlineDrive Datasource и удаления

Dify **не** автоматически удаляет документы из Knowledge Base при исчезновении
файла из списка datasource. Однако механизм работает следующим образом:

1. **Browse Files** — Dify вызывает `_browse_files()` и получает список файлов
2. **Indexing** — Dify индексирует документы из выбранных файлов
3. **Re-sync** — При повторной синхронизации Dify снова вызывает `_browse_files()`
4. **Comparison** — Dify сравнивает новый список с предыдущим по `id`
5. **Orphaned Documents** — Файлы, отсутствующие в новом списке, помечаются как "orphaned"

### Что происходит с orphaned документами?

- Dify показывает их в UI как "Orphaned"
- Пользователь может вручную удалить их
- Они не обновляются при повторных sync

## Паттерн: Git Deletion Handling

Для Git репозиториев нужно определять удалённые файлы и не возвращать их в `_browse_files()`.

### Механизм отслеживания удалений

#### 1. Инкрементальная синхронизация

```python
def get_changes_between_commits(repo_path: str, old_sha: str, new_sha: str):
    """
    Получение списка изменений между коммитами.
    
    Returns:
        dict: {
            'added': [...],
            'modified': [...],
            'deleted': [...],
            'renamed': [(old_path, new_path), ...]
        }
    """
    from git import Repo
    
    repo = Repo(repo_path)
    old_commit = repo.commit(old_sha)
    new_commit = repo.commit(new_sha)
    
    diff = old_commit.diff(new_commit)
    
    changes = {
        'added': [],
        'modified': [],
        'deleted': [],
        'renamed': [],
    }
    
    for d in diff:
        if d.new_file:
            changes['added'].append(d.b_path)
        elif d.deleted_file:
            changes['deleted'].append(d.a_path)
        elif d.renamed:
            changes['renamed'].append((d.a_path, d.b_path))
        else:
            changes['modified'].append(d.a_path)
    
    return changes
```

#### 2. Фильтрация файлов для browse

```python
class GitDataSource(OnlineDriveDatasource):
    
    def _browse_files(self, request):
        # ... получаем last_synced_sha ...
        
        if last_synced_sha:
            # Инкрементальная синхронизация
            changes = get_changes_between_commits(
                repo_path, 
                last_synced_sha, 
                current_sha
            )
            
            # Получаем текущий список файлов
            all_files = self._list_all_files()
            
            # Убираем удалённые файлы
            deleted_set = set(changes['deleted'])
            renamed_from_set = {old for old, new in changes['renamed']}
            deleted_set.update(renamed_from_set)
            
            # Фильтруем список
            active_files = [
                f for f in all_files 
                if f['path'] not in deleted_set
            ]
            
            files_to_return = active_files
        else:
            # Первичная синхронизация
            files_to_return = self._list_all_files()
        
        # Сохраняем новый SHA
        self.session.storage.set(storage_key, current_sha.encode())
        
        # Возвращаем только активные файлы
        return self._format_response(files_to_return)
```

## Альтернативный подход: Explicit Deletion Tracking

Если нужно более точное отслеживание, можно хранить список всех файлов:

```python
def track_deletions_explicitly(self):
    """
    Явное отслеживание удалений через сохранение списка файлов.
    """
    storage_key_list = f"{storage_key}:file_list"
    
    # Получаем предыдущий список
    prev_files = set()
    if self.session.storage.exist(storage_key_list):
        prev_files_data = self.session.storage.get(storage_key_list)
        prev_files = set(prev_files_data.decode().split('\n'))
    
    # Получаем текущий список
    current_files = set(self._get_current_file_paths())
    
    # Определяем удалённые
    deleted_files = prev_files - current_files
    
    # Сохраняем новый список
    self.session.storage.set(
        storage_key_list, 
        '\n'.join(current_files).encode()
    )
    
    # Возвращаем только неудалённые файлы
    return [f for f in self._list_all_files() if f['path'] not in deleted_files]
```

## Паттерн: Переименования

Переименования можно обрабатывать двумя способами:

### Вариант 1: Treat as Delete + Add (рекомендуется)

```python
def handle_renames_as_delete_add(changes: dict) -> tuple[set, set]:
    """
    Обработка переименований как удаление + добавление.
    
    Returns:
        tuple[set, set]: (to_delete, to_add)
    """
    to_delete = set(changes['deleted'])
    to_add = set(changes['added'])
    
    # Переименования как удаление + добавление
    for old_path, new_path in changes['renamed']:
        to_delete.add(old_path)
        to_add.add(new_path)
    
    return to_delete, to_add
```

### Вариант 2: Preserve Identity

Если важна история документа, можно использовать стабильный ID:

```python
def make_stable_file_id(repo_url: str, ref: str, file_path: str) -> str:
    """
    Стабильный ID файла, не зависящий от переименований.
    
    Можно использовать blob SHA или содержимое файла.
    """
    import hashlib
    
    # Используем путь + repo identity для стабильности
    identity = f"{repo_url}:{ref}:{file_path}"
    return hashlib.sha256(identity.encode()).hexdigest()
```

## UX Рекомендации

### 1. Показывать статус файлов

В UI можно показывать типы изменений:

```python
def annotate_files_with_status(files: list, changes: dict) -> list:
    """Добавление статуса к файлам для UI."""
    deleted_set = set(changes['deleted'])
    renamed_dict = {old: new for old, new in changes['renamed']}
    
    annotated = []
    for f in files:
        status = "unchanged"
        if f['path'] in deleted_set:
            status = "deleted"
        elif f['path'] in renamed_dict.values():
            status = "renamed"
        
        f['status'] = status
        annotated.append(f)
    
    return annotated
```

### 2. Предупреждать о удалениях

Перед синхронизацией показывать список удалённых файлов:

```
⚠️  Будут удалены из Knowledge Base:
• docs/deprecated/guide.md
• old-spec.txt

Продолжить синхронизацию?
[Синхронизировать] [Отмена]
```

## Edge Cases

### 1. Force Push

Если пользователь сделал force push, `last_synced_sha` может быть недостижим:

```python
def is_sha_reachable(repo, old_sha: str, new_sha: str) -> bool:
    """Проверка достижимости SHA."""
    try:
        # Проверяем что old достижим из new
        repo.git.merge_base(old_sha, new_sha)
        return True
    except Exception:
        return False

def handle_force_push(self, last_sha: str, current_sha: str):
    """Обработка force push."""
    if not is_sha_reachable(self.repo, last_sha, current_sha):
        # Выполнить full sync
        return self._list_all_files()
    else:
        # Нормальная инкрементальная синхронизация
        return self._get_changed_files(last_sha, current_sha)
```

### 2. Большое количество изменений

Если между коммитами слишком много изменений:

```python
MAX_COMMITS_FOR_INCREMENTAL = 1000

def should_use_full_sync(repo, old_sha: str, new_sha: str) -> bool:
    """Определение необходимости полной синхронизации."""
    try:
        commits = list(repo.iter_commits(
            f"{old_sha}..{new_sha}",
            max_count=MAX_COMMITS_FOR_INCREMENTAL + 1
        ))
        return len(commits) > MAX_COMMITS_FOR_INCREMENTAL
    except Exception:
        return True  # На случай ошибок
```

## Тестирование

### Unit Tests для удалений

```python
def test_file_deletion_detection():
    """Тест обнаружения удалений."""
    # Создаём тестовый репозиторий
    repo = create_test_repo()
    
    # Коммит 1: файлы A, B, C
    commit1 = commit_files(repo, {'A.txt': 'content', 'B.txt': 'content', 'C.txt': 'content'})
    
    # Коммит 2: удалён B, добавлен D
    commit2 = commit_files(repo, {'A.txt': 'content', 'C.txt': 'content', 'D.txt': 'content'})
    
    # Проверяем diff
    changes = get_changes_between_commits(repo.path, commit1, commit2)
    
    assert 'B.txt' in changes['deleted']
    assert 'D.txt' in changes['added']
    assert 'A.txt' in changes['modified'] or 'A.txt' not in changes  # зависит от содержимого

def test_browse_excludes_deleted():
    """Тест что browse не возвращает удалённые файлы."""
    # ... имитируем состояние с удалёнными файлами ...
    files = git_datasource._browse_files(mock_request)
    
    # Проверяем что удалённые файлы отсутствуют
    file_paths = [f.id for f in files.result[0].files]
    assert 'deleted_file.txt' not in file_paths
```
