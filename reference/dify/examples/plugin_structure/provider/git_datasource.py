"""
provider/git_datasource.py

Провайдер Git Data Source — валидация credentials.
Верифицировано по: dify-plugin-sdks/python/examples/notion_datasource/provider/notion_datasource.py
"""

from collections.abc import Mapping
from typing import Any

from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from dify_plugin.interfaces.datasource import DatasourceProvider


class GitDatasourceProvider(DatasourceProvider):
    """
    Git Repository Data Source Provider.
    
    Отвечает за валидацию credentials при настройке источника данных.
    """

    def _validate_credentials(self, credentials: Mapping[str, Any]):
        """
        Проверка учетных данных.
        
        Вызывается Dify при настройке источника данных.
        Должен выбросить ToolProviderCredentialValidationError если credentials невалидны.
        
        Args:
            credentials: Словарь с учетными данными из YAML конфигурации
                - repo_url: URL репозитория
                - branch: ветка (опционально)
                - access_token: токен доступа (опционально)
                - subdir: поддиректория (опционально)
                - extensions: расширения файлов (опционально)
        """
        repo_url = credentials.get("repo_url")
        if not repo_url:
            raise ToolProviderCredentialValidationError("Repository URL is required")
        
        # Валидация формата URL
        if not (repo_url.startswith("https://") or repo_url.startswith("http://") or 
                repo_url.startswith("git@") or repo_url.startswith("ssh://") or
                repo_url.startswith("/") or repo_url.startswith("file://")):
            raise ToolProviderCredentialValidationError(
                "Repository URL must start with https://, http://, git@, ssh://, /, or file://"
            )
        
        # Проверяем доступ к репозиторию
        access_token = credentials.get("access_token")
        branch = credentials.get("branch", "main")
        
        try:
            self._test_connection(repo_url, access_token, branch)
        except Exception as e:
            raise ToolProviderCredentialValidationError(
                f"Cannot connect to repository: {e}"
            ) from e

    def _test_connection(self, repo_url: str, access_token: str | None, branch: str):
        """
        Проверка подключения к репозиторию.
        
        Выполняет ls-remote для проверки доступа.
        """
        import subprocess
        import os
        
        # Определяем тип репозитория
        if repo_url.startswith("/") or repo_url.startswith("file://"):
            # Локальный репозиторий
            path = repo_url.replace("file://", "")
            if not os.path.exists(path):
                raise Exception(f"Local repository not found: {path}")
            # Простая проверка что это Git репозиторий
            if not (os.path.exists(os.path.join(path, ".git")) or 
                   os.path.exists(os.path.join(path, "HEAD"))):
                raise Exception(f"Not a Git repository: {path}")
            return  # Локальный репозиторий проверен
        
        # Формируем URL с токеном если есть
        if access_token and repo_url.startswith("https://"):
            # https://github.com/... -> https://token:xxx@github.com/...
            auth_url = repo_url.replace("https://", f"https://token:{access_token}@")
        else:
            auth_url = repo_url
        
        try:
            # Используем git ls-remote для проверки доступа
            result = subprocess.run(
                ["git", "ls-remote", "--heads", auth_url, branch],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                # Маскируем токен в сообщении об ошибке
                if access_token:
                    error_msg = error_msg.replace(access_token, "***")
                raise Exception(error_msg or "Unknown error")
                
        except subprocess.TimeoutExpired:
            raise Exception("Connection timeout")
        except FileNotFoundError:
            raise Exception("Git is not installed")
