# Git Data Source Plugin Validation Summary

> Верифицировано по: dify-plugin-sdks (December 2025)

## ✅ Feasibility: REALISTIC

Проект технически осуществим. SDK изучен, контракт понятен, все ключевые требования реализуемы.

## 📋 Key Findings

### 1. Dify Data Source Types

Dify поддерживает три типа datasource:
| Тип | Интерфейс | Методы | Подходит для Git |
|-----|-----------|--------|------------------|
| `online_document` | OnlineDocumentDatasource | `_get_pages()`, `_get_content()` | ❌ |
| `website_crawl` | WebsiteCrawlDatasource | `_get_website_crawl()` | ❌ |
| `online_drive` | **OnlineDriveDatasource** | `_browse_files()`, `_download_file()` | ✅ |

**Рекомендация:** Использовать `online_drive` — идеально подходит для файловой навигации.

### 2. Persistent Storage

✅ **Доступно:** Все datasource имеют доступ к `self.session.storage` — persistent key-value storage.

```python
self.session.storage.set(key: str, val: bytes) -> None
self.session.storage.get(key: str) -> bytes
self.session.storage.exist(key: str) -> bool
self.session.storage.delete(key: str) -> None
```

Используем для хранения `last_synced_sha`.

### 3. Инкрементальная синхронизация

✅ **Реализуема:** Хотя online_drive не имеет встроенного механизма sync, можно:
- Хранить `last_synced_sha` в session.storage
- При повторном browse возвращать только изменённые файлы
- Dify сам определит изменения по списку файлов

### 4. Обработка удалений

⚠️ **Частично автоматически:** 
- Dify не удаляет документы при исчезновении из списка
- Но online_drive контракт предполагает актуальный список
- Удалённые файлы просто не возвращаются в `_browse_files()`

### 5. Git Libraries

Доступны два основных варианта:
| Библиотека | Тип | Преимущества | Недостатки |
|------------|-----|--------------|------------|
| **GitPython** | Wrapper | Проще в использовании, быстрее | Требует git binary |
| **Dulwich** | Pure Python | Портативнее, не зависит от системы | Медленнее |

**Рекомендация:** Использовать GitPython для MVP, Dulwich как fallback.

## 🛠 Technical Requirements

### 1. Plugin Structure (VERIFIED)

```
git-datasource/
├── manifest.yaml                    # Метаданные плагина
├── main.py                          # Точка входа
├── requirements.txt                 # Зависимости
├── _assets/
│   └── icon.svg                     # Иконка
├── provider/
│   ├── git_datasource.yaml          # Конфигурация провайдера
│   └── git_datasource.py            # Валидация credentials
└── datasources/
    ├── git_datasource.yaml          # Конфигурация datasource
    └── git_datasource.py            # Реализация (online_drive)
```

### 2. OnlineDrive Interface (VERIFIED)

```python
class GitDataSource(OnlineDriveDatasource):
    def _browse_files(self, request: OnlineDriveBrowseFilesRequest) -> OnlineDriveBrowseFilesResponse:
        """Получение списка файлов/папок."""
    
    def _download_file(self, request: OnlineDriveDownloadFileRequest) -> Generator[DatasourceMessage, None, None]:
        """Скачивание содержимого файла."""
```

### 3. Credentials Support

✅ Поддерживаются все нужные типы:
- HTTPS public (no auth)
- HTTPS private with token (GitHub, GitLab, Gitea)
- SSH with key (deploy key)
- Local filesystem path

## 📈 Implementation Plan

### MVP-1: Базовый browse + download (3-5 дней)
1. Создать структуру плагина
2. Реализовать `_browse_files()` с GitPython
3. Реализовать `_download_file()`
4. Тестирование на публичном репозитории

### MVP-2: Аутентификация (2-3 дня)
1. HTTPS + token
2. SSH key
3. Local path
4. Валидация credentials

### MVP-3: Фильтрация и UX (2-3 дня)
1. Фильтрация по расширениям
2. Поддиректория
3. Пагинация

### MVP-4: Инкрементальная синхронизация (3-5 дней)
1. Хранение `last_synced_sha` в session.storage
2. Определение изменений через Git diff
3. Обработка удалений

**Итого: 2-3 недели**

## 🔧 Critical Components

### 1. Change Detection Strategy

```python
# Инкрементальная синхронизация
old_sha = get_last_synced_sha()
new_sha = get_head_sha()

if old_sha:
    # Только изменения
    changes = get_git_diff(old_sha, new_sha)
    files = filter_changed_files(changes)
else:
    # Все файлы
    files = list_all_files()
```

### 2. State Storage

```python
# Уникальный ключ для хранения SHA
def get_storage_key(repo_url: str, branch: str) -> str:
    import hashlib
    identity = f"{repo_url}:{branch}"
    return f"git_sync:{hashlib.sha256(identity.encode()).hexdigest()[:16]}"

# Использование
storage_key = get_storage_key(repo_url, branch)
if session.storage.exist(storage_key):
    last_sha = session.storage.get(storage_key).decode()
session.storage.set(storage_key, current_sha.encode())
```

### 3. File Identification

Для стабильного ID документа:
```python
# Формат: {repo_identity}::{ref}::{file_path}
file_id = f"{repo_hash}::{branch}::{file_path}"
```

## ⚠️ Limitations

1. **No Built-in Deletion API** — online_drive не имеет метода для явного удаления
2. **No Native Sync Mechanism** — нужно реализовывать самостоятельно через session.storage
3. **Rate Limits** — для больших репозиториев могут быть ограничения API

## ✅ Success Criteria

**Plugin считается успешным если:**
1. Может подключаться к любому Git репозиторию (HTTP/SSH/local)
2. Импортирует документы с сохранением структуры
3. Поддерживает инкрементальную синхронизацию
4. Обрабатывает удаления файлов
5. Работает в стандартной среде Dify
