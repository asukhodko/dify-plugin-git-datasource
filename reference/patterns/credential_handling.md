# Безопасная работа с Credentials

## Обзор

Плагин должен безопасно обрабатывать различные типы учетных данных:
- Access tokens (GitHub, GitLab, Gitea)
- Username/Password
- SSH private keys

## Принципы безопасности

### 1. Никогда не логировать credentials

```python
import logging

logger = logging.getLogger(__name__)

def validate_credentials(credentials: dict):
    # ❌ ПЛОХО — токен попадет в логи
    logger.info(f"Validating credentials: {credentials}")
    
    # ✅ ХОРОШО — логируем только безопасную информацию
    logger.info(f"Validating credentials for repo: {credentials.get('repo_url')}")
    logger.info(f"Auth type: {credentials.get('auth_type')}")
```

### 2. Маскирование в сообщениях об ошибках

```python
def mask_url(url: str) -> str:
    """Маскирование credentials в URL."""
    import re
    # https://token:xxx@github.com -> https://***:***@github.com
    return re.sub(r'://[^@]+@', '://***:***@', url)

def mask_token(token: str) -> str:
    """Маскирование токена."""
    if len(token) <= 8:
        return "***"
    return token[:4] + "***" + token[-4:]

# Использование в ошибках
try:
    clone_repo(url_with_token)
except Exception as e:
    raise ValueError(f"Failed to clone {mask_url(url_with_token)}: {e}")
```

### 3. Очистка временных файлов

```python
import os
import tempfile
from contextlib import contextmanager

@contextmanager
def temp_ssh_key(private_key: str):
    """
    Контекстный менеджер для временного SSH ключа.
    Гарантирует удаление файла после использования.
    """
    fd, path = tempfile.mkstemp(suffix='.key', prefix='git_')
    try:
        os.write(fd, private_key.encode())
        os.close(fd)
        os.chmod(path, 0o600)
        yield path
    finally:
        # Перезаписываем файл нулями перед удалением
        try:
            with open(path, 'wb') as f:
                f.write(b'\x00' * len(private_key))
            os.unlink(path)
        except Exception:
            pass

# Использование
with temp_ssh_key(credentials.ssh_private_key) as key_path:
    os.environ["GIT_SSH_COMMAND"] = f"ssh -i {key_path} -o StrictHostKeyChecking=no"
    repo = Repo.clone_from(url, target)
# Ключ автоматически удален
```

### 4. Не хранить credentials в памяти дольше необходимого

```python
class GitClient:
    def __init__(self, credentials: dict):
        # Храним только необходимое
        self._repo_url = credentials.get("repo_url")
        self._auth_type = credentials.get("auth_type")
        
        # Для token/password — используем сразу и забываем
        self._prepared_url = self._prepare_url(credentials)
        
        # Для SSH — храним ключ только если нужен
        if self._auth_type == "ssh":
            self._ssh_key = credentials.get("ssh_private_key")
        else:
            self._ssh_key = None
    
    def _prepare_url(self, credentials: dict) -> str:
        """Подготовка URL с credentials."""
        url = credentials.get("repo_url")
        auth_type = credentials.get("auth_type")
        
        if auth_type == "token":
            token = credentials.get("access_token")
            if url.startswith("https://"):
                url = url.replace("https://", f"https://token:{token}@")
        elif auth_type == "basic":
            username = credentials.get("username")
            password = credentials.get("password")
            if url.startswith("https://"):
                url = url.replace("https://", f"https://{username}:{password}@")
        
        return url
    
    def __del__(self):
        """Очистка при удалении объекта."""
        self._ssh_key = None
        self._prepared_url = None
```

## Типы аутентификации

### 1. Public Repository (no auth)

```python
def clone_public(repo_url: str, target: str):
    """Клонирование публичного репозитория."""
    from git import Repo
    return Repo.clone_from(repo_url, target)
```

### 2. HTTPS + Access Token

Поддерживаемые форматы токенов:
- GitHub: `ghp_xxxxxxxxxxxx`
- GitLab: `glpat-xxxxxxxxxxxx`
- Gitea: `xxxxxxxxxxxxxxxx`

