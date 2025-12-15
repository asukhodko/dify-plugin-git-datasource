# Reference Documentation

> **Верифицировано по:** dify-plugin-sdks (December 2024)

Собранная документация и примеры кода для реализации dify-plugin-git-datasource.

**Начните с:** [FEASIBILITY_ANALYSIS.md](./FEASIBILITY_ANALYSIS.md) — оценка реалистичности и план действий.

## Ключевое открытие

Dify поддерживает **три типа** Data Source плагинов:

| Тип | Для чего | Пример |
|-----|----------|--------|
| `online_document` | Документы с иерархией | Notion |
| `website_crawl` | Краулинг веб-сайтов | Firecrawl |
| `online_drive` | Файловые хранилища | Google Cloud Storage |

**Для Git репозитория используем `online_drive`** — он предоставляет навигацию по файлам и скачивание содержимого.

## Структура

```
reference/
├── FEASIBILITY_ANALYSIS.md         # ⭐ Анализ реалистичности (ВЕРИФИЦИРОВАНО)
├── dify/
│   ├── datasource_plugin_guide.md  # Гайд по Data Source (ВЕРИФИЦИРОВАНО)
│   ├── plugin_sdk_overview.md      # Обзор Dify Plugin SDK
│   ├── plugin_manifest_schema.md   # Схема manifest.yaml
│   └── examples/
│       ├── notion_datasource/      # Разбор Notion плагина
│       └── plugin_structure/       # ⭐ Готовый скелет Git плагина (ВЕРИФИЦИРОВАНО)
│           ├── manifest.yaml
│           ├── main.py
│           ├── requirements.txt
│           ├── provider/
│           │   ├── git_datasource.yaml
│           │   └── git_datasource.py
│           └── datasources/
│               ├── git_datasource.yaml
│               └── git_datasource.py
├── git/
│   ├── dulwich_guide.md            # Работа с Dulwich
│   ├── gitpython_guide.md          # Работа с GitPython
│   └── examples/
│       ├── clone_fetch.py
│       ├── diff_changes.py
│       └── tree_traversal.py
└── patterns/
    ├── incremental_sync.md
    └── credential_handling.md
```

## Оценка реалистичности

**Вердикт: ✅ РЕАЛИСТИЧНО** — проект осуществим за 2-3 недели.

### ✅ Верифицировано

1. **Контракт Data Source** — изучен по коду SDK
2. **Тип плагина** — `online_drive` (как Google Cloud Storage)
3. **Методы** — `_browse_files()`, `_download_file()`
4. **Структура** — provider/ + datasources/

### 📋 Порядок изучения

1. `FEASIBILITY_ANALYSIS.md` — общая картина
2. `dify/datasource_plugin_guide.md` — контракт online_drive
3. `dify/examples/plugin_structure/` — готовый скелет
4. `git/gitpython_guide.md` — Git библиотека

## Источники верификации

Документация верифицирована по коду:
- `vendor/dify-plugin-sdks/python/dify_plugin/interfaces/datasource/online_drive.py`
- `vendor/dify-plugin-sdks/python/examples/google_cloud_storage/`
- `vendor/dify-plugin-sdks/python/examples/notion_datasource/`
