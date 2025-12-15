# Анализ реалистичности: Git Data Source Plugin для Dify

> Верифицировано по: dify-plugin-sdks (December 2024)

## Резюме

**Вердикт: ✅ РЕАЛИСТИЧНО**

Проект технически осуществим. SDK изучен, контракт понятен.

---

## Ключевое открытие: Три типа Data Source

Dify поддерживает **три разных типа** Data Source плагинов:

| Тип | Интерфейс | Методы | Пример |
|-----|-----------|--------|--------|
| `online_document` | `OnlineDocumentDatasource` | `_get_pages()`, `_get_content()` | Notion |
| `website_crawl` | `WebsiteCrawlDatasource` | `_get_website_crawl()` | Firecrawl |
| `online_drive` | `OnlineDriveDatasource` | `_browse_files()`, `_download_file()` | Google Cloud Storage |

### Рекомендация для Git: `online_drive`

**Почему `online_drive`:**
- Иерархическая навигация по файлам/папкам ✅
- Скачивание содержимого файлов ✅
- Пагинация встроена ✅
- Простой контракт (2 метода) ✅

**Почему НЕ `online_document`:**
- Предназначен для документов с workspace/page иерархией (Notion)
- Требует `workspace_id`, `page_id` — не подходит для Git

**Почему НЕ `website_crawl`:**
- Предназначен для краулинга веб-сайтов
- Асинхронный job-based подход — избыточен для Git

---

## Структура плагина (верифицировано)

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

---

## Контракт OnlineDriveDatasource

### _browse_files()

```python
def _browse_files(self, request: OnlineDriveBrowseFilesRequest) -> OnlineDriveBrowseFilesResponse:
    """
    Получение списка файлов/папок.
    
    request:
        - bucket: str | None (не используется для Git)
        - prefix: str | None (путь к директории)
        - max_keys: int (макс. файлов, default: 20)
        - next_page_parameters: dict | None (для пагинации)
    
    returns:
        OnlineDriveBrowseFilesResponse с:
        - result: list[OnlineDriveFileBucket]
            - files: list[OnlineDriveFile]
                - id: str (путь файла)
                - name: str (имя)
                - size: int (байты)
                - type: str ("folder" | "file")
            - is_truncated: bool
            - next_page_parameters: dict | None
    """
```

### _download_file()

```python
def _download_file(self, request: OnlineDriveDownloadFileRequest) -> Generator[DatasourceMessage, None, None]:
    """
    Скачивание содержимого файла.
    
    request:
        - bucket: str | None (не используется)
        - id: str (путь к файлу)
    
    yields:
        DatasourceMessage (blob с содержимым)
    """
    yield self.create_blob_message(content_bytes, meta={"file_name": ..., "mime_type": ...})
```

---

## Persistent Storage для инкрементального sync

**Ключевая находка:** Все datasource имеют доступ к `self.session.storage` — persistent key-value storage!

### API Storage

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

### Использование для Git sync

```python
class GitDataSource(OnlineDriveDatasource):
    
    def _get_storage_key(self) -> str:
        """Уникальный ключ для хранения SHA."""
        repo_url = self.runtime.credentials.get("repo_url")
        branch = self.runtime.credentials.get("branch", "main")
        # Хэшируем для уникальности
        import hashlib
        key = f"{repo_url}:{branch}"
        return f"git_sync:{hashlib.sha256(key.encode()).hexdigest()[:16]}"
    
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

### Источник верификации

- `vendor/dify-plugin-sdks/python/dify_plugin/invocations/storage.py`
- `vendor/dify-plugin-sdks/python/examples/google_calendar_trigger/` — пример использования

---

## Оценка по компонентам

### 1. Dify Plugin SDK ✅

| Аспект | Оценка | Комментарий |
|--------|--------|-------------|
| Документация | ⚠️ Средняя | Код SDK — лучший источник |
| Примеры | ✅ Отлично | Notion, Firecrawl, GCS — полные примеры |
| Контракт | ✅ Понятен | Изучен по коду SDK |

### 2. Git библиотеки ✅

| Библиотека | Рекомендация |
|------------|--------------|
| GitPython | ✅ Для MVP — проще |
| Dulwich | ✅ Для production — портативнее |

### 3. Инкрементальная синхронизация ⚠️

**Проблема:** `online_drive` не имеет встроенного механизма sync.

**Решение:** 
- Dify сам определяет изменения при повторном browse
- Для оптимизации можно кэшировать локально

---

## Что НЕ нужно реализовывать

1. ❌ `list_items()` / `get_item_content()` — это НЕ контракт Dify
2. ❌ `DataSourceItem` / `ListItemsResponse` — таких классов НЕТ в SDK
3. ❌ `updated_at` для change detection — Dify не использует это для online_drive

---

## План реализации (обновлённый)

### MVP-1: Базовый browse + download (3-5 дней)

1. Создать структуру плагина
2. Реализовать `_browse_files()` с GitPython
3. Реализовать `_download_file()`
4. Тестирование на публичном репозитории

### MVP-2: Аутентификация (2-3 дня)

1. HTTPS + token
2. Валидация credentials

### MVP-3: Фильтрация и UX (2-3 дня)

1. Фильтрация по расширениям
2. Поддиректория
3. Пагинация

### MVP-4: Кэширование (3-5 дней)

1. Локальный кэш репозитория
2. Инкрементальный fetch

**Итого: 2-3 недели**

---

## Ссылки на верифицированные источники

- SDK код: `vendor/dify-plugin-sdks/python/dify_plugin/`
- Интерфейсы: `vendor/dify-plugin-sdks/python/dify_plugin/interfaces/datasource/`
- Примеры: `vendor/dify-plugin-sdks/python/examples/`
  - `notion_datasource/` — online_document
  - `firecrawl_datasource/` — website_crawl
  - `google_cloud_storage/` — online_drive (наш референс!)
