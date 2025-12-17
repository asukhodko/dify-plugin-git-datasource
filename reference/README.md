# Reference Documentation

> **Статус:** Справочные материалы, использованные при разработке. Реализация завершена в `plugin/`.

## Структура

```
reference/
├── FEASIBILITY_ANALYSIS.md         # Анализ реалистичности (✅ подтверждено)
├── dify/
│   ├── datasource_plugin_guide.md  # Гайд по Data Source плагинам
│   ├── plugin_sdk_overview.md      # Обзор Dify Plugin SDK
│   ├── plugin_manifest_schema.md   # Схема manifest.yaml
│   └── examples/
│       ├── notion_datasource/      # Разбор Notion плагина
│       └── plugin_structure/       # Скелет Git плагина (использован как основа)
├── git/
│   ├── dulwich_guide.md            # Работа с Dulwich
│   ├── gitpython_guide.md          # Работа с GitPython (✅ выбран для MVP)
│   └── examples/                   # Примеры Git операций
└── patterns/
    ├── incremental_sync.md         # Паттерн инкрементальной синхронизации
    ├── credential_handling.md      # Обработка credentials
    ├── deletion_handling.md        # Обработка удалений
    └── local_repository.md         # Работа с локальными репозиториями
```

## Ключевые решения

| Вопрос | Решение |
|--------|---------|
| Тип плагина | `online_drive` (как Google Cloud Storage) |
| Git библиотека | GitPython (проще API, требует git binary) |
| Хранение состояния | `session.storage` с SHA коммита |
| Аутентификация | HTTPS+Token, SSH key, Local path |

## Связанные материалы

- **Реализация:** [../plugin/](../plugin/) — готовый код плагина
- **Спецификация:** [../.kiro/specs/git-datasource-plugin/](../.kiro/specs/git-datasource-plugin/)
- **Документация идеи:** [../docs/](../docs/)
