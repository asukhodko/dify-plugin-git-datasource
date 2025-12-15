# GitPython — Git Wrapper for Python

> Источник: https://gitpython.readthedocs.io/

## Почему GitPython

- **Высокоуровневый API** — удобнее для типичных операций
- **Зрелая библиотека** — много примеров и документации
- **Требует git binary** — использует системный `git`

## Установка

```bash
pip install GitPython
```

**Важно:** Требуется установленный `git` в системе.

## Основные операции

### Клонирование репозитория

```python
from git import Repo

# Клонирование публичного репозитория
repo = Repo.clone_from(
    url="https://github.com/user/repo.git",
    to_path="/path/to/local/repo"
)

# Клонирование с аутентификацией (HTTPS + token)
# Токен встраивается в URL
repo = Repo.clone_from(
    url="https://token:ghp_xxxx@github.com/user/private-repo.git",
    to_path="/path/to/local/repo"
)

# Bare clone
repo = Repo.clone_from(
    url="https://github.com/user/repo.git",
    to_path="/path/to/local/repo.git",
    bare=True
)

# Shallow clone (только последние N коммитов)
repo = Repo.clone_from(
    url="https://github.com/user/repo.git",
    to_path="/path/to/local/repo",
    depth=1
)
```

### Открытие существующего репозитория

```python
from git import Repo

repo = Repo("/path/to/local/repo")

# Проверка что это валидный репозиторий
if repo.bare:
    print("This is a bare repository")
else:
    print(f"Working directory: {repo.working_dir}")
```

### Fetch (обновление)

```python
from git import Repo

repo = Repo("/path/to/local/repo")

# Fetch из origin
origin = repo.remotes.origin
origin.fetch()

# Fetch с прогрессом
from git import RemoteProgress

class Progress(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        print(f"Progress: {cur_count}/{max_count} {message}")

origin.fetch(progress=Progress())
```

### Работа с ветками и refs

```python
from git import Repo

repo = Repo("/path/to/local/repo")

# Текущая ветка
print(f"Current branch: {repo.active_branch}")

# HEAD commit
head_commit = repo.head.commit
print(f"HEAD: {head_commit.hexsha}")

# Список всех веток
for branch in repo.branches:
    print(f"Branch: {branch.name}")

# Список remote веток
for ref in repo.remotes.origin.refs:
    print(f"Remote: {ref.name}")

# Получить коммит по ветке/тегу
commit = repo.commit("main")
print(f"main: {commit.hexsha}")

# Получить коммит по SHA
commit = repo.commit("abc123def456")
```

### Обход дерева файлов

```python
from git import Repo

repo = Repo("/path/to/local/repo")

def walk_tree(tree, path=""):
    """
    Рекурсивный обход дерева файлов.
    
    Yields:
        (path, blob) для каждого файла
    """
    for item in tree:
        full_path = f"{path}/{item.name}" if path else item.name
        
        if item.type == "tree":
            # Директория — рекурсивно
            yield from walk_tree(item, full_path)
        elif item.type == "blob":
            # Файл
            yield (full_path, item)


# Использование
commit = repo.commit("main")
for path, blob in walk_tree(commit.tree):
    print(f"File: {path}, Size: {blob.size}")
```

### Чтение содержимого файла

```python
from git import Repo

repo = Repo("/path/to/local/repo")

def read_file(repo, ref, file_path):
    """
    Чтение содержимого файла из репозитория.
    
    Args:
        repo: GitPython Repo
        ref: ветка, тег или SHA коммита
        file_path: путь к файлу
    
    Returns:
        bytes: содержимое файла
    """
    commit = repo.commit(ref)
    
    try:
        blob = commit.tree / file_path
        return blob.data_stream.read()
    except KeyError:
        raise FileNotFoundError(f"File not found: {file_path}")


# Использование
content = read_file(repo, "main", "docs/README.md")
print(content.decode("utf-8"))
```

### Получение истории коммитов для файла

```python
from git import Repo

repo = Repo("/path/to/local/repo")

def get_file_history(repo, ref, file_path, max_commits=10):
    """
    Получение истории коммитов для файла.
    
    Returns:
        list of dict with commit info
    """
    history = []
    
    for commit in repo.iter_commits(ref, paths=file_path, max_count=max_commits):
        history.append({
            "sha": commit.hexsha,
            "time": commit.committed_datetime,
            "author": str(commit.author),
            "message": commit.message.strip(),
        })
    
    return history


# Использование
history = get_file_history(repo, "main", "docs/README.md")
for h in history:
    print(f"{h['sha'][:8]} - {h['message']}")
```

### Время последнего изменения файла

