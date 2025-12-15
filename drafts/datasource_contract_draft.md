# Data Source Plugin Contract (VERIFIED)

> Верифицировано по: dify-plugin-sdks (December 2025)
> Статус: ✅ CONFIRMED

## Тип datasource для Git: `online_drive`

Dify поддерживает три типа datasource:
| Тип | Интерфейс | Методы |
|-----|-----------|--------|
| `online_document` | OnlineDocumentDatasource | `_get_pages()`, `_get_content()` |
| `website_crawl` | WebsiteCrawlDatasource | `_get_website_crawl()` |
| `online_drive` | **OnlineDriveDatasource** | `_browse_files()`, `_download_file()` |

**Git → online_drive** — лучший fit для файловой навигации.

## Контракт OnlineDriveDatasource

### Метод 1: _browse_files()
```python
def _browse_files(self, request: OnlineDriveBrowseFilesRequest) -> OnlineDriveBrowseFilesResponse:
    """
    Request:
        - bucket: str | None (не используется для Git)
        - prefix: str | None (путь к директории)
        - max_keys: int = 20 (макс. файлов)
        - next_page_parameters: dict | None (пагинация)
    
    Response:
        OnlineDriveBrowseFilesResponse с:
        - result: list[OnlineDriveFileBucket]
            - files: list[OnlineDriveFile]
                - id: str (путь файла — СТАБИЛЬНЫЙ ID)
                - name: str (имя для отображения)
                - size: int (байты)
                - type: str ("folder" | "file")
            - is_truncated: bool
            - next_page_parameters: dict | None
    """
```

### Метод 2: _download_file()
```python
def _download_file(self, request: OnlineDriveDownloadFileRequest) -> Generator[DatasourceMessage, None, None]:
    """
    Request:
        - bucket: str | None (не используется)
        - id: str (путь к файлу — тот же что в _browse_files)
    
    Yields:
        DatasourceMessage (blob с содержимым)
    """
    yield self.create_blob_message(content_bytes, meta={"file_name": ..., "mime_type": ...})
```

## Ответы на вопросы

### Q: Are "list" + "get" separate calls?
**A: ДА.** `_browse_files()` для списка, `_download_file()` для содержимого.

### Q: How does Dify request pagination?
**A:** Через `next_page_parameters` dict. Плагин возвращает `is_truncated=True` и
`next_page_parameters` с данными для следующей страницы. Dify передаёт их обратно.

### Q: How does Dify decide that an item changed?
**A:** Dify **не** использует `updated_at` для online_drive. Dify сравнивает
список файлов по `id`. Изменения определяются при повторном browse.

### Q: Is deletion handled by "missing from list" semantics?
**A:** ⚠️ **ЧАСТИЧНО.** Dify не автоматически удаляет документы при исчезновении из списка.
Но online_drive контракт предполагает что плагин возвращает актуальный список файлов.
Для корректной работы с удалениями нужно:
1. Возвращать только существующие файлы
2. Dify сам определит что файлы отсутствуют при следующем импорте

## Persistent Storage (для SHA tracking)

Все datasource имеют доступ к `self.session.storage`:
```python
self.session.storage.set(key: str, val: bytes) -> None
self.session.storage.get(key: str) -> bytes
self.session.storage.exist(key: str) -> bool
self.session.storage.delete(key: str) -> None
```

Используем для хранения `last_synced_sha`.
