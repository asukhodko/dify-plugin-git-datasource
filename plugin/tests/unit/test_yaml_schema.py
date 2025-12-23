"""
Unit tests for YAML configuration schema validation.

Validates that datasource and provider YAML files conform to Dify's expected schema.
"""

import pytest
import yaml
from pathlib import Path


# Valid types for datasource parameters (from Dify pydantic schema)
VALID_PARAMETER_TYPES = {"string", "number", "boolean", "select", "secret-input", "file", "files"}

# Required fields for datasource parameters
REQUIRED_PARAMETER_FIELDS = {"name", "type", "label", "description"}

# Required fields for credentials schema
REQUIRED_CREDENTIAL_FIELDS = {"name", "type", "label"}


class TestDatasourceYamlSchema:
    """Tests for datasource YAML schema validation."""
    
    @pytest.fixture
    def datasource_yaml(self):
        """Load datasource YAML file."""
        yaml_path = Path(__file__).parent.parent.parent / "datasources" / "git_datasource.yaml"
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    def test_identity_required_fields(self, datasource_yaml):
        """Test identity section has required fields."""
        assert "identity" in datasource_yaml
        identity = datasource_yaml["identity"]
        
        assert "name" in identity
        assert "author" in identity
        assert "label" in identity
        
        # Label must have at least en_US
        assert "en_US" in identity["label"]
    
    def test_description_required(self, datasource_yaml):
        """Test description section exists."""
        assert "description" in datasource_yaml
        assert "en_US" in datasource_yaml["description"]
    
    def test_parameters_valid_types(self, datasource_yaml):
        """Test all parameters have valid types."""
        if "parameters" not in datasource_yaml:
            pytest.skip("No parameters defined")
        
        for i, param in enumerate(datasource_yaml["parameters"]):
            param_type = param.get("type")
            assert param_type in VALID_PARAMETER_TYPES, (
                f"Parameter {i} ({param.get('name', 'unknown')}) has invalid type '{param_type}'. "
                f"Valid types: {VALID_PARAMETER_TYPES}"
            )
    
    def test_parameters_required_fields(self, datasource_yaml):
        """Test all parameters have required fields."""
        if "parameters" not in datasource_yaml:
            pytest.skip("No parameters defined")
        
        for i, param in enumerate(datasource_yaml["parameters"]):
            param_name = param.get("name", f"parameter_{i}")
            
            for field in REQUIRED_PARAMETER_FIELDS:
                assert field in param, (
                    f"Parameter '{param_name}' missing required field '{field}'"
                )
            
            # Label and description must have at least en_US
            assert "en_US" in param["label"], (
                f"Parameter '{param_name}' label missing en_US"
            )
            assert "en_US" in param["description"], (
                f"Parameter '{param_name}' description missing en_US"
            )
    
    def test_extra_python_source(self, datasource_yaml):
        """Test extra.python.source points to existing file."""
        assert "extra" in datasource_yaml
        assert "python" in datasource_yaml["extra"]
        assert "source" in datasource_yaml["extra"]["python"]
        
        source_path = datasource_yaml["extra"]["python"]["source"]
        full_path = Path(__file__).parent.parent.parent / source_path
        
        assert full_path.exists(), f"Source file not found: {source_path}"


class TestProviderYamlSchema:
    """Tests for provider YAML schema validation."""
    
    @pytest.fixture
    def provider_yaml(self):
        """Load provider YAML file."""
        yaml_path = Path(__file__).parent.parent.parent / "provider" / "git_datasource.yaml"
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    def test_identity_required_fields(self, provider_yaml):
        """Test identity section has required fields."""
        assert "identity" in provider_yaml
        identity = provider_yaml["identity"]
        
        assert "name" in identity
        assert "author" in identity
        assert "label" in identity
        assert "icon" in identity
        
        # Label must have at least en_US
        assert "en_US" in identity["label"]
    
    def test_provider_type_valid(self, provider_yaml):
        """Test provider_type is valid."""
        assert "provider_type" in provider_yaml
        # website_crawl is the expected type for this plugin
        assert provider_yaml["provider_type"] == "website_crawl"
    
    def test_credentials_schema_valid_types(self, provider_yaml):
        """Test credentials_schema has valid types."""
        if "credentials_schema" not in provider_yaml:
            pytest.skip("No credentials_schema defined")
        
        for i, cred in enumerate(provider_yaml["credentials_schema"]):
            cred_type = cred.get("type")
            # Credentials can use secret-input for sensitive data
            assert cred_type in VALID_PARAMETER_TYPES, (
                f"Credential {i} ({cred.get('name', 'unknown')}) has invalid type '{cred_type}'"
            )
    
    def test_credentials_schema_required_fields(self, provider_yaml):
        """Test credentials_schema has required fields."""
        if "credentials_schema" not in provider_yaml:
            pytest.skip("No credentials_schema defined")
        
        for i, cred in enumerate(provider_yaml["credentials_schema"]):
            cred_name = cred.get("name", f"credential_{i}")
            
            for field in REQUIRED_CREDENTIAL_FIELDS:
                assert field in cred, (
                    f"Credential '{cred_name}' missing required field '{field}'"
                )


class TestManifestYamlSchema:
    """Tests for manifest YAML schema validation."""
    
    @pytest.fixture
    def manifest_yaml(self):
        """Load manifest YAML file."""
        yaml_path = Path(__file__).parent.parent.parent / "manifest.yaml"
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    def test_required_fields(self, manifest_yaml):
        """Test manifest has required fields."""
        required = ["version", "type", "author", "name", "label", "description", "icon"]
        for field in required:
            assert field in manifest_yaml, f"Manifest missing required field '{field}'"
    
    def test_type_is_plugin(self, manifest_yaml):
        """Test type is 'plugin'."""
        assert manifest_yaml["type"] == "plugin"
    
    def test_meta_section(self, manifest_yaml):
        """Test meta section has required fields."""
        assert "meta" in manifest_yaml
        meta = manifest_yaml["meta"]
        
        assert "version" in meta
        assert "arch" in meta
        assert "runner" in meta
        
        runner = meta["runner"]
        assert "language" in runner
        assert "version" in runner
        assert "entrypoint" in runner
    
    def test_plugins_datasources_exist(self, manifest_yaml):
        """Test plugins.datasources references existing files."""
        assert "plugins" in manifest_yaml
        assert "datasources" in manifest_yaml["plugins"]
        
        for ds_path in manifest_yaml["plugins"]["datasources"]:
            full_path = Path(__file__).parent.parent.parent / ds_path
            assert full_path.exists(), f"Datasource file not found: {ds_path}"
    
    def test_storage_permission(self, manifest_yaml):
        """Test storage permission is enabled (required for SHA tracking)."""
        assert "resource" in manifest_yaml
        assert "permission" in manifest_yaml["resource"]
        assert "storage" in manifest_yaml["resource"]["permission"]
        
        storage = manifest_yaml["resource"]["permission"]["storage"]
        assert storage.get("enabled") is True, "Storage permission must be enabled"
