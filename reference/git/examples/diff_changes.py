"""
Примеры определения изменений между коммитами.

Используется для инкрементальной синхронизации:
- Определение добавленных файлов
- Определение измененных файлов
- Определение удаленных файлов
- Обработка переименований
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


class ChangeType(Enum):
    """Тип изменения файла."""
    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"
    RENAMED = "R"


@dataclass
class FileChange:
    """Информация об изменении файла."""
    change_type: ChangeType
    path: str
    old_path: Optional[str] = None  # Для переименований
    old_sha: Optional[str] = None
    new_sha: Optional[str] = None


@dataclass
class SyncChanges:
    """Результат сравнения для синхронизации."""
    added: List[str]
    modified: List[str]
    deleted: List[str]
    renamed: List[Tuple[str, str]]  # (old_path, new_path)


# =============================================================================
# GitPython Implementation
# =============================================================================

def get_changes_gitpython(
    repo_path: str,
    old_sha: str,
    new_sha: str,
    subdir: str = "",
    extensions: Optional[List[str]] = None,
) -> SyncChanges:
    """
    Получение изменений между двумя коммитами (GitPython).
    
    Args:
        repo_path: Путь к репозиторию
        old_sha: SHA старого коммита (last_synced)
        new_sha: SHA нового коммита (HEAD)
        subdir: Фильтр по поддиректории
        extensions: Фильтр по расширениям
    
    Returns:
        SyncChanges с списками изменений
    """
    from git import Repo
    
    repo = Repo(repo_path)
    
    old_commit = repo.commit(old_sha)
    new_commit = repo.commit(new_sha)
    
    # Получаем diff
    diff = old_commit.diff(new_commit)
    
    changes = SyncChanges(
        added=[],
        modified=[],
        deleted=[],
        renamed=[],
    )
    
    for d in diff:
        # Определяем путь
        path = d.b_path if d.b_path else d.a_path
        old_path = d.a_path
        
        # Фильтр по поддиректории
        if subdir:
            if not (path and path.startswith(subdir)) and \
               not (old_path and old_path.startswith(subdir)):
                continue
        
        # Фильтр по расширениям
        if extensions:
            path_to_check = path or old_path
            if not any(path_to_check.lower().endswith(ext) for ext in extensions):
                continue
        
        # Классифицируем изменение
        if d.new_file:
            changes.added.append(path)
        elif d.deleted_file:
            changes.deleted.append(old_path)
        elif d.renamed:
            changes.renamed.append((old_path, path))
        else:
            changes.modified.append(path)
    
    return changes


def get_head_sha_gitpython(repo_path: str, ref: str = "main") -> str:
    """Получение SHA HEAD для ветки."""
    from git import Repo
    
    repo = Repo(repo_path)
    
    # Пробуем как локальную ветку
    try:
        return repo.commit(ref).hexsha
    except Exception:
        pass
    
    # Пробуем как remote ветку
    try:
        return repo.commit(f"origin/{ref}").hexsha
    except Exception:
        pass
    
    raise ValueError(f"Cannot resolve ref: {ref}")


# =============================================================================
# Dulwich Implementation
# =============================================================================

def get_changes_dulwich(
    repo_path: str,
    old_sha: str,
    new_sha: str,
    subdir: str = "",
    extensions: Optional[List[str]] = None,
) -> SyncChanges:
    """
    Получение изменений между двумя коммитами (Dulwich).
    
    Args:
        repo_path: Путь к репозиторию
        old_sha: SHA старого коммита
        new_sha: SHA нового коммита
        subdir: Фильтр по поддиректории
        extensions: Фильтр по расширениям
    
    Returns:
        SyncChanges с списками изменений
    """
    from dulwich.repo import Repo
    from dulwich.diff_tree import tree_changes, RenameDetector
    
    repo = Repo(repo_path)
    
    old_commit = repo[bytes.fromhex(old_sha)]
    new_commit = repo[bytes.fromhex(new_sha)]
    
    changes = SyncChanges(
        added=[],
        modified=[],
        deleted=[],
        renamed=[],
    )
    
    # Используем RenameDetector для обнаружения переименований
    rename_detector = RenameDetector(repo.object_store)
    
    for change in tree_changes(
        repo.object_store,
        old_commit.tree,
        new_commit.tree,
        rename_detector=rename_detector,
    ):
        old_path = change.old.path.decode() if change.old.path else None
        new_path = change.new.path.decode() if change.new.path else None
        
        # Определяем путь для фильтрации
        path = new_path or old_path
        
        # Фильтр по поддиректории
        if subdir:
            if not (path and path.startswith(subdir)):
                continue
        
        # Фильтр по расширениям
        if extensions:
            if not any(path.lower().endswith(ext) for ext in extensions):
                continue
        
        # Классифицируем изменение
        if change.type == "add":
            changes.added.append(new_path)
        elif change.type == "delete":
            changes.deleted.append(old_path)
        elif change.type == "modify":
            changes.modified.append(new_path)
        elif change.type == "rename":
            changes.renamed.append((old_path, new_path))
    
    return changes


def get_head_sha_dulwich(repo_path: str, ref: str = "main") -> str:
    """Получение SHA HEAD для ветки (Dulwich)."""
    from dulwich.repo import Repo
    
    repo = Repo(repo_path)
    
    ref_bytes = ref.encode()
    
    # Пробуем как локальную ветку
    branch_ref = b"refs/heads/" + ref_bytes
    if branch_ref in repo.refs:
        return repo.refs[branch_ref].hex()
    
    # Пробуем как remote ветку
    remote_ref = b"refs/remotes/origin/" + ref_bytes
    if remote_ref in repo.refs:
        return repo.refs[remote_ref].hex()
    
    raise ValueError(f"Cannot resolve ref: {ref}")


# =============================================================================
# Sync Logic
# =============================================================================

def compute_sync_actions(
    changes: SyncChanges,
    treat_rename_as_delete_add: bool = True,
) -> dict:
    """
    Вычисление действий для синхронизации.
    
    Args:
        changes: Изменения между коммитами
        treat_rename_as_delete_add: Обрабатывать rename как delete + add
    
    Returns:
        dict с ключами:
        - to_add: файлы для добавления/индексации
        - to_update: файлы для обновления
        - to_delete: файлы для удаления
    """
    actions = {
        "to_add": list(changes.added),
        "to_update": list(changes.modified),
        "to_delete": list(changes.deleted),
    }
    
    # Обработка переименований
    for old_path, new_path in changes.renamed:
        if treat_rename_as_delete_add:
            # Удаляем старый, добавляем новый
            actions["to_delete"].append(old_path)
            actions["to_add"].append(new_path)
        else:
            # Обновляем (если Dify поддерживает rename)
            actions["to_update"].append(new_path)
    
    return actions


def should_full_sync(
    repo_path: str,
    last_synced_sha: Optional[str],
    current_sha: str,
    max_commits_for_incremental: int = 1000,
) -> bool:
    """
    Определение необходимости полной синхронизации.
    
    Полная синхронизация нужна если:
    - Нет last_synced_sha (первый sync)
    - last_synced_sha не найден в истории
    - Слишком много коммитов между ними
    
    Returns:
        True если нужна полная синхронизация
    """
    if not last_synced_sha:
        return True
    
    from git import Repo
    
    repo = Repo(repo_path)
    
    # Проверяем что old SHA существует
    try:
        repo.commit(last_synced_sha)
    except Exception:
        return True
    
    # Считаем количество коммитов между ними
    try:
        commits = list(repo.iter_commits(
            f"{last_synced_sha}..{current_sha}",
            max_count=max_commits_for_incremental + 1
        ))
        if len(commits) > max_commits_for_incremental:
            return True
    except Exception:
        return True
    
    return False


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    repo_path = "/path/to/repo"
    
    # Получаем текущий HEAD
    current_sha = get_head_sha_gitpython(repo_path, "main")
    print(f"Current HEAD: {current_sha}")
    
    # Предположим, у нас есть сохраненный last_synced_sha
    last_synced_sha = "abc123..."
    
    # Проверяем нужна ли полная синхронизация
    if should_full_sync(repo_path, last_synced_sha, current_sha):
        print("Full sync required")
    else:
        # Инкрементальная синхронизация
        changes = get_changes_gitpython(
            repo_path,
            last_synced_sha,
            current_sha,
            extensions=[".md", ".txt"],
        )
        
        print(f"Added: {len(changes.added)}")
        print(f"Modified: {len(changes.modified)}")
        print(f"Deleted: {len(changes.deleted)}")
        print(f"Renamed: {len(changes.renamed)}")
        
        # Вычисляем действия
        actions = compute_sync_actions(changes)
        
        print(f"\nActions:")
        print(f"  To add: {actions['to_add']}")
        print(f"  To update: {actions['to_update']}")
        print(f"  To delete: {actions['to_delete']}")
