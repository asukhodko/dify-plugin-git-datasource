# State Storage for Incremental Sync (VERIFIED)

> Верифицировано по: dify-plugin-sdks (December 2025)
> Решение: ✅ Option B — Plugin Persistent Storage

## Выбранный подход: self.session.storage

Dify SDK предоставляет persistent key-value storage для всех datasource плагинов.

### API
```python
# Сохранить значение
self.session.storage.set(key: str, val: bytes) -> None

# Получить значение
self.session.storage.get(key: str) -> bytes

# Проверить существование
self.session.storage.exist(key: str) -> bool

# Удалить
self.session.storage.delete(key: str) -> None
```

### Схема ключей для Git sync

```python
import hashlib

def get_storage_key(repo_url: str, branch: str) -> str:
    """Уникальный ключ для хранения SHA."""
    identity = f"{repo_url}:{branch}"
    key_hash = hashlib.sha256(identity.encode()).hexdigest()[:16]
    return f"git_sync:{key_hash}"
```

### Использование

```python
class GitDataSource(OnlineDriveDatasource):
    
    def _browse_files(self, request):
        storage_key = self._get_storage_key()
        
        # Получаем last_synced_sha
        last_sha = None
        if self.session.storage.exist(storage_key):
            last_sha = self.session.storage.get(storage_key).decode()
        
        # Получаем текущий HEAD
        current_sha = self._get_head_sha()
        
        if not last_sha:
            # First sync — все файлы
            files = self._list_all_files()
        else:
            # Incremental sync — только изменённые
            files = self._get_changed_files(last_sha, current_sha)
        
        # Сохраняем новый SHA
        self.session.storage.set(storage_key, current_sha.encode())
        
        return OnlineDriveBrowseFilesResponse(...)
```

## Альтернативы (отклонены)

### Option A: Dify-managed state/cursor
❌ **Не подходит** — online_drive контракт не имеет встроенного курсора.

### Option C: Encode state in item metadata
⚠️ **Ограниченно** — online_drive не использует `updated_at` для change detection.
Можно использовать как дополнительную информацию.

## Edge Cases

### Multi-instance concurrency
session.storage изолирован по session. При нескольких пользователях
каждый будет иметь своё состояние. Это OK для нашего use case.

### Force Push / History Rewrite
Если `last_synced_sha` недостижим → выполнить full sync.

### Branch Change
Ключ включает branch, поэтому смена ветки → новый ключ → full sync.

