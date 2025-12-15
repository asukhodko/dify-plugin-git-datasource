"""
Примеры клонирования и обновления Git репозиториев.

Поддержка:
- HTTPS public
- HTTPS с токеном
- SSH с ключом
- Локальный путь
"""

import os
import tempfile
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class AuthType(Enum):
    NONE = "none"
    TOKEN = "token"
    BASIC = "basic"
    SSH = "ssh"


@dataclass
class GitCredentials:
    """Учетные данные для Git."""
    repo_url: str
    auth_type: AuthType = AuthType.NONE
    access_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_private_key: Optional[str] = None
    ssh_passphrase: Optional[str] = None


# =============================================================================
# GitPython Implementation
# =============================================================================

def clone_with_gitpython(
    credentials: GitCredentials,
    target_path: str,
    ref: str = "main",
    bare: bool = True,
    depth: Optional[int] = None,
) -> "git.Repo":
    """
    Клонирование репозитория с помощью GitPython.
    
    Args:
        credentials: Учетные данные
        target_path: Путь для клонирования
        ref: Ветка/тег для checkout
        bare: Bare clone (без working tree)
        depth: Shallow clone depth (None = full)
    
    Returns:
        git.Repo: Клонированный репозиторий
    """
    from git import Repo
    
    url = _prepare_url_gitpython(credentials)
    env = _prepare_env_gitpython(credentials)
    
    # Сохраняем текущее окружение
    old_env = os.environ.copy()
    
    try:
        # Устанавливаем SSH команду если нужно
        if env:
            os.environ.update(env)
        
        kwargs = {
            "url": url,
            "to_path": target_path,
            "bare": bare,
        }
        
        if depth:
            kwargs["depth"] = depth
        
        repo = Repo.clone_from(**kwargs)
        
        # Checkout нужной ветки (для non-bare)
        if not bare and ref:
            repo.git.checkout(ref)
        
        return repo
        
    finally:
        # Восстанавливаем окружение
        os.environ.clear()
        os.environ.update(old_env)


def fetch_with_gitpython(
    repo_path: str,
    credentials: GitCredentials,
) -> str:
    """
    Обновление репозитория (fetch).
    
    Returns:
        str: SHA нового HEAD
    """
    from git import Repo
    
    repo = Repo(repo_path)
    env = _prepare_env_gitpython(credentials)
    
    old_env = os.environ.copy()
    
    try:
        if env:
            os.environ.update(env)
        
        # Fetch из origin
        origin = repo.remotes.origin
        origin.fetch()
        
        return repo.head.commit.hexsha
        
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def _prepare_url_gitpython(credentials: GitCredentials) -> str:
    """Подготовка URL с встроенными credentials для HTTPS."""
    url = credentials.repo_url
    
    if credentials.auth_type == AuthType.TOKEN:
        # Встраиваем токен в URL
        # https://github.com/... -> https://token:xxx@github.com/...
        if url.startswith("https://"):
            url = url.replace(
                "https://",
                f"https://token:{credentials.access_token}@"
            )
    elif credentials.auth_type == AuthType.BASIC:
        if url.startswith("https://"):
            url = url.replace(
                "https://",
                f"https://{credentials.username}:{credentials.password}@"
            )
    
    return url


def _prepare_env_gitpython(credentials: GitCredentials) -> dict:
    """Подготовка environment variables для SSH."""
    env = {}
    
    if credentials.auth_type == AuthType.SSH and credentials.ssh_private_key:
        # Создаем временный файл с ключом
        key_file = _write_temp_key(credentials.ssh_private_key)
        env["GIT_SSH_COMMAND"] = f"ssh -i {key_file} -o StrictHostKeyChecking=no"
    
    return env


# =============================================================================
# Dulwich Implementation
# =============================================================================

