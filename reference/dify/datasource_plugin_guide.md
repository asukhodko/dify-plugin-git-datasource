# Dify Data Source Plugin Guide

> Источник: dify-plugin-sdks (актуальный код SDK)
> Верифицировано: December 2025

## ВАЖНО: Три типа Data Source

Dify поддерживает **три разных типа** Data Source плагинов:

| Тип | Класс | Методы | Пример |
|-----|-------|--------|--------|
| `online_document` | `OnlineDocumentDatasource` | `_get_pages()`, `_get_content()` | Notion |
| `website_crawl` | `WebsiteCrawlDatasource` | `_get_website_crawl()` | Firecrawl |
| `online_drive` | `OnlineDriveDatasource` | `_browse_files()`, `_download_file()` | Google Cloud Storage |

**Для Git репозитория лучше всего подходит `online_drive`** — он предоставляет:
- Иерархическую навигацию по файлам/папкам
- Скачивание содержимого файлов
- Пагинацию

## Структура Data Source плагина

```
my-datasource/
├── manifest.yaml                    # Метаданные плагина
├── main.py                          # Точка входа
├── requirements.txt                 # Зависимости
├── _assets/
│   └── icon.svg                     # Иконка
├── provider/
│   ├── my_provider.yaml             # Конфигурация провайдера
│   └── my_provider.py               # Валидация credentials
└── datasources/
    ├── my_datasource.yaml           # Конфигурация datasource
    └── my_datasource.py             # Реализация datasource
```

## manifest.yaml

```yaml
version: 0.1.0
type: plugin
author: your-name
name: git_datasource
label:
  en_US: Git Repository
  ru_RU: Git Репозиторий
description:
  en_US: Import documents from Git repository
  ru_RU: Импорт документов из Git репозитория
icon: icon.svg
resource:
  memory: 268435456  # 256 MB
  permission: {}
plugins:
  datasources:
    - provider/git_datasource.yaml
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

## provider/git_datasource.yaml

```yaml
identity:
  author: your-name
  name: git_datasource
  label:
    en_US: Git Repository
    ru_RU: Git Репозиторий
  description:
    en_US: Import documents from Git repository
    ru_RU: Импорт документов из Git репозитория
  icon: icon.svg

# Тип провайдера — online_drive для файловой навигации
provider_type: online_drive

# Схема credentials (вводятся при настройке)
credentials_schema:
  - name: repo_url
    type: text-input
    required: true
    label:
      en_US: Repository URL
      ru_RU: URL репозитория
    placeholder:
      en_US: https://github.com/user/repo.git

  - name: branch
    type: text-input
    required: false
    label:
      en_US: Branch
      ru_RU: Ветка
    placeholder:
      en_US: main

  - name: access_token
    type: secret-input
    required: false
    label:
      en_US: Access Token
      ru_RU: Токен доступа
    placeholder:
      en_US: ghp_xxxx or glpat-xxxx
    help:
      en_US: Personal access token for private repositories
      ru_RU: Персональный токен для приватных репозиториев

# Список datasources
datasources:
  - datasources/git_datasource.yaml

extra:
  python:
    source: provider/git_datasource.py
```

## provider/git_datasource.py

```python
from collections.abc import Mapping
from typing import Any

from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from dify_plugin.interfaces.datasource import DatasourceProvider


class GitDatasourceProvider(DatasourceProvider):
    """
    Git Repository Data Source Provider.
    Валидация credentials при настройке.
    """

    def _validate_credentials(self, credentials: Mapping[str, Any]):
        """
        Проверка учетных данных.
        Вызывается при настройке источника данных.
        """
        repo_url = credentials.get("repo_url")
        if not repo_url:
            raise ToolProviderCredentialValidationError("Repository URL is required")
        
        # Проверяем доступ к репозиторию
        # TODO: Реализовать проверку подключения
        # try:
        #     git_client = GitClient(credentials)
        #     git_client.test_connection()
        # except Exception as e:
        #     raise ToolProviderCredentialValidationError(f"Cannot connect: {e}")
```

## datasources/git_datasource.yaml

```yaml
identity:
  name: git_datasource
  author: your-name
  label:
    en_US: Git Repository
    ru_RU: Git Репозиторий

description:
  en_US: Browse and import files from Git repository
  ru_RU: Просмотр и импорт файлов из Git репозитория

# Параметры (опционально)
parameters: []

# Схема вывода
output_schema:
  type: object
  properties:
    file:
      $ref: "https://dify.ai/schemas/v1/file.json"

extra:
  python:
    source: datasources/git_datasource.py
```

## datasources/git_datasource.py (online_drive тип)

```python
from collections.abc import Generator
from typing import Any

from dify_plugin.entities.datasource import (
    DatasourceMessage,
    OnlineDriveBrowseFilesRequest,
    OnlineDriveBrowseFilesResponse,
    OnlineDriveDownloadFileRequest,
    OnlineDriveFile,
    OnlineDriveFileBucket,
)
from dify_plugin.interfaces.datasource.online_drive import OnlineDriveDatasource


