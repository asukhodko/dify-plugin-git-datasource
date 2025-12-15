# Работа с локальными Git репозиториями

> Для сценариев когда репозиторий доступен через файловую систему

## Типы локальных репозиториев

### 1. Working Tree (обычный репозиторий)

```
/path/to/repo/
├── .git/           # Git metadata
├── docs/
│   └── guide.md
└── README.md
```

### 2. Bare Repository

```
/path/to/repo.git/
├── HEAD
├── config
├── objects/
├── refs/
└── ...
```

## Определение типа репозитория

### GitPython

```python
from git import Repo, InvalidGitRepositoryError

def open_local_repo(path: str) -> Repo:
    """
    Открытие локального репозитория.
    
    Поддерживает:
    - Working tree: /path/to/repo
    - Bare: /path/to/repo.git
    """
    try:
        repo = Repo(path)
        
        if repo.bare:
            print(f"Bare repository: {path}")
        else:
            print(f"Working tree: {repo.working_dir}")
        
        return repo
        
    except InvalidGitRepositoryError:
        raise ValueError(f"Not a valid Git repository: {path}")


def is_bare_repo(path: str) -> bool:
    """Проверка является ли репозиторий bare."""
    repo = Repo(path)
    return repo.bare
```

### Dulwich

```python
from dulwich.repo import Repo, NotGitRepository

def open_local_repo_dulwich(path: str):
    """Открытие локального репозитория (Dulwich)."""
    try:
        repo = Repo(path)
        
        # Dulwich определяет bare по наличию .git
        if repo.path.endswith('.git'):
            print("Possible bare repository")
        
        return repo
        
    except NotGitRepository:
        raise ValueError(f"Not a valid Git repository: {path}")
```

## Чтение файлов из локального репозитория

### GitPython — из HEAD

```python
from git import Repo

def read_file_from_local(repo_path: str, ref: str, file_path: str) -> bytes:
    """
    Чтение файла из локального репозитория.
    
    Args:
        repo_path: Путь к репозиторию
        ref: Ветка/тег/SHA (например "main", "v1.0", "abc123")
        file_path: Путь к файлу относительно корня репо
    
    Returns:
        bytes: Содержимое файла
    """
    repo = Repo(repo_path)
    
    try:
        commit = repo.commit(ref)
        blob = commit.tree / file_path
        return blob.data_stream.read()
    except KeyError:
        raise FileNotFoundError(f"File not found: {file_path} in {ref}")
```

### Dulwich — из HEAD

```python
from dulwich.repo import Repo

def read_file_from_local_dulwich(repo_path: str, ref: str, file_path: str) -> bytes:
    """Чтение файла (Dulwich)."""
    repo = Repo(repo_path)
    
    # Разрешаем ref в SHA
    ref_bytes = ref.encode()
    commit_sha = None
    
    # Пробуем как ветку
    if b"refs/heads/" + ref_bytes in repo.refs:
        commit_sha = repo.refs[b"refs/heads/" + ref_bytes]
    # Пробуем как тег
    elif b"refs/tags/" + ref_bytes in repo.refs:
        commit_sha = repo.refs[b"refs/tags/" + ref_bytes]
    # Пробуем как SHA
    else:
        try:
            commit_sha = bytes.fromhex(ref)
        except ValueError:
            raise ValueError(f"Cannot resolve ref: {ref}")
    
    commit = repo[commit_sha]
    tree = repo[commit.tree]
    
    # Навигация по пути
    parts = file_path.split("/")
    current = tree
    
    for i, part in enumerate(parts):
        for entry in current.items():
            if entry.path.decode() == part:
                obj = repo[entry.sha]
                if i == len(parts) - 1:
                    return obj.data
                else:
                    current = obj
                    break
        else:
            raise FileNotFoundError(f"Path not found: {file_path}")
    
    raise FileNotFoundError(f"Path not found: {file_path}")
```

## Обновление локального репозитория

### Fetch (если есть remote)

```python
from git import Repo

def fetch_updates(repo_path: str, remote: str = "origin") -> str:
    """
    Обновление локального репозитория из remote.
    
    Returns:
        str: SHA нового HEAD
    """
    repo = Repo(repo_path)
    
    if remote in [r.name for r in repo.remotes]:
        remote_obj = repo.remote(remote)
        remote_obj.fetch()
    
    return repo.head.commit.hexsha
```

### Для bare репозиториев без remote