```python
from git import Repo
from datetime import datetime

def get_file_last_modified(repo, ref, file_path):
    """
    Получение времени последнего изменения файла.
    
    Returns:
        datetime: время последнего коммита, затрагивающего файл
    """
    commits = list(repo.iter_commits(ref, paths=file_path, max_count=1))
    if commits:
        return commits[0].committed_datetime
    return None


# Использование
last_modified = get_file_last_modified(repo, "main", "docs/README.md")
print(f"Last modified: {last_modified}")
```

### Определение изменений между коммитами

```python
from git import Repo

repo = Repo("/path/to/local/repo")

def get_changes(repo, old_sha, new_sha):
    """
    Получение списка изменений между двумя коммитами.
    
    Returns:
        dict with keys: added, modified, deleted, renamed
    """
    old_commit = repo.commit(old_sha)
    new_commit = repo.commit(new_sha)
    
    diff = old_commit.diff(new_commit)
    
    changes = {
        "added": [],
        "modified": [],
        "deleted": [],
        "renamed": [],
    }
    
    for d in diff:
        if d.new_file:
            changes["added"].append(d.b_path)
        elif d.deleted_file:
            changes["deleted"].append(d.a_path)
        elif d.renamed:
            changes["renamed"].append({
                "from": d.a_path,
                "to": d.b_path,
            })
        else:
            changes["modified"].append(d.a_path)
    
    return changes


# Использование
changes = get_changes(repo, "abc123", "def456")
print(f"Added: {changes['added']}")
print(f"Modified: {changes['modified']}")
print(f"Deleted: {changes['deleted']}")
print(f"Renamed: {changes['renamed']}")
```

### Diff с именами файлов (аналог git diff --name-status)

```python
from git import Repo

def get_changed_files(repo, old_ref, new_ref):
    """
    Получение списка измененных файлов между refs.
    
    Аналог: git diff --name-status old_ref..new_ref
    """
    old_commit = repo.commit(old_ref)
    new_commit = repo.commit(new_ref)
    
    diff_index = old_commit.diff(new_commit)
    
    result = []
    for diff_item in diff_index:
        status = "M"  # modified
        path = diff_item.a_path or diff_item.b_path
        
        if diff_item.new_file:
            status = "A"  # added
            path = diff_item.b_path
        elif diff_item.deleted_file:
            status = "D"  # deleted
            path = diff_item.a_path
        elif diff_item.renamed:
            status = "R"  # renamed
            path = f"{diff_item.a_path} -> {diff_item.b_path}"
        
        result.append((status, path))
    
    return result


# Использование
changes = get_changed_files(repo, "v1.0.0", "main")
for status, path in changes:
    print(f"{status} {path}")
```

## SSH аутентификация

GitPython использует системный SSH:

```python
from git import Repo
import os

# Вариант 1: Использовать системный SSH agent
# Ключ должен быть добавлен в agent: ssh-add ~/.ssh/id_rsa

repo = Repo.clone_from(
    url="git@github.com:user/repo.git",
    to_path="/path/to/local/repo"
)

# Вариант 2: Указать конкретный ключ через GIT_SSH_COMMAND
os.environ["GIT_SSH_COMMAND"] = "ssh -i /path/to/private_key -o StrictHostKeyChecking=no"

repo = Repo.clone_from(
    url="git@github.com:user/repo.git",
    to_path="/path/to/local/repo"
)

# Вариант 3: Временный файл с ключом
import tempfile

def clone_with_ssh_key(url, target, private_key_str):
    """Клонирование с SSH ключом из строки."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.key', delete=False) as f:
        f.write(private_key_str)
        key_path = f.name
    
    try:
        os.chmod(key_path, 0o600)
        os.environ["GIT_SSH_COMMAND"] = f"ssh -i {key_path} -o StrictHostKeyChecking=no"
        repo = Repo.clone_from(url, target)
        return repo
    finally:
        os.unlink(key_path)
```

## Сравнение с Dulwich

| Аспект | GitPython | Dulwich |
|--------|-----------|---------|
| Зависимости | Требует git binary | Pure Python |
| API | Высокоуровневый | Низкоуровневый |
| Производительность | Быстрее (нативный git) | Медленнее |
| Портативность | Зависит от системы | Везде где Python |
| SSH | Через системный SSH | Через Paramiko |

## Рекомендация для проекта

**Для MVP:** GitPython — проще в использовании, быстрее.

**Для production:** Dulwich — лучшая портативность, не зависит от системы.

**Гибридный подход:** Использовать GitPython если git доступен, fallback на Dulwich.

## Ссылки

- Документация: https://gitpython.readthedocs.io/
- GitHub: https://github.com/gitpython-developers/GitPython
- Tutorial: https://gitpython.readthedocs.io/en/stable/tutorial.html