```python
def clone_with_token(repo_url: str, token: str, target: str):
    """Клонирование с access token."""
    from git import Repo
    
    # Встраиваем токен в URL
    if repo_url.startswith("https://"):
        auth_url = repo_url.replace("https://", f"https://token:{token}@")
    else:
        raise ValueError("Token auth requires HTTPS URL")
    
    return Repo.clone_from(auth_url, target)
```

### 3. HTTPS + Username/Password

```python
def clone_with_basic_auth(repo_url: str, username: str, password: str, target: str):
    """Клонирование с basic auth."""
    from git import Repo
    from urllib.parse import quote
    
    # URL-encode username и password
    username_encoded = quote(username, safe='')
    password_encoded = quote(password, safe='')
    
    if repo_url.startswith("https://"):
        auth_url = repo_url.replace(
            "https://",
            f"https://{username_encoded}:{password_encoded}@"
        )
    else:
        raise ValueError("Basic auth requires HTTPS URL")
    
    return Repo.clone_from(auth_url, target)
```

### 4. SSH + Private Key

```python
import os
import tempfile
from contextlib import contextmanager

@contextmanager
def ssh_environment(private_key: str, passphrase: str = None):
    """
    Настройка SSH окружения для Git операций.
    """
    # Создаем временный файл с ключом
    fd, key_path = tempfile.mkstemp(suffix='.key')
    try:
        os.write(fd, private_key.encode())
        os.close(fd)
        os.chmod(key_path, 0o600)
        
        # Формируем SSH команду
        ssh_cmd = f"ssh -i {key_path} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        
        # Если есть passphrase, нужен ssh-agent или sshpass
        # Для простоты предполагаем ключ без passphrase
        
        old_env = os.environ.get("GIT_SSH_COMMAND")
        os.environ["GIT_SSH_COMMAND"] = ssh_cmd
        
        yield
        
    finally:
        # Восстанавливаем окружение
        if old_env:
            os.environ["GIT_SSH_COMMAND"] = old_env
        else:
            os.environ.pop("GIT_SSH_COMMAND", None)
        
        # Безопасно удаляем ключ
        try:
            with open(key_path, 'wb') as f:
                f.write(b'\x00' * len(private_key))
            os.unlink(key_path)
        except Exception:
            pass


def clone_with_ssh(repo_url: str, private_key: str, target: str):
    """Клонирование через SSH."""
    from git import Repo
    
    with ssh_environment(private_key):
        return Repo.clone_from(repo_url, target)
```

## Валидация Credentials

### Проверка формата

```python
import re

def validate_repo_url(url: str) -> bool:
    """Валидация URL репозитория."""
    # HTTPS
    if re.match(r'^https://[^/]+/[^/]+/[^/]+\.git$', url):
        return True
    if re.match(r'^https://[^/]+/[^/]+/[^/]+$', url):
        return True
    
    # SSH
    if re.match(r'^git@[^:]+:[^/]+/[^/]+\.git$', url):
        return True
    if re.match(r'^ssh://[^/]+/[^/]+/[^/]+\.git$', url):
        return True
    
    # Local path
    if url.startswith("/") or url.startswith("file://"):
        return True
    
    return False


def validate_ssh_key(key: str) -> bool:
    """Валидация SSH ключа."""
    # Проверяем формат
    if "-----BEGIN" not in key or "-----END" not in key:
        return False
    
    # Проверяем что это приватный ключ
    valid_headers = [
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "-----BEGIN RSA PRIVATE KEY-----",
        "-----BEGIN EC PRIVATE KEY-----",
        "-----BEGIN DSA PRIVATE KEY-----",
    ]
    
    return any(header in key for header in valid_headers)


def validate_token_format(token: str, provider: str = None) -> bool:
    """Валидация формата токена."""
    if not token or len(token) < 10:
        return False
    
    if provider == "github":
        # GitHub tokens: ghp_, gho_, ghu_, ghs_, ghr_
        return token.startswith(("ghp_", "gho_", "ghu_", "ghs_", "ghr_"))
    elif provider == "gitlab":
        # GitLab tokens: glpat-
        return token.startswith("glpat-")
    
    # Generic — просто проверяем длину
    return len(token) >= 20
```

