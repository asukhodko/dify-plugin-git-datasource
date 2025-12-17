"""
Credential masking utilities.

SECURITY: These functions ensure sensitive data never appears in logs or error messages.
"""

from typing import Any


# Sensitive credential keys
SENSITIVE_KEYS = frozenset(
    [
        "access_token",
        "ssh_private_key",
        "password",
        "token",
        "secret",
        "api_key",
        "private_key",
    ]
)


def mask_credentials(text: str, credentials: dict[str, Any]) -> str:
    """
    Replace credential values with '***' in text.

    Args:
        text: Text that may contain credentials
        credentials: Dictionary of credentials to mask

    Returns:
        Text with all credential values replaced by '***'
    """
    if not text or not credentials:
        return text

    result = text

    for key, value in credentials.items():
        if value and isinstance(value, str) and len(value) > 0:
            # Mask the value
            result = result.replace(value, "***")

    return result


def mask_url(url: str) -> str:
    """
    Mask credentials embedded in URL.

    Handles formats like:
    - https://token:xxx@github.com/...
    - https://user:password@github.com/...

    Args:
        url: URL that may contain embedded credentials

    Returns:
        URL with credentials replaced by '***:***'
    """
    if not url:
        return url

    # Find the position of :// and the last @ before the host
    if "://" not in url:
        return url

    scheme_end = url.index("://") + 3
    rest = url[scheme_end:]

    # Find the @ that separates credentials from host
    # We need to find the last @ before the first /
    slash_pos = rest.find("/")
    if slash_pos == -1:
        search_part = rest
    else:
        search_part = rest[:slash_pos]

    at_pos = search_part.rfind("@")
    if at_pos == -1:
        # No credentials in URL
        return url

    # Replace everything before @ with ***:***
    host_and_path = rest[at_pos + 1 :]
    return f"{url[:scheme_end]}***:***@{host_and_path}"


def mask_token(token: str) -> str:
    """
    Mask a token, showing only first and last 4 characters.

    Args:
        token: Token to mask

    Returns:
        Masked token like "ghp_****xxxx"
    """
    if not token:
        return "***"

    if len(token) <= 8:
        return "***"

    return f"{token[:4]}****{token[-4:]}"


def is_sensitive_key(key: str) -> bool:
    """
    Check if a key name indicates sensitive data.

    Args:
        key: Key name to check

    Returns:
        True if the key likely contains sensitive data
    """
    key_lower = key.lower()
    return any(sensitive in key_lower for sensitive in SENSITIVE_KEYS)


def mask_dict(data: dict[str, Any]) -> dict[str, Any]:
    """
    Create a copy of dict with sensitive values masked.

    Args:
        data: Dictionary that may contain sensitive values

    Returns:
        Copy of dictionary with sensitive values replaced by '***'
    """
    if not data:
        return data

    result = {}
    for key, value in data.items():
        if is_sensitive_key(key) and value:
            result[key] = "***"
        elif isinstance(value, dict):
            result[key] = mask_dict(value)
        else:
            result[key] = value

    return result


def safe_repr(obj: Any, credentials: dict[str, Any] | None = None) -> str:
    """
    Create a safe string representation of an object.

    Masks any credentials found in the string representation.

    Args:
        obj: Object to represent
        credentials: Optional credentials to mask

    Returns:
        Safe string representation
    """
    text = repr(obj)

    if credentials:
        text = mask_credentials(text, credentials)

    # Also mask common URL patterns with credentials
    text = mask_url(text)

    return text
