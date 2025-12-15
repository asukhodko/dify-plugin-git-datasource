# Dulwich — Pure Python Git Implementation

> Источник: https://www.dulwich.io/docs/

## Почему Dulwich

- **Pure Python** — не требует установленного `git` binary
- **Портативность** — работает везде где есть Python
- **Полный контроль** — низкоуровневый доступ к Git объектам
- **Активно поддерживается** — регулярные релизы

## Установка

```bash
pip install dulwich
```

## Основные операции

### Клонирование репозитория

```python
from dulwich import porcelain

# Клонирование публичного репозитория
repo = porcelain.clone(
    source="https://github.com/user/repo.git",
    target="/path/to/local/repo"
)

# Клонирование с аутентификацией (HTTPS + token)
repo = porcelain.clone(
    source="https://github.com/user/private-repo.git",
    target="/path/to/local/repo",
    username="token",
    password="ghp_xxxxxxxxxxxx"
)

# Bare clone (без working tree, экономит место)
repo = porcelain.clone(
    source="https://github.com/user/repo.git",
    target="/path/to/local/repo.git",
    bare=True
)
```

### Fetch (обновление)

```python
from dulwich import porcelain
from dulwich.repo import Repo

repo = Repo("/path/to/local/repo")

# Fetch всех веток
porcelain.fetch(repo)

# Fetch с аутентификацией
porcelain.fetch(
    repo,
    username="token",
    password="ghp_xxxxxxxxxxxx"
)
```

### Работа с ветками и refs

```python
from dulwich.repo import Repo

repo = Repo("/path/to/local/repo")

# Получить SHA текущего HEAD
head_sha = repo.head()
print(f"HEAD: {head_sha.decode()}")

# Получить SHA конкретной ветки
refs = repo.refs
main_sha = refs[b"refs/heads/main"]
print(f"main: {main_sha.decode()}")

# Список всех веток
for ref in refs.keys():
    if ref.startswith(b"refs/heads/"):
        branch_name = ref[len(b"refs/heads/"):].decode()
        print(f"Branch: {branch_name}")

# Получить SHA тега
tag_sha = refs.get(b"refs/tags/v1.0.0")
```

### Обход дерева файлов

```python
from dulwich.repo import Repo
from dulwich.objects import Tree, Blob

def walk_tree(repo, tree_sha, path=""):
    """
    Рекурсивный обход дерева файлов.
    
    Yields:
        (path, mode, sha, is_blob)
    """
    tree = repo[tree_sha]
    
    for entry in tree.items():
        name = entry.path.decode()
        mode = entry.mode
        sha = entry.sha
        full_path = f"{path}/{name}" if path else name
        
        obj = repo[sha]
        
        if isinstance(obj, Tree):
            # Это директория — рекурсивно обходим
            yield from walk_tree(repo, sha, full_path)
        elif isinstance(obj, Blob):
            # Это файл
            yield (full_path, mode, sha, True)


# Использование
repo = Repo("/path/to/local/repo")
commit = repo[repo.head()]
tree_sha = commit.tree

for path, mode, sha, is_blob in walk_tree(repo, tree_sha):
    if is_blob:
        print(f"File: {path}")
```

### Чтение содержимого файла

```python
from dulwich.repo import Repo

repo = Repo("/path/to/local/repo")

def read_file(repo, ref, file_path):
    """
    Чтение содержимого файла из репозитория.
    
    Args:
        repo: Dulwich Repo
        ref: ветка, тег или SHA коммита
        file_path: путь к файлу
    
    Returns:
        bytes: содержимое файла
    """
    # Получаем SHA коммита
    if isinstance(ref, str):
        ref = ref.encode()
    
    # Пробуем как ветку
    commit_sha = repo.refs.get(b"refs/heads/" + ref)
    if not commit_sha:
        # Пробуем как тег
        commit_sha = repo.refs.get(b"refs/tags/" + ref)
    if not commit_sha:
        # Пробуем как SHA
        commit_sha = bytes.fromhex(ref.decode())
    
    commit = repo[commit_sha]
    tree = repo[commit.tree]
    
    # Навигация по пути
    parts = file_path.split("/")
    current = tree
    
    for i, part in enumerate(parts):
        found = False
        for entry in current.items():
            if entry.path.decode() == part:
                obj = repo[entry.sha]
                if i == len(parts) - 1:
                    # Последний элемент — должен быть файл
                    return obj.data
                else:
                    # Промежуточный — должен быть директория
                    current = obj
                    found = True
                    break
        if not found:
            raise FileNotFoundError(f"Path not found: {file_path}")
    
    raise FileNotFoundError(f"Path not found: {file_path}")


# Использование
content = read_file(repo, "main", "docs/README.md")
print(content.decode("utf-8"))
```

### Получение истории коммитов для файла

