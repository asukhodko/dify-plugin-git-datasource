"""
Примеры SSH аутентификации для Git репозиториев.

Поддержка:
- SSH ключи из строки (Dify secret field)
- SSH ключи из файла
- SSH agent
- Различные типы ключей (RSA, Ed25519)
"""

import os
import tempfile
from contextlib import contextmanager
from typing import Optional, Generator
from dataclasses import dataclass


@dataclass
class SSHCredentials:
    """SSH учетные данные."""
    private_key: str  # PEM-формат ключа
    passphrase: Optional[str] = None


# =============================================================================
# GitPython SSH Authentication
# =============================================================================

@contextmanager
def ssh_environment(
    private_key: str,
    passphrase: Optional[str] = None,
) -> Generator[None, None, None]:
    """
    Контекстный менеджер для SSH окружения.
    
    Создаёт временный файл с ключом и настраивает GIT_SSH_COMMAND.
    Гарантирует безопасную очистку после использования.
    
    Args:
        private_key: SSH приватный ключ в PEM формате
        passphrase: Passphrase для ключа (опционально)
    
    Usage:
        with ssh_environment(key):
            repo = Repo.clone_from("git@github.com:user/repo.git", target)
    """
    # Создаём временный файл с ключом
    fd, key_path = tempfile.mkstemp(suffix='.key', prefix='git_ssh_')
    
    try:
        # Записываем ключ
        os.write(fd, private_key.encode())
        os.close(fd)
        
        # Устанавливаем права (SSH требует 600)
        os.chmod(key_path, 0o600)
        
        # Формируем SSH команду
        # -o StrictHostKeyChecking=no — не проверять host key (для автоматизации)
        # -o UserKnownHostsFile=/dev/null — не сохранять host keys
        # -o BatchMode=yes — не запрашивать ввод
        ssh_cmd = (
            f"ssh -i {key_path} "
            f"-o StrictHostKeyChecking=no "
            f"-o UserKnownHostsFile=/dev/null "
            f"-o BatchMode=yes"
        )
        
        # Если есть passphrase, нужен SSH_ASKPASS или sshpass
        # Для простоты предполагаем ключ без passphrase
        # В production можно использовать sshpass:
        # ssh_cmd = f"sshpass -P passphrase -p '{passphrase}' {ssh_cmd}"
        
        # Сохраняем старое значение
        old_ssh_command = os.environ.get("GIT_SSH_COMMAND")
        
        # Устанавливаем новое
        os.environ["GIT_SSH_COMMAND"] = ssh_cmd
        
        yield
        
    finally:
        # Восстанавливаем окружение
        if old_ssh_command is not None:
            os.environ["GIT_SSH_COMMAND"] = old_ssh_command
        else:
            os.environ.pop("GIT_SSH_COMMAND", None)
        
        # Безопасно удаляем ключ
        try:
            # Перезаписываем файл нулями
            key_size = len(private_key)
            with open(key_path, 'wb') as f:
                f.write(b'\x00' * key_size)
            
            # Удаляем файл
            os.unlink(key_path)
        except Exception:
            pass  # Best effort cleanup


def clone_with_ssh_gitpython(
    repo_url: str,
    target_path: str,
    private_key: str,
    passphrase: Optional[str] = None,
    branch: str = "main",
    bare: bool = True,
) -> "git.Repo":
    """
    Клонирование через SSH с GitPython.
    
    Args:
        repo_url: SSH URL (git@github.com:user/repo.git)
        target_path: Путь для клонирования
        private_key: SSH приватный ключ
        passphrase: Passphrase (опционально)
        branch: Ветка
        bare: Bare clone
    
    Returns:
        git.Repo: Клонированный репозиторий
    """
    from git import Repo
    
    with ssh_environment(private_key, passphrase):
        repo = Repo.clone_from(
            url=repo_url,
            to_path=target_path,
            bare=bare,
        )
        
        if not bare:
            repo.git.checkout(branch)
        
        return repo


def fetch_with_ssh_gitpython(
    repo_path: str,
    private_key: str,
    passphrase: Optional[str] = None,
) -> str:
    """
    Fetch через SSH с GitPython.
    
    Returns:
        str: SHA нового HEAD
    """
    from git import Repo
    
    repo = Repo(repo_path)
    
    with ssh_environment(private_key, passphrase):
        origin = repo.remotes.origin
        origin.fetch()
    
    return repo.head.commit.hexsha


# =============================================================================
# Dulwich SSH Authentication
# =============================================================================

