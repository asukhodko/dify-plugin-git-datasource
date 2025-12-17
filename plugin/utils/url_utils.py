"""
URL validation and type detection utilities.
"""

import re
from typing import Literal
from urllib.parse import urlparse, quote


UrlType = Literal["https", "ssh", "local", "unknown"]


# Valid URL patterns
HTTPS_PATTERN = re.compile(
    r"^https?://[a-zA-Z0-9.-]+(?::\d+)?/[a-zA-Z0-9._/-]+(?:\.git)?$"
)
SSH_GIT_PATTERN = re.compile(r"^git@[a-zA-Z0-9.-]+:[a-zA-Z0-9._/-]+(?:\.git)?$")
SSH_URL_PATTERN = re.compile(
    r"^ssh://(?:[a-zA-Z0-9._-]+@)?[a-zA-Z0-9.-]+(?::\d+)?/[a-zA-Z0-9._/-]+(?:\.git)?$"
)
LOCAL_PATH_PATTERN = re.compile(r"^(?:file://)?/[a-zA-Z0-9._/-]+$")


def validate_repo_url(url: str) -> tuple[bool, str]:
    """
    Validate repository URL format.

    Args:
        url: Repository URL to validate

    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is empty string.
    """
    if not url:
        return False, "Repository URL is required"

    url = url.strip()

    # Check for valid patterns
    if HTTPS_PATTERN.match(url):
        return True, ""

    if SSH_GIT_PATTERN.match(url):
        return True, ""

    if SSH_URL_PATTERN.match(url):
        return True, ""

    if LOCAL_PATH_PATTERN.match(url):
        return True, ""

    # Check for common mistakes
    if url.startswith("git://"):
        return (
            False,
            "git:// protocol is not supported. Use https:// or git@host:user/repo.git",
        )

    if "@" in url and "://" not in url and ":" not in url.split("@")[1]:
        return False, "Invalid SSH URL format. Use git@host:user/repo.git"

    return False, (
        "Invalid repository URL format. Supported formats:\n"
        "- HTTPS: https://github.com/user/repo.git\n"
        "- SSH: git@github.com:user/repo.git\n"
        "- SSH URL: ssh://git@github.com/user/repo.git\n"
        "- Local: /path/to/repo or file:///path/to/repo"
    )


def get_url_type(url: str) -> UrlType:
    """
    Detect URL type.

    Args:
        url: Repository URL

    Returns:
        URL type: "https", "ssh", "local", or "unknown"
    """
    if not url:
        return "unknown"

    url = url.strip()

    # HTTPS
    if url.startswith("https://") or url.startswith("http://"):
        return "https"

    # SSH formats
    if url.startswith("git@") or url.startswith("ssh://"):
        return "ssh"

    # Local path
    if url.startswith("/") or url.startswith("file://"):
        return "local"

    return "unknown"


def build_auth_url(url: str, token: str | None = None) -> str:
    """
    Build authenticated URL with embedded token.

    WARNING: The returned URL contains credentials and should NEVER be logged!

    Args:
        url: Original HTTPS URL
        token: Access token (optional)

    Returns:
        URL with embedded token for authentication
    """
    if not token:
        return url

    url_type = get_url_type(url)
    if url_type != "https":
        # Token auth only works with HTTPS
        return url

    # Parse URL
    parsed = urlparse(url)

    # Embed token in URL
    # Format: https://token:TOKEN@host/path
    netloc_with_auth = f"token:{quote(token, safe='')}@{parsed.netloc}"

    # Reconstruct URL
    auth_url = f"{parsed.scheme}://{netloc_with_auth}{parsed.path}"
    if parsed.query:
        auth_url += f"?{parsed.query}"

    return auth_url


def extract_repo_name(url: str) -> str:
    """
    Extract repository name from URL.

    Args:
        url: Repository URL

    Returns:
        Repository name (e.g., "repo" from "https://github.com/user/repo.git")
    """
    if not url:
        return "unknown"

    url = url.strip()

    # Remove .git suffix
    if url.endswith(".git"):
        url = url[:-4]

    # Get last path component
    if "/" in url:
        return url.rsplit("/", 1)[-1]

    if ":" in url:
        return url.rsplit(":", 1)[-1]

    return url
