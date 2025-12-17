"""
Data models for Git Datasource Plugin.
"""

from dataclasses import dataclass, field, asdict
from typing import Any
import json


@dataclass
class FileInfo:
    """Information about a file in the repository."""

    path: str  # Full path from repository root
    name: str  # File name (basename)
    size: int  # Size in bytes
    type: str  # "file" or "folder"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileInfo":
        """Create from dictionary."""
        return cls(
            path=data["path"],
            name=data["name"],
            size=data["size"],
            type=data["type"],
        )

    @classmethod
    def from_json(cls, json_str: str) -> "FileInfo":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class ChangeSet:
    """Set of changes between two commits."""

    added: list[str] = field(default_factory=list)  # Added file paths
    modified: list[str] = field(default_factory=list)  # Modified file paths
    deleted: list[str] = field(default_factory=list)  # Deleted file paths
    renamed: list[tuple[str, str]] = field(default_factory=list)  # (old_path, new_path)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "added": self.added,
            "modified": self.modified,
            "deleted": self.deleted,
            "renamed": self.renamed,
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChangeSet":
        """Create from dictionary."""
        return cls(
            added=data.get("added", []),
            modified=data.get("modified", []),
            deleted=data.get("deleted", []),
            renamed=[tuple(r) for r in data.get("renamed", [])],
        )

    @classmethod
    def from_json(cls, json_str: str) -> "ChangeSet":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def is_empty(self) -> bool:
        """Check if changeset has no changes."""
        return (
            not self.added
            and not self.modified
            and not self.deleted
            and not self.renamed
        )

    def get_all_affected_paths(self) -> set[str]:
        """Get all paths affected by changes."""
        paths = set(self.added + self.modified + self.deleted)
        for old_path, new_path in self.renamed:
            paths.add(old_path)
            paths.add(new_path)
        return paths