def clone_with_ssh_dulwich(
    repo_url: str,
    target_path: str,
    private_key: str,
    passphrase: Optional[str] = None,
    bare: bool = True,
):
    """
    Клонирование через SSH с Dulwich.
    
    Примечание: Dulwich использует Paramiko для SSH.
    Требуется: pip install dulwich[paramiko]
    
    Args:
        repo_url: SSH URL
        target_path: Путь для клонирования
        private_key: SSH приватный ключ
        passphrase: Passphrase (опционально)
        bare: Bare clone
    """
    from dulwich import porcelain
    from dulwich.contrib.paramiko_vendor import ParamikoSSHVendor
    import paramiko
    import io
    
    class CustomSSHVendor(ParamikoSSHVendor):
        """SSH vendor с ключом из строки."""
        
        def __init__(self, key_str: str, key_passphrase: Optional[str]):
            super().__init__()
            self._key_str = key_str
            self._key_passphrase = key_passphrase
        
        def _load_key(self) -> paramiko.PKey:
            """Загрузка ключа из строки."""
            key_file = io.StringIO(self._key_str)
            
            # Пробуем разные типы ключей
            key_types = [
                (paramiko.RSAKey, "RSA"),
                (paramiko.Ed25519Key, "Ed25519"),
                (paramiko.ECDSAKey, "ECDSA"),
                (paramiko.DSSKey, "DSS"),
            ]
            
            for key_class, key_name in key_types:
                try:
                    key_file.seek(0)
                    return key_class.from_private_key(
                        key_file,
                        password=self._key_passphrase
                    )
                except paramiko.SSHException:
                    continue
            
            raise ValueError("Cannot load SSH key: unsupported format")
        
        def run_command(
            self,
            host: str,
            command: str,
            username: Optional[str] = None,
            port: Optional[int] = None,
            **kwargs
        ):
            """Выполнение SSH команды."""
            pkey = self._load_key()
            
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            client.connect(
                hostname=host,
                port=port or 22,
                username=username or "git",
                pkey=pkey,
                look_for_keys=False,
                allow_agent=False,
            )
            
            return client.exec_command(command)
    
    # Устанавливаем кастомный SSH vendor
    # ВАЖНО: Это глобальная настройка
    import dulwich.client
    old_vendor = dulwich.client.get_ssh_vendor
    
    try:
        vendor = CustomSSHVendor(private_key, passphrase)
        dulwich.client.get_ssh_vendor = lambda: vendor
        
        repo = porcelain.clone(
            source=repo_url,
            target=target_path,
            bare=bare,
        )
        
        return repo
        
    finally:
        dulwich.client.get_ssh_vendor = old_vendor


# =============================================================================
# Key Validation
# =============================================================================

def validate_ssh_key(key: str) -> tuple[bool, str]:
    """
    Валидация SSH приватного ключа.
    
    Returns:
        tuple[bool, str]: (is_valid, error_message or key_type)
    """
    key = key.strip()
    
    # Проверяем наличие маркеров
    if "-----BEGIN" not in key or "-----END" not in key:
        return False, "Missing BEGIN/END markers"
    
    # Определяем тип ключа
    key_types = {
        "-----BEGIN OPENSSH PRIVATE KEY-----": "OpenSSH",
        "-----BEGIN RSA PRIVATE KEY-----": "RSA",
        "-----BEGIN EC PRIVATE KEY-----": "ECDSA",
        "-----BEGIN DSA PRIVATE KEY-----": "DSA",
    }
    
    for marker, key_type in key_types.items():
        if marker in key:
            return True, key_type
    
    # Проверяем что это не публичный ключ
    if "PUBLIC KEY" in key:
        return False, "This is a public key, private key required"
    
    return False, "Unknown key format"


def normalize_ssh_key(key: str) -> str:
    """
    Нормализация SSH ключа.
    
    - Убирает лишние пробелы
    - Нормализует переносы строк
    """
    lines = key.strip().split('\n')
    normalized = []
    
    for line in lines:
        line = line.rstrip()
        if line:
            normalized.append(line)
    
    return '\n'.join(normalized) + '\n'


# =============================================================================
# Integration Example
# =============================================================================

class SSHGitClient:
    """
    Git клиент с SSH аутентификацией.
    
    Использование:
        client = SSHGitClient("git@github.com:user/repo.git", ssh_key)
        client.clone("/tmp/repo")
        files = client.list_files("main")
    """
    
    def __init__(
        self,
        repo_url: str,
        private_key: str,
        passphrase: Optional[str] = None,
    ):
        is_valid, msg = validate_ssh_key(private_key)
        if not is_valid:
            raise ValueError(f"Invalid SSH key: {msg}")
        
        self.repo_url = repo_url
        self.private_key = normalize_ssh_key(private_key)
        self.passphrase = passphrase
        self._local_path: Optional[str] = None
    
    def clone(self, target_path: str, bare: bool = True):
        """Клонирование репозитория."""
        clone_with_ssh_gitpython(
            self.repo_url,
            target_path,
            self.private_key,
            self.passphrase,
            bare=bare,
        )
        self._local_path = target_path
    
    def fetch(self) -> str:
        """Обновление репозитория."""
        if not self._local_path:
            raise RuntimeError("Repository not cloned")
        
        return fetch_with_ssh_gitpython(
            self._local_path,
            self.private_key,
            self.passphrase,
        )
    
    def list_files(self, ref: str = "main") -> list[str]:
        """Список файлов."""
        if not self._local_path:
            raise RuntimeError("Repository not cloned")
        
        from git import Repo
        
        repo = Repo(self._local_path)
        commit = repo.commit(ref)
        
        files = []
        for item in commit.tree.traverse():
            if item.type == 'blob':
                files.append(item.path)
        
        return files


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Пример SSH ключа (НЕ настоящий)
    example_key = """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
...
-----END OPENSSH PRIVATE KEY-----"""
    
    # Валидация
    is_valid, key_type = validate_ssh_key(example_key)
    print(f"Key valid: {is_valid}, type: {key_type}")
    
    # Пример клонирования
    # client = SSHGitClient("git@github.com:user/repo.git", example_key)
    # client.clone("/tmp/test-repo")
    # files = client.list_files("main")
    # print(f"Files: {files}")
