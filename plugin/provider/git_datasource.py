"""
Git Datasource Provider - credential validation.
"""

from collections.abc import Mapping
from typing import Any

from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from dify_plugin.interfaces.datasource import DatasourceProvider


class GitDatasourceProvider(DatasourceProvider):
    """
    Git Repository Data Source Provider.

    Validates credentials when configuring the data source.
    """

    def _validate_credentials(self, credentials: Mapping[str, Any]) -> None:
        """
        Validate credentials.

        Called by Dify when configuring the data source.
        Raises ToolProviderCredentialValidationError if credentials are invalid.
        """
        from utils.url_utils import validate_repo_url, get_url_type
        from utils.masking import mask_credentials

        repo_url = credentials.get("repo_url")
        if not repo_url:
            raise ToolProviderCredentialValidationError("Repository URL is required")

        # Validate URL format
        is_valid, error_msg = validate_repo_url(repo_url)
        if not is_valid:
            raise ToolProviderCredentialValidationError(error_msg)

        # Check auth type matches URL type
        url_type = get_url_type(repo_url)
        ssh_private_key = credentials.get("ssh_private_key")

        if url_type == "ssh" and not ssh_private_key:
            raise ToolProviderCredentialValidationError(
                "SSH URL requires SSH private key"
            )

        if ssh_private_key and url_type != "ssh":
            raise ToolProviderCredentialValidationError(
                "SSH private key provided but URL is not SSH format. "
                "Use git@host:user/repo.git or ssh://host/user/repo.git"
            )

        # Test connection
        try:
            self._test_connection(credentials)
        except Exception as e:
            # Mask credentials in error message
            error_str = mask_credentials(str(e), dict(credentials))
            raise ToolProviderCredentialValidationError(
                f"Cannot connect to repository: {error_str}"
            ) from e

    def _test_connection(self, credentials: Mapping[str, Any]) -> None:
        """
        Test connection to repository.

        Uses git ls-remote to verify access.
        """
        from git_client import GitClient

        repo_url = credentials.get("repo_url", "")
        branch = credentials.get("branch", "main")

        client = GitClient(
            repo_url=repo_url,
            branch=branch,
            credentials=dict(credentials),
            cache_dir="/tmp/git_datasource_cache",
        )

        # This will raise an exception if connection fails
        client.test_connection()