```python
from dulwich.repo import Repo
from dulwich.walk import Walker

def get_file_history(repo, ref, file_path, max_commits=10):
    """
    Получение истории коммитов для файла.
    
    Returns:
        list of (commit_sha, commit_time, author, message)
    """
    # Получаем SHA коммита
    if isinstance(ref, str):
        ref = ref.encode()
    commit_sha = repo.refs.get(b"refs/heads/" + ref)
    
    history = []
    walker = Walker(repo.object_store, [commit_sha], paths=[file_path.encode()])
    
    for entry in walker:
        commit = entry.commit
        history.append({
            "sha": commit.id.hex(),
            "time": commit.commit_time,
            "author": commit.author.decode(),
            "message": commit.message.decode().strip(),
        })
        if len(history) >= max_commits:
            break
    
    return history


# Использование
history = get_file_history(repo, "main", "docs/README.md")
for h in history:
    print(f"{h['sha'][:8]} - {h['message']}")
```

### Определение изменений между коммитами

```python
from dulwich.repo import Repo
from dulwich.diff_tree import tree_changes

def get_changes(repo, old_sha, new_sha):
    """
    Получение списка изменений между двумя коммитами.
    
    Returns:
        dict with keys: added, modified, deleted
    """
    old_commit = repo[bytes.fromhex(old_sha)]
    new_commit = repo[bytes.fromhex(new_sha)]
    
    changes = {
        "added": [],
        "modified": [],
        "deleted": [],
    }
    
    for change in tree_changes(
        repo.object_store,
        old_commit.tree,
        new_commit.tree
    ):
        old_path = change.old.path.decode() if change.old.path else None
        new_path = change.new.path.decode() if change.new.path else None
        
        if change.type == "add":
            changes["added"].append(new_path)
        elif change.type == "delete":
            changes["deleted"].append(old_path)
        elif change.type == "modify":
            changes["modified"].append(new_path)
        elif change.type == "rename":
            changes["deleted"].append(old_path)
            changes["added"].append(new_path)
    
    return changes


# Использование
changes = get_changes(repo, "abc123...", "def456...")
print(f"Added: {changes['added']}")
print(f"Modified: {changes['modified']}")
print(f"Deleted: {changes['deleted']}")
```

## SSH аутентификация

Dulwich поддерживает SSH через Paramiko:

```bash
pip install dulwich[paramiko]
```

```python
from dulwich import porcelain
from dulwich.contrib.paramiko_vendor import ParamikoSSHVendor
import paramiko

# Создаем SSH клиент с ключом
def get_ssh_vendor(private_key_str, passphrase=None):
    """Создание SSH vendor с приватным ключом."""
    
    class CustomSSHVendor(ParamikoSSHVendor):
        def __init__(self, private_key_str, passphrase):
            super().__init__()
            self.private_key_str = private_key_str
            self.passphrase = passphrase
        
        def run_command(self, host, command, username=None, port=None, **kwargs):
            # Загружаем ключ из строки
            import io
            key_file = io.StringIO(self.private_key_str)
            
            try:
                pkey = paramiko.RSAKey.from_private_key(key_file, password=self.passphrase)
            except paramiko.SSHException:
                key_file.seek(0)
                pkey = paramiko.Ed25519Key.from_private_key(key_file, password=self.passphrase)
            
            # Подключаемся
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                host,
                port=port or 22,
                username=username or "git",
                pkey=pkey,
            )
            
            return client.exec_command(command)
    
    return CustomSSHVendor(private_key_str, passphrase)


# Использование
ssh_key = """-----BEGIN OPENSSH PRIVATE KEY-----
...
-----END OPENSSH PRIVATE KEY-----"""

vendor = get_ssh_vendor(ssh_key)

# Клонирование через SSH
repo = porcelain.clone(
    source="git@github.com:user/repo.git",
    target="/path/to/local/repo",
    # Dulwich использует глобальный vendor, нужно настроить
)
```

## Полезные утилиты

### Размер файла без загрузки содержимого

```python
def get_file_size(repo, blob_sha):
    """Получение размера файла по SHA blob'а."""
    blob = repo[blob_sha]
    return len(blob.data)
```

### Фильтрация файлов по расширению

```python
import fnmatch

def filter_files(files, extensions, exclude_patterns):
    """
    Фильтрация списка файлов.
    
    Args:
        files: список путей
        extensions: список расширений (.md, .txt)
        exclude_patterns: glob паттерны для исключения
    """
    result = []
    
    for path in files:
        # Проверяем расширение
        if extensions:
            if not any(path.lower().endswith(ext) for ext in extensions):
                continue
        
        # Проверяем exclude паттерны
        excluded = False
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(path, pattern):
                excluded = True
                break
            # Проверяем каждый компонент пути
            for part in path.split("/"):
                if fnmatch.fnmatch(part, pattern):
                    excluded = True
                    break
        
        if not excluded:
            result.append(path)
    
    return result
```

## Ссылки

- Документация: https://www.dulwich.io/docs/
- GitHub: https://github.com/dulwich/dulwich
- Tutorial: https://www.dulwich.io/docs/tutorial/
- API Reference: https://www.dulwich.io/docs/api/
