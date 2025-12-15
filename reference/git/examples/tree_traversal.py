"""
Примеры обхода дерева файлов Git репозитория.

Включает:
- Рекурсивный обход
- Фильтрация по расширениям
- Исключение по паттернам
- Получение метаданных файлов
"""

import fnmatch
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, List, Optional


@dataclass
class FileInfo:
    """Информация о файле в репозитории."""
    path: str
    name: str
    size: int
    blob_sha: str
    last_commit_sha: Optional[str] = None
    last_commit_time: Optional[datetime] = None
    last_commit_message: Optional[str] = None
    last_commit_author: Optional[str] = None


# =============================================================================
# GitPython Implementation
# =============================================================================

def list_files_gitpython(
    repo_path: str,
    ref: str = "main",
    subdir: str = "",
    extensions: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    max_size_bytes: Optional[int] = None,
    max_files: Optional[int] = None,
    include_history: bool = True,
) -> Iterator[FileInfo]:
    """
    Получение списка файлов из репозитория (GitPython).
    
    Args:
        repo_path: Путь к репозиторию
        ref: Ветка/тег/SHA
        subdir: Поддиректория для фильтрации
        extensions: Список расширений (.md, .txt)
        exclude_patterns: Glob паттерны для исключения
        max_size_bytes: Максимальный размер файла
        max_files: Максимальное количество файлов
        include_history: Включать информацию о последнем коммите
    
    Yields:
        FileInfo для каждого файла
    """
    from git import Repo
    
    repo = Repo(repo_path)
    commit = repo.commit(ref)
    
    # Определяем стартовую точку
    if subdir:
        try:
            tree = commit.tree / subdir
        except KeyError:
            return  # Поддиректория не существует
    else:
        tree = commit.tree
    
    count = 0
    
    for item in _walk_tree_gitpython(tree, subdir):
        path, blob = item
        
        # Фильтрация по расширению
        if extensions:
            if not any(path.lower().endswith(ext.lower()) for ext in extensions):
                continue
        
        # Фильтрация по exclude паттернам
        if exclude_patterns and _matches_exclude(path, exclude_patterns):
            continue
        
        # Фильтрация по размеру
        if max_size_bytes and blob.size > max_size_bytes:
            continue
        
        # Создаем FileInfo
        file_info = FileInfo(
            path=path,
            name=blob.name,
            size=blob.size,
            blob_sha=blob.hexsha,
        )
        
        # Добавляем историю если нужно
        if include_history:
            history = _get_file_last_commit_gitpython(repo, ref, path)
            if history:
                file_info.last_commit_sha = history["sha"]
                file_info.last_commit_time = history["time"]
                file_info.last_commit_message = history["message"]
                file_info.last_commit_author = history["author"]
        
        yield file_info
        
        count += 1
        if max_files and count >= max_files:
            break


def _walk_tree_gitpython(tree, prefix: str = ""):
    """Рекурсивный обход дерева (GitPython)."""
    for item in tree:
        path = f"{prefix}/{item.name}" if prefix else item.name
        
        if item.type == "tree":
            yield from _walk_tree_gitpython(item, path)
        elif item.type == "blob":
            yield (path, item)


def _get_file_last_commit_gitpython(repo, ref: str, file_path: str) -> Optional[dict]:
    """Получение информации о последнем коммите для файла."""
    try:
        commits = list(repo.iter_commits(ref, paths=file_path, max_count=1))
        if commits:
            commit = commits[0]
            return {
                "sha": commit.hexsha,
                "time": commit.committed_datetime,
                "message": commit.message.strip().split("\n")[0],  # Первая строка
                "author": str(commit.author),
            }
    except Exception:
        pass
    return None


# =============================================================================
# Dulwich Implementation
# =============================================================================

def list_files_dulwich(
    repo_path: str,
    ref: str = "main",
    subdir: str = "",
    extensions: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    max_size_bytes: Optional[int] = None,
    max_files: Optional[int] = None,
) -> Iterator[FileInfo]:
    """
    Получение списка файлов из репозитория (Dulwich).
    
    Args:
        repo_path: Путь к репозиторию
        ref: Ветка/тег/SHA
        subdir: Поддиректория для фильтрации
        extensions: Список расширений
        exclude_patterns: Glob паттерны для исключения
        max_size_bytes: Максимальный размер файла
        max_files: Максимальное количество файлов
    
    Yields:
        FileInfo для каждого файла
    """
    from dulwich.repo import Repo
    from dulwich.objects import Tree, Blob
    
    repo = Repo(repo_path)
    
    # Получаем SHA коммита
    commit_sha = _resolve_ref_dulwich(repo, ref)
    commit = repo[commit_sha]
    tree_sha = commit.tree
    
    # Если указана поддиректория, находим её
    if subdir:
        tree_sha = _find_subtree_dulwich(repo, tree_sha, subdir)
        if tree_sha is None:
            return
    
    count = 0
    
    for path, blob_sha in _walk_tree_dulwich(repo, tree_sha, subdir):
        # Фильтрация по расширению
        if extensions:
            if not any(path.lower().endswith(ext.lower()) for ext in extensions):
                continue
        
        # Фильтрация по exclude паттернам
        if exclude_patterns and _matches_exclude(path, exclude_patterns):
            continue
        
        # Получаем blob
        blob = repo[blob_sha]
        
        # Фильтрация по размеру
        if max_size_bytes and len(blob.data) > max_size_bytes:
            continue
        
        file_info = FileInfo(
            path=path,
            name=path.split("/")[-1],
            size=len(blob.data),
            blob_sha=blob_sha.hex(),
        )
        
        yield file_info
        
        count += 1
        if max_files and count >= max_files:
            break