class GitDataSource(OnlineDriveDatasource):
    """
    Git Repository Data Source.
    
    Реализует интерфейс OnlineDriveDatasource для навигации
    по файлам репозитория и скачивания их содержимого.
    """

    def _browse_files(self, request: OnlineDriveBrowseFilesRequest) -> OnlineDriveBrowseFilesResponse:
        """
        Получение списка файлов/папок.
        
        Args:
            request: Запрос с параметрами:
                - bucket: None (не используется для Git)
                - prefix: путь к директории (например "docs/")
                - max_keys: максимум файлов на странице
                - next_page_parameters: параметры для следующей страницы
        
        Returns:
            OnlineDriveBrowseFilesResponse со списком файлов
        """
        repo_url = self.runtime.credentials.get("repo_url")
        branch = self.runtime.credentials.get("branch", "main")
        access_token = self.runtime.credentials.get("access_token")
        
        prefix = request.prefix or ""
        max_keys = request.max_keys or 100
        
        # TODO: Реализовать получение файлов из Git
        # git_client = GitClient(repo_url, branch, access_token)
        # files = git_client.list_files(prefix, max_keys)
        
        files = []  # Заглушка
        
        # Преобразуем в формат Dify
        drive_files = []
        for f in files:
            drive_files.append(OnlineDriveFile(
                id=f["path"],           # Путь как ID
                name=f["name"],         # Имя файла
                size=f["size"],         # Размер в байтах
                type="folder" if f["is_dir"] else "file",
            ))
        
        file_bucket = OnlineDriveFileBucket(
            bucket=None,                # Git не использует buckets
            files=drive_files,
            is_truncated=False,         # TODO: пагинация
            next_page_parameters=None,
        )
        
        return OnlineDriveBrowseFilesResponse(result=[file_bucket])

    def _download_file(self, request: OnlineDriveDownloadFileRequest) -> Generator[DatasourceMessage, None, None]:
        """
        Скачивание содержимого файла.
        
        Args:
            request: Запрос с параметрами:
                - bucket: None (не используется)
                - id: путь к файлу
        
        Yields:
            DatasourceMessage с содержимым файла
        """
        repo_url = self.runtime.credentials.get("repo_url")
        branch = self.runtime.credentials.get("branch", "main")
        access_token = self.runtime.credentials.get("access_token")
        file_path = request.id
        
        # TODO: Реализовать чтение файла из Git
        # git_client = GitClient(repo_url, branch, access_token)
        # content = git_client.read_file(file_path)
        
        content = b""  # Заглушка
        
        # Определяем MIME тип
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "text/plain"
        
        yield self.create_blob_message(
            content,
            meta={
                "file_name": file_path,
                "mime_type": mime_type,
            }
        )
```

## main.py

```python
from dify_plugin import Plugin, DifyPluginEnv

plugin = Plugin(DifyPluginEnv())

if __name__ == "__main__":
    plugin.run()
```

## Ключевые классы SDK

### DatasourceRuntime

```python
class DatasourceRuntime(BaseModel):
    credentials: Mapping[str, Any]  # Credentials из provider
    user_id: str | None
    session_id: str | None
```

Доступ в datasource: `self.runtime.credentials`

### Session и Storage

Все datasource имеют доступ к `self.session` с persistent storage:

```python
class GitDataSource(OnlineDriveDatasource):
    def _browse_files(self, request):
        # Persistent key-value storage
        self.session.storage.set("my_key", b"my_value")
        value = self.session.storage.get("my_key")  # -> bytes
        exists = self.session.storage.exist("my_key")  # -> bool
        self.session.storage.delete("my_key")
```

**Использование для Git sync:**
```python
# Сохранить last_synced_sha
self.session.storage.set("git:last_sha", current_sha.encode())

# Получить last_synced_sha
if self.session.storage.exist("git:last_sha"):
    last_sha = self.session.storage.get("git:last_sha").decode()
```

### OnlineDriveFile

```python
class OnlineDriveFile(BaseModel):
    id: str          # Уникальный ID (путь файла)
    name: str        # Отображаемое имя
    size: int        # Размер в байтах
    type: str        # "folder" или "file"
```

### OnlineDriveBrowseFilesRequest

```python
class OnlineDriveBrowseFilesRequest(BaseModel):
    bucket: str | None           # Bucket (None для Git)
    prefix: str | None           # Путь к директории
    max_keys: int = 20           # Макс. файлов на странице
    next_page_parameters: dict | None  # Для пагинации
```

### OnlineDriveBrowseFilesResponse

```python
class OnlineDriveBrowseFilesResponse(BaseModel):
    result: list[OnlineDriveFileBucket]
```

### OnlineDriveFileBucket

```python
class OnlineDriveFileBucket(BaseModel):
    bucket: str | None
    files: list[OnlineDriveFile]
    is_truncated: bool           # Есть ли ещё страницы
    next_page_parameters: dict | None
```

## Типы credentials полей

| Тип | Описание |
|-----|----------|
| `text-input` | Текстовое поле |
| `secret-input` | Скрытое поле (пароли, токены) |
| `select` | Выпадающий список |
| `boolean` | Чекбокс |
| `number` | Числовое поле |

## Ссылки

- SDK: https://github.com/langgenius/dify-plugin-sdks
- Примеры: `dify-plugin-sdks/python/examples/`
