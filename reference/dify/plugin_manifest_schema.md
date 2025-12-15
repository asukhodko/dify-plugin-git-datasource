# Dify Plugin Manifest Schema

> Верифицировано по: dify-plugin-sdks/python/examples/*/manifest.yaml

## manifest.yaml — полная схема

```yaml
# Версия плагина
version: 0.1.0

# Тип — всегда "plugin" для datasource
type: plugin

# Автор
author: your-name

# Уникальное имя (snake_case)
name: my_datasource

# Отображаемое имя (локализация)
label:
  en_US: My Datasource
  zh_Hans: 我的数据源
  ru_RU: Мой источник данных

# Описание
description:
  en_US: Description of the datasource
  zh_Hans: 数据源描述
  ru_RU: Описание источника данных

# Иконка (относительный путь)
icon: icon.svg

# Ресурсы
resource:
  memory: 268435456  # Байты (256 MB)
  permission:
    model:
      enabled: false
    # Другие permissions...

# Список провайдеров
plugins:
  datasources:
    - provider/my_provider.yaml

# Метаданные
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

# Теги для поиска
tags:
  - rag
  - datasource
```

## provider/*.yaml — схема провайдера

```yaml
# Идентификация
identity:
  author: your-name
  name: my_datasource
  label:
    en_US: My Datasource
  description:
    en_US: Description
  icon: icon.svg

# Тип провайдера (ВАЖНО!)
provider_type: online_drive  # или online_document, website_crawl

# Схема credentials
credentials_schema:
  - name: api_key
    type: secret-input
    required: true
    label:
      en_US: API Key
    placeholder:
      en_US: Enter key
    help:
      en_US: Help text
    url: https://example.com/get-key  # Ссылка на получение

# OAuth (опционально)
oauth_schema:
  client_schema:
    - name: client_id
      type: secret-input
      label:
        en_US: Client ID
  credentials_schema:
    - name: access_token
      type: secret-input
      label:
        en_US: Access Token

# Список datasources
datasources:
  - datasources/my_datasource.yaml

# Путь к Python коду
extra:
  python:
    source: provider/my_provider.py
```

## datasources/*.yaml — схема datasource

```yaml
# Идентификация
identity:
  name: my_datasource
  author: your-name
  label:
    en_US: My Datasource

# Описание
description:
  en_US: Description of what this datasource does

# Параметры (опционально)
parameters:
  - name: param1
    type: string
    required: false
    label:
      en_US: Parameter 1
    description:
      en_US: Description

# Схема вывода
output_schema:
  type: object
  properties:
    file:
      $ref: "https://dify.ai/schemas/v1/file.json"

# Путь к Python коду
extra:
  python:
    source: datasources/my_datasource.py
```

## Типы полей credentials

| Тип | Описание | Пример |
|-----|----------|--------|
| `text-input` | Текстовое поле | URL, путь |
| `secret-input` | Скрытое поле | Токен, пароль, ключ |
| `select` | Выпадающий список | Выбор региона |
| `boolean` | Чекбокс | Вкл/выкл опции |
| `number` | Числовое поле | Лимиты |

## Пример select

```yaml
credentials_schema:
  - name: region
    type: select
    required: true
    default: us-east-1
    label:
      en_US: Region
    options:
      - value: us-east-1
        label:
          en_US: US East
      - value: eu-west-1
        label:
          en_US: EU West
```

## Локализация

Поддерживаемые локали:
- `en_US` — English (обязательно)
- `zh_Hans` — Simplified Chinese
- `zh_Hant` — Traditional Chinese
- `ja_JP` — Japanese
- `ru_RU` — Russian
- `pt_BR` — Portuguese (Brazil)

## Ссылки

- Примеры: `dify-plugin-sdks/python/examples/*/manifest.yaml`
