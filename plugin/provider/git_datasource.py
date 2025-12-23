"""
Git Datasource Provider - credential validation.
"""

import logging
from collections.abc import Mapping
from typing import Any

from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from dify_plugin.interfaces.datasource import DatasourceProvider

logger = logging.getLogger(__name__)


class GitDatasourceProvider(DatasourceProvider):
    """
    Git Repository Data Source Provider.

    Validates credentials when configuring the data source.
    
    In website_crawl mode:
    - Credentials (access_token, ssh_private_key) are configured at plugin level
    - Parameters (repo_url, branch, etc.) are specified when creating Knowledge Base
    """

    def _validate_credentials(self, credentials: Mapping[str, Any]) -> None:
        """
        Validate credentials format.

        Called by Dify when configuring the plugin authorization.
        At this stage we only have credentials (access_token, ssh_private_key),
        NOT the repository URL - that comes later when creating Knowledge Base.
        
        Raises ToolProviderCredentialValidationError if credentials are invalid.
        """
        access_token = credentials.get("access_token", "")
        ssh_private_key = credentials.get("ssh_private_key", "")
        
        # At least one credential should be provided (or both empty for public repos)
        # We can't validate against a repo URL here because it's not available yet
        
        # Validate SSH key format if provided
        if ssh_private_key:
            self._validate_ssh_key_format(ssh_private_key)
        
        # Validate access token format if provided
        if access_token:
            self._validate_access_token_format(access_token)
        
        # If both are empty, that's OK - user might use public repos
        # The actual connection test will happen when creating Knowledge Base
        
        logger.info("Credentials validated successfully")
    
    def _validate_ssh_key_format(self, ssh_key: str) -> None:
        """
        Validate SSH private key format.
        
        Checks that the key looks like a valid PEM-formatted private key.
        """
        # Normalize key - handle various formats
        normalized = ssh_key.replace("\\n", "\n").strip()
        
        # Check for PEM format markers
        valid_headers = [
            "-----BEGIN RSA PRIVATE KEY-----",
            "-----BEGIN OPENSSH PRIVATE KEY-----",
            "-----BEGIN PRIVATE KEY-----",
            "-----BEGIN EC PRIVATE KEY-----",
            "-----BEGIN DSA PRIVATE KEY-----",
        ]
        
        has_valid_header = any(header in normalized for header in valid_headers)
        has_end_marker = "-----END" in normalized and "PRIVATE KEY-----" in normalized
        
        if not has_valid_header:
            raise ToolProviderCredentialValidationError(
                "Invalid SSH key format. Key must be in PEM format "
                "(starting with -----BEGIN ... PRIVATE KEY-----). "
                "For OpenSSH keys, convert with: ssh-keygen -p -m PEM -f keyfile"
            )
        
        if not has_end_marker:
            raise ToolProviderCredentialValidationError(
                "Invalid SSH key format. Key appears to be truncated "
                "(missing -----END ... PRIVATE KEY----- marker)"
            )
    
    def _validate_access_token_format(self, token: str) -> None:
        """
        Validate access token format.
        
        Basic validation - token should not be empty or contain only whitespace.
        """
        if not token.strip():
            raise ToolProviderCredentialValidationError(
                "Access token cannot be empty or whitespace only"
            )
        
        # Token should not contain newlines or other control characters
        if "\n" in token or "\r" in token:
            raise ToolProviderCredentialValidationError(
                "Access token should not contain newlines"
            )
