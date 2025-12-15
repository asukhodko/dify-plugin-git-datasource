# Dify Plugin SDK Overview

> Верифицировано по: dify-plugin-sdks (December 2024)

## Типы плагинов

Dify поддерживает несколько типов плагинов:

| Тип | Описание |
|-----|----------|
| Tool | Инструменты для агентов |
| Model | Провайдеры моделей |
| Endpoint | HTTP endpoints |
| Agent Strategy | Стратегии агентов |
| Trigger | Триггеры событий |
| **Datasource** | Источники данных для Knowledge Base |

## Data Source — три подтипа

```python
class DatasourceProviderType(StrEnum):
    ONLINE_DOCUMENT = "online_document"  # Notion-like
    WEBSITE_CRAWL = "website_crawl"      # Firecrawl-like
    ONLINE_DRIVE = "online_drive"        # GCS-like, Git
```

## Структура плагина

```
my-plugin/
├── manifest.yaml          # Метаданные плагина
├── main.py                # Точка входа
├── requirements.txt       # Зависимости
├── _assets/
│   └── icon.svg           # Иконка
├── provider/
│   ├── my_provider.yaml   # Конфигурация провайдера
│   └── my_provider.py     # Валидация credentials
└── datasources/           # Для datasource плагинов
    ├── my_datasource.yaml
    └── my_datasource.py
```

## manifest.yaml

```yaml
version: 0.1.0
type: plugin
author: your-name
name: my_plugin
label:
  en_US: My Plugin
description:
  en_US: Plugin description
icon: icon.svg

resource:
  memory: 268435456  # 256 MB
  permission: {}

plugins:
  datasources:
    - provider/my_provider.yaml

meta:
  version: 0.0.1
  arch:
    - amd64
    - arm64
  runner:
    language: python
    version: "3.12"
    entrypoint: main
  minimum_dify_version: 1.9.0

tags:
  - rag
```

## main.py

```python
from dify_plugin import Plugin, DifyPluginEnv

plugin = Plugin(DifyPluginEnv())

if __name__ == "__main__":
    plugin.run()
```

## Credentials

Типы полей credentials:

| Тип | Описание |
|-----|----------|
| `text-input` | Текстовое поле |
| `secret-input` | Скрытое поле (токены, пароли) |
| `select` | Выпадающий список |
| `boolean` | Чекбокс |
| `number` | Числовое поле |

Пример в YAML:

```yaml
credentials_schema:
  - name: api_key
    type: secret-input
    required: true
    label:
      en_US: API Key
    placeholder:
      en_US: Enter your API key
    help:
      en_US: Get your key from settings
```

## DatasourceRuntime

Доступен в datasource через `self.runtime`:

```python
class DatasourceRuntime(BaseModel):
    credentials: Mapping[str, Any]  # Credentials из provider
    user_id: str | None
    session_id: str | None
```

Использование:

```python
class MyDataSource(OnlineDriveDatasource):
    def _browse_files(self, request):
        api_key = self.runtime.credentials.get("api_key")
        # ...
```

## Ссылки

- SDK: https://github.com/langgenius/dify-plugin-sdks
- Примеры: `dify-plugin-sdks/python/examples/`
