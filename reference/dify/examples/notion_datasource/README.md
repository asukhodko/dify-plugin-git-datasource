# Notion Data Source — Анализ референсной реализации

> Источник: `vendor/dify-plugin-sdks/python/examples/notion_datasource/`

## Тип плагина

Notion использует тип `online_document` — для документов с workspace/page иерархией.

**Для Git репозитория этот тип НЕ подходит!** Используйте `online_drive` (см. Google Cloud Storage пример).

## Структура Notion плагина

```
notion_datasource/
├── manifest.yaml
├── main.py
├── requirements.txt
├── _assets/
│   └── icon.svg
├── provider/
│   ├── notion_datasource.yaml      # credentials + provider_type
│   └── notion_datasource.py        # валидация + OAuth
└── datasources/
    ├── notion_datasource.yaml      # параметры datasource
    ├── notion_datasource.py        # реализация
    └── utils/
        ├── notion_client.py
        └── notion_extractor.py
```

## Ключевые отличия online_document от online_drive

| Аспект | online_document (Notion) | online_drive (GCS, Git) |
|--------|--------------------------|-------------------------|
| Иерархия | workspace → pages | bucket → folders → files |
| Методы | `_get_pages()`, `_get_content()` | `_browse_files()`, `_download_file()` |
| ID элемента | page_id | file path |
| Контент | Текст страницы | Бинарный blob |

## Что полезного взять из Notion

1. **Структура provider/** — валидация credentials
2. **OAuth flow** — если нужна OAuth авторизация
3. **Паттерн utils/** — вынос логики в отдельные модули

## Что НЕ копировать

1. ❌ `OnlineDocumentDatasource` — не подходит для Git
2. ❌ `_get_pages()` / `_get_content()` — другой контракт
3. ❌ `OnlineDocumentInfo`, `OnlineDocumentPage` — другие entities

## Рекомендация

Для Git Data Source используйте как референс:
- **Google Cloud Storage** (`vendor/dify-plugin-sdks/python/examples/google_cloud_storage/`)
- Тип: `online_drive`
- Методы: `_browse_files()`, `_download_file()`