def clone_with_dulwich(
    credentials: GitCredentials,
    target_path: str,
    ref: str = "main",
    bare: bool = True,
) -> "dulwich.repo.Repo":
    """
    Клонирование репозитория с помощью Dulwich.
    
    Args:
        credentials: Учетные данные
        target_path: Путь для клонирования
        ref: Ветка/тег
        bare: Bare clone
    
    Returns:
        dulwich.repo.Repo: Клонированный репозиторий
    """
    from dulwich import porcelain
    
    kwargs = {
        "source": credentials.repo_url,
        "target": target_path,
        "bare": bare,
    }
    
    # Добавляем credentials
    if credentials.auth_type == AuthType.TOKEN:
        kwargs["username"] = "token"
        kwargs["password"] = credentials.access_token
    elif credentials.auth_type == AuthType.BASIC:
        kwargs["username"] = credentials.username
        kwargs["password"] = credentials.password
    elif credentials.auth_type == AuthType.SSH:
        # Для SSH нужен кастомный vendor
        # См. dulwich_guide.md для деталей
        pass
    
    repo = porcelain.clone(**kwargs)
    return repo


def fetch_with_dulwich(
    repo_path: str,
    credentials: GitCredentials,
) -> str:
    """
    Обновление репозитория (fetch) с помощью Dulwich.
    
    Returns:
        str: SHA нового HEAD
    """
    from dulwich import porcelain
    from dulwich.repo import Repo
    
    repo = Repo(repo_path)
    
    kwargs = {}
    if credentials.auth_type == AuthType.TOKEN:
        kwargs["username"] = "token"
        kwargs["password"] = credentials.access_token
    elif credentials.auth_type == AuthType.BASIC:
        kwargs["username"] = credentials.username
        kwargs["password"] = credentials.password
    
    porcelain.fetch(repo, **kwargs)
    
    return repo.head().decode()


# =============================================================================
# Utility Functions
# =============================================================================

def _write_temp_key(private_key: str) -> str:
    """
    Записывает SSH ключ во временный файл.
    
    Returns:
        str: Путь к файлу
    """
    fd, path = tempfile.mkstemp(suffix=".key")
    try:
        os.write(fd, private_key.encode())
    finally:
        os.close(fd)
    
    os.chmod(path, 0o600)
    return path


def get_cache_path(credentials: GitCredentials, cache_dir: str = ".git_cache") -> str:
    """
    Генерация пути для кэша репозитория.
    
    Формат: {cache_dir}/{url_hash}
    """
    import hashlib
    
    # Хэшируем URL + auth identity
    identity = f"{credentials.repo_url}:{credentials.auth_type.value}"
    if credentials.username:
        identity += f":{credentials.username}"
    
    url_hash = hashlib.sha256(identity.encode()).hexdigest()[:16]
    
    return os.path.join(cache_dir, url_hash)


def ensure_repo_cached(
    credentials: GitCredentials,
    cache_dir: str = ".git_cache",
    ref: str = "main",
) -> str:
    """
    Обеспечивает наличие актуального кэша репозитория.
    
    - Если кэша нет — клонирует
    - Если кэш есть — делает fetch
    
    Returns:
        str: Путь к кэшу репозитория
    """
    cache_path = get_cache_path(credentials, cache_dir)
    
    if os.path.exists(cache_path):
        # Обновляем существующий кэш
        fetch_with_gitpython(cache_path, credentials)
    else:
        # Клонируем
        os.makedirs(cache_dir, exist_ok=True)
        clone_with_gitpython(
            credentials,
            cache_path,
            ref=ref,
            bare=True,
        )
    
    return cache_path


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Пример 1: Публичный репозиторий
    creds_public = GitCredentials(
        repo_url="https://github.com/langgenius/dify.git",
        auth_type=AuthType.NONE,
    )
    
    # Пример 2: Приватный репозиторий с токеном
    creds_token = GitCredentials(
        repo_url="https://github.com/user/private-repo.git",
        auth_type=AuthType.TOKEN,
        access_token="ghp_xxxxxxxxxxxx",
    )
    
    # Пример 3: SSH
    creds_ssh = GitCredentials(
        repo_url="git@github.com:user/repo.git",
        auth_type=AuthType.SSH,
        ssh_private_key="""-----BEGIN OPENSSH PRIVATE KEY-----
...
-----END OPENSSH PRIVATE KEY-----""",
    )
    
    # Клонирование
    # repo = clone_with_gitpython(creds_public, "/tmp/test-repo")
    
    # Кэширование
    # cache_path = ensure_repo_cached(creds_public)
    # print(f"Repo cached at: {cache_path}")