def _resolve_ref_dulwich(repo, ref: str) -> bytes:
    """Разрешение ref в SHA коммита (Dulwich)."""
    ref_bytes = ref.encode() if isinstance(ref, str) else ref
    
    # Пробуем как ветку
    branch_ref = b"refs/heads/" + ref_bytes
    if branch_ref in repo.refs:
        return repo.refs[branch_ref]
    
    # Пробуем как тег
    tag_ref = b"refs/tags/" + ref_bytes
    if tag_ref in repo.refs:
        return repo.refs[tag_ref]
    
    # Пробуем как SHA
    try:
        return bytes.fromhex(ref)
    except ValueError:
        pass
    
    raise ValueError(f"Cannot resolve ref: {ref}")


def _find_subtree_dulwich(repo, tree_sha: bytes, subdir: str) -> Optional[bytes]:
    """Поиск поддиректории в дереве (Dulwich)."""
    from dulwich.objects import Tree
    
    parts = subdir.strip("/").split("/")
    current_sha = tree_sha
    
    for part in parts:
        if not part:
            continue
        
        tree = repo[current_sha]
        found = False
        
        for entry in tree.items():
            if entry.path.decode() == part:
                current_sha = entry.sha
                found = True
                break
        
        if not found:
            return None
    
    return current_sha


def _walk_tree_dulwich(repo, tree_sha: bytes, prefix: str = ""):
    """Рекурсивный обход дерева (Dulwich)."""
    from dulwich.objects import Tree, Blob
    
    tree = repo[tree_sha]
    
    for entry in tree.items():
        name = entry.path.decode()
        path = f"{prefix}/{name}" if prefix else name
        obj = repo[entry.sha]
        
        if isinstance(obj, Tree):
            yield from _walk_tree_dulwich(repo, entry.sha, path)
        elif isinstance(obj, Blob):
            yield (path, entry.sha)


# =============================================================================
# Utility Functions
# =============================================================================

def _matches_exclude(path: str, patterns: List[str]) -> bool:
    """
    Проверка соответствия пути exclude паттернам.
    
    Проверяет:
    - Полный путь
    - Каждый компонент пути отдельно
    """
    for pattern in patterns:
        # Проверяем полный путь
        if fnmatch.fnmatch(path, pattern):
            return True
        if fnmatch.fnmatch(path, f"*/{pattern}"):
            return True
        if fnmatch.fnmatch(path, f"{pattern}/*"):
            return True
        if fnmatch.fnmatch(path, f"*/{pattern}/*"):
            return True
        
        # Проверяем каждый компонент
        for part in path.split("/"):
            if fnmatch.fnmatch(part, pattern):
                return True
    
    return False


def parse_extensions(extensions_str: str) -> List[str]:
    """Парсинг строки расширений в список."""
    if not extensions_str:
        return []
    
    extensions = []
    for ext in extensions_str.split(","):
        ext = ext.strip()
        if ext:
            # Добавляем точку если её нет
            if not ext.startswith("."):
                ext = "." + ext
            extensions.append(ext.lower())
    
    return extensions


def parse_patterns(patterns_str: str) -> List[str]:
    """Парсинг строки паттернов в список."""
    if not patterns_str:
        return []
    
    return [p.strip() for p in patterns_str.split(",") if p.strip()]


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Пример использования
    repo_path = "/path/to/repo"
    
    # Список всех .md файлов
    for file_info in list_files_gitpython(
        repo_path,
        ref="main",
        extensions=[".md", ".txt"],
        exclude_patterns=[".*", "node_modules", "__pycache__"],
        max_size_bytes=1024 * 1024,  # 1 MB
        max_files=1000,
    ):
        print(f"{file_info.path} ({file_info.size} bytes)")
        if file_info.last_commit_time:
            print(f"  Last modified: {file_info.last_commit_time}")
            print(f"  By: {file_info.last_commit_author}")