Bare репозитории внутри сети (например, служебные копии GitLab/Gitea)
могут не иметь remote. В этом случае:

```python
def get_head_sha_bare(repo_path: str, branch: str = "main") -> str:
    """Получение HEAD SHA для bare репозитория."""
    from git import Repo
    
    repo = Repo(repo_path)
    
    # Для bare репозитория ветки в refs/heads/
    ref = f"refs/heads/{branch}"
    
    try:
        return repo.git.rev_parse(ref)
    except Exception:
        # Fallback на HEAD
        return repo.head.commit.hexsha
```

## Интеграция с плагином

### Определение типа URL

```python
def parse_repo_location(repo_url: str) -> dict:
    """
    Парсинг URL/пути репозитория.
    
    Returns:
        dict с ключами:
        - type: "https" | "ssh" | "local"
        - url: оригинальный URL/путь
        - requires_clone: нужно ли клонировать
    """
    if repo_url.startswith("https://") or repo_url.startswith("http://"):
        return {
            "type": "https",
            "url": repo_url,
            "requires_clone": True,
        }
    elif repo_url.startswith("git@") or repo_url.startswith("ssh://"):
        return {
            "type": "ssh",
            "url": repo_url,
            "requires_clone": True,
        }
    elif repo_url.startswith("/") or repo_url.startswith("file://"):
        # Локальный путь
        path = repo_url.replace("file://", "")
        return {
            "type": "local",
            "url": path,
            "requires_clone": False,  # Можно читать напрямую
        }
    else:
        raise ValueError(f"Unknown repository URL format: {repo_url}")
```

### Использование в datasource

```python
class GitDataSource(OnlineDriveDatasource):
    
    def _get_repo(self) -> str:
        """Получение пути к репозиторию для чтения."""
        repo_url = self.runtime.credentials.get("repo_url")
        location = parse_repo_location(repo_url)
        
        if location["type"] == "local":
            # Читаем напрямую из локального репозитория
            return location["url"]
        else:
            # Для remote — используем кэш
            return self._ensure_cloned()
    
    def _browse_files(self, request):
        repo_path = self._get_repo()
        branch = self.runtime.credentials.get("branch", "main")
        
        # Теперь можно использовать одинаковую логику
        # для локальных и удалённых репозиториев
        files = list_files(repo_path, branch, ...)
        ...
```

## Безопасность локального доступа

### Валидация пути

```python
import os

def validate_local_path(path: str, allowed_prefixes: list[str] = None) -> bool:
    """
    Валидация локального пути к репозиторию.
    
    Args:
        path: Путь к репозиторию
        allowed_prefixes: Разрешённые префиксы путей (для sandboxing)
    
    Returns:
        bool: True если путь валиден
    """
    # Нормализуем путь
    real_path = os.path.realpath(path)
    
    # Проверяем существование
    if not os.path.exists(real_path):
        return False
    
    # Проверяем что это директория
    if not os.path.isdir(real_path):
        return False
    
    # Проверяем что это Git репозиторий
    git_dir = os.path.join(real_path, ".git")
    if not os.path.isdir(git_dir) and not os.path.isfile(os.path.join(real_path, "HEAD")):
        return False
    
    # Проверяем prefix (если указаны)
    if allowed_prefixes:
        if not any(real_path.startswith(prefix) for prefix in allowed_prefixes):
            return False
    
    return True
```

### Изоляция доступа

Для production рекомендуется:

1. **Ограничить разрешённые пути** — только определённые директории
2. **Запретить symlinks** — для предотвращения выхода за пределы
3. **Использовать read-only монтирование** — если возможно

```python
ALLOWED_LOCAL_PREFIXES = [
    "/var/git/",
    "/opt/repos/",
]

def is_safe_local_repo(path: str) -> bool:
    """Проверка безопасности локального пути."""
    real_path = os.path.realpath(path)
    
    # Проверяем что путь в разрешённой зоне
    return any(
        real_path.startswith(prefix)
        for prefix in ALLOWED_LOCAL_PREFIXES
    )
```

## Пример credentials для локального репозитория

```yaml
credentials_schema:
  - name: repo_url
    type: text-input
    required: true
    label:
      en_US: Repository Path
    placeholder:
      en_US: /var/git/myrepo.git or file:///path/to/repo
    help:
      en_US: |
        Local path to Git repository.
        Supports both working tree and bare repositories.
```