### Проверка подключения

```python
def test_connection(credentials: dict) -> bool:
    """
    Проверка подключения к репозиторию.
    
    Выполняет ls-remote для проверки доступа.
    """
    from git import cmd
    
    repo_url = credentials.get("repo_url")
    auth_type = credentials.get("auth_type", "none")
    
    # Подготавливаем URL с credentials
    if auth_type == "token":
        token = credentials.get("access_token")
        if repo_url.startswith("https://"):
            repo_url = repo_url.replace("https://", f"https://token:{token}@")
    elif auth_type == "basic":
        username = credentials.get("username")
        password = credentials.get("password")
        if repo_url.startswith("https://"):
            from urllib.parse import quote
            repo_url = repo_url.replace(
                "https://",
                f"https://{quote(username)}:{quote(password)}@"
            )
    
    try:
        if auth_type == "ssh":
            private_key = credentials.get("ssh_private_key")
            with ssh_environment(private_key):
                git = cmd.Git()
                git.ls_remote(repo_url)
        else:
            git = cmd.Git()
            git.ls_remote(repo_url)
        return True
    except Exception as e:
        raise ValueError(f"Connection failed: {mask_url(str(e))}")
```

## Dify Credential Configuration

### YAML конфигурация

```yaml
credentials:
  - name: repo_url
    type: text-input
    required: true
    label:
      en_US: Repository URL
    help:
      en_US: |
        HTTPS: https://github.com/user/repo.git
        SSH: git@github.com:user/repo.git

  - name: auth_type
    type: select
    required: true
    default: none
    label:
      en_US: Authentication
    options:
      - value: none
        label:
          en_US: Public (no auth)
      - value: token
        label:
          en_US: Access Token
      - value: ssh
        label:
          en_US: SSH Key

  # Secret fields — Dify шифрует их
  - name: access_token
    type: secret-input
    required: false
    label:
      en_US: Access Token
    help:
      en_US: Personal access token (GitHub, GitLab, etc.)

  - name: ssh_private_key
    type: secret-input
    required: false
    label:
      en_US: SSH Private Key
    help:
      en_US: |
        Private key for SSH authentication.
        Paste the entire key including BEGIN/END lines.
```

### Обработка в коде

```python
class GitDataSource(DataSourceProvider):
    
    def validate_credentials(self, credentials: dict) -> None:
        """Валидация credentials при настройке."""
        repo_url = credentials.get("repo_url")
        auth_type = credentials.get("auth_type", "none")
        
        # Валидация URL
        if not repo_url:
            raise ValueError("Repository URL is required")
        if not validate_repo_url(repo_url):
            raise ValueError("Invalid repository URL format")
        
        # Валидация auth
        if auth_type == "token":
            token = credentials.get("access_token")
            if not token:
                raise ValueError("Access token is required")
            # Опционально: проверка формата
            # if not validate_token_format(token):
            #     raise ValueError("Invalid token format")
        
        elif auth_type == "ssh":
            ssh_key = credentials.get("ssh_private_key")
            if not ssh_key:
                raise ValueError("SSH private key is required")
            if not validate_ssh_key(ssh_key):
                raise ValueError("Invalid SSH key format")
            
            # Проверяем что URL — SSH
            if not (repo_url.startswith("git@") or repo_url.startswith("ssh://")):
                raise ValueError("SSH auth requires SSH URL (git@... or ssh://...)")
        
        # Проверяем подключение
        test_connection(credentials)
```

## Рекомендации

1. **Используйте `secret-input`** для всех sensitive полей в Dify
2. **Никогда не логируйте** credentials или URL с credentials
3. **Маскируйте** credentials в сообщениях об ошибках
4. **Удаляйте временные файлы** с ключами сразу после использования
5. **Перезаписывайте** содержимое файлов перед удалением
6. **Валидируйте формат** credentials перед использованием
7. **Проверяйте подключение** при настройке источника
