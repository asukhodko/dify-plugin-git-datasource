"""
datasources/git_datasource.py

Реализация Git Data Source (online_drive тип) с инкрементальным sync.
Верифицировано по: dify-plugin-sdks (December 2024)
"""

import hashlib
import mimetypes
import os
from collections.abc import Generator

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
    
    Реализует интерфейс OnlineDriveDatasource для:
    - Навигации по файлам/папкам репозитория
    - Скачивания содержимого файлов
    - Инкрементального sync через session.storage
    
    Сценарий работы:
    1. Initial sync: загрузить все файлы, сохранить SHA
    2. Incremental sync: загрузить только изменённые файлы с последнего SHA
    """

    def _get_storage_key(self) -> str:
        """
        Уникальный ключ для хранения last_synced_sha.
        
        Формат: git_sync:{hash(repo_url:branch)}
        """
        repo_url = self.runtime.credentials.get("repo_url", "")
        branch = self.runtime.credentials.get("branch", "main")
        key = f"{repo_url}:{branch}"
        return f"git_sync:{hashlib.sha256(key.encode()).hexdigest()[:16]}"

    def _browse_files(self, request: OnlineDriveBrowseFilesRequest) -> OnlineDriveBrowseFilesResponse:
        """
        Получение списка файлов/папок.
        
        Логика инкрементального sync:
        1. Получить last_synced_sha из storage
        2. Получить текущий HEAD SHA
        3. Если first sync — вернуть все файлы
        4. Иначе — вернуть только изменённые файлы
        5. Сохранить новый SHA в storage
        """
        # Получаем credentials
        repo_url = self.runtime.credentials.get("repo_url")
        branch = self.runtime.credentials.get("branch", "main")
        access_token = self.runtime.credentials.get("access_token")
        subdir = self.runtime.credentials.get("subdir", "")
        extensions = self._parse_extensions(self.runtime.credentials.get("extensions", ""))
        
        # Параметры запроса
        prefix = request.prefix or ""
        max_keys = request.max_keys or 100
        
        # Получаем last_synced_sha из persistent storage
        storage_key = self._get_storage_key()
        last_synced_sha = None
        if self.session.storage.exist(storage_key):
            last_synced_sha = self.session.storage.get(storage_key).decode()
        
        # TODO: Реализовать Git операции
        # git_client = GitClient(repo_url, branch, access_token)
        # git_client.ensure_cloned()
        # current_sha = git_client.get_head_sha()
        
        current_sha = "HEAD"  # Заглушка
        
        # Определяем какие файлы возвращать
        if not last_synced_sha:
            # First sync — все файлы
            # files = git_client.list_all_files(subdir, extensions)
            files = []  # Заглушка
        else:
            # Incremental sync — только изменённые
            # files = git_client.get_changed_files(last_synced_sha, current_sha, subdir, extensions)
            files = []  # Заглушка
        
        # Сохраняем новый SHA
        self.session.storage.set(storage_key, current_sha.encode())
        
        # Преобразуем в формат Dify
        drive_files = []
        for entry in files:
            # Фильтрация по расширениям (только для файлов)
            if entry.get("type") == "file" and extensions:
                if not any(entry["name"].lower().endswith(ext) for ext in extensions):
                    continue
            
            drive_files.append(OnlineDriveFile(
                id=entry["path"],
                name=entry["name"],
                size=entry.get("size", 0),
                type=entry.get("type", "file"),
            ))
        
        # Сортируем: папки первыми
        drive_files.sort(key=lambda x: (0 if x.type == "folder" else 1, x.name.lower()))
        
        # Пагинация
        is_truncated = len(drive_files) > max_keys
        if is_truncated:
            drive_files = drive_files[:max_keys]
        
        file_bucket = OnlineDriveFileBucket(
            bucket=None,
            files=drive_files,
            is_truncated=is_truncated,
            next_page_parameters=None,
        )
        
        return OnlineDriveBrowseFilesResponse(result=[file_bucket])

    def _download_file(self, request: OnlineDriveDownloadFileRequest) -> Generator[DatasourceMessage, None, None]:
        """
        Скачивание содержимого файла.
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
        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "text/plain"
        
        yield self.create_blob_message(
            content,
            meta={
                "file_name": os.path.basename(file_path),
                "mime_type": mime_type,
            }
        )

    def _parse_extensions(self, extensions_str: str) -> list[str]:
        """Парсинг строки расширений в список."""
        if not extensions_str:
            return []
        
        extensions = []
        for ext in extensions_str.split(","):
            ext = ext.strip().lower()
            if ext:
                if not ext.startswith("."):
                    ext = "." + ext
                extensions.append(ext)
        
        return extensions
