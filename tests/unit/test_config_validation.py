"""
Unit tests for configuration validation.
"""

import pytest
import tempfile
import yaml
import os
from pathlib import Path
from unittest.mock import patch


def create_test_config(temp_dir, **overrides):
    """Create a test configuration with required fields."""
    vault_path = temp_dir / "vault"
    vault_path.mkdir()
    
    model_path = temp_dir / "models"
    model_path.mkdir()
    
    manifest_path = temp_dir / "manifest"
    manifest_path.mkdir()
    
    default_config = {
        "hardware": {"gpu": "cpu"},
        "network": {"bind_host": "localhost", "ports": {"chromadb": 8000}},
        "paths": {
            "vault": str(vault_path),
            "model_store": str(model_path),
            "manifest_dir": str(manifest_path)
        },
        "embedding": {
            "model_file": "test.gguf",
            "n_ctx": 512,
            "n_gpu_layers": 0,
            "split_headers": ["#"],
            "embed_batch_size": 32
        },
        "chromadb": {
            "collection_name": "test",
            "distance_metric": "cosine",
            "auth_token": "test_token_12345678901234567890"
        },
        "sync": {
            "exclude_patterns": ["*.tmp"],
            "prune_deleted": True,
            "embed_batch_size": 32
        },
        "jan": {
            "base_url": "http://localhost:1337",
            "inference_model": "test",
            "embedding_model": "test"
        }
    }
    
    for key, value in overrides.items():
        if key in default_config and isinstance(default_config[key], dict):
            default_config[key].update(value)
        else:
            default_config[key] = value
    
    return default_config


class TestGPUValidation:
    """Tests for GPU configuration validation."""

    def test_valid_gpu_cpu(self, temp_dir):
        """Test that valid GPU 'cpu' is accepted."""
        from homeschool.config import Config
        config_data = create_test_config(temp_dir, hardware={"gpu": "cpu"})
        config = Config(config_data)
        assert config.hardware.gpu == "cpu"

    def test_valid_gpu_nvidia(self, temp_dir):
        """Test that valid GPU 'nvidia' is accepted."""
        from homeschool.config import Config
        config_data = create_test_config(temp_dir, hardware={"gpu": "nvidia"})
        config = Config(config_data)
        assert config.hardware.gpu == "nvidia"

    def test_valid_gpu_metal(self, temp_dir):
        """Test that valid GPU 'metal' is accepted."""
        from homeschool.config import Config
        config_data = create_test_config(temp_dir, hardware={"gpu": "metal"})
        config = Config(config_data)
        assert config.hardware.gpu == "metal"

    def test_invalid_gpu_raises(self, temp_dir):
        """Test that invalid GPU values raise ConfigError."""
        from homeschool.config import Config, ConfigError
        config_data = create_test_config(temp_dir, hardware={"gpu": "invalid_gpu"})
        with pytest.raises(ConfigError) as exc_info:
            Config(config_data)
        assert "gpu" in str(exc_info.value).lower()


class TestAuthTokenValidation:
    """Tests for authentication token validation."""

    def test_default_token_raises(self, temp_dir):
        """Test that default chromadb auth token raises ConfigError."""
        from homeschool.config import Config, ConfigError
        config_data = create_test_config(temp_dir, chromadb={"auth_token": "CHANGE_ME"})
        with pytest.raises(ConfigError) as exc_info:
            Config(config_data)
        assert "CHANGE_ME" in str(exc_info.value) or "default" in str(exc_info.value).lower()


class TestDistanceMetric:
    """Tests for ChromaDB distance metric."""

    def test_cosine_metric(self, temp_dir):
        """Test that cosine distance metric is correctly stored."""
        from homeschool.config import Config
        config_data = create_test_config(temp_dir, chromadb={"distance_metric": "cosine"})
        config = Config(config_data)
        assert config.chromadb.distance_metric == "cosine"

    def test_euclidean_metric(self, temp_dir):
        """Test that euclidean distance metric is loaded."""
        from homeschool.config import Config
        config_data = create_test_config(temp_dir, chromadb={"distance_metric": "euclidean"})
        config = Config(config_data)
        assert config.chromadb.distance_metric == "euclidean"


class TestSyncConfig:
    """Tests for sync configuration."""

    def test_exclude_patterns(self, temp_dir):
        """Test that sync exclude patterns are correctly loaded."""
        from homeschool.config import Config
        exclude = ["**/*.tmp", "**/*.log", "**/.git/**"]
        config_data = create_test_config(temp_dir, sync={"exclude_patterns": exclude})
        config = Config(config_data)
        assert config.sync.exclude_patterns == exclude

    def test_prune_deleted(self, temp_dir):
        """Test that prune_deleted setting is correctly loaded."""
        from homeschool.config import Config
        config_data = create_test_config(temp_dir, sync={"prune_deleted": False})
        config = Config(config_data)
        assert config.sync.prune_deleted is False


class TestDatabasesConfig:
    """Tests for databases configuration (plan_05 feature)."""

    def test_default_database(self, temp_dir):
        """Test that default database is available."""
        from homeschool.config import Config
        config_data = create_test_config(temp_dir)
        config = Config(config_data)
        assert "default" in config.databases

    def test_multiple_databases(self, temp_dir):
        """Test that multiple databases can be configured."""
        from homeschool.config import Config
        databases = {
            "default": {"vault_subpath": "", "collection": "homeschool"},
            "essay": {"vault_subpath": "essays", "collection": "essay_collection"},
            "homework": {"vault_subpath": "homework", "collection": "homework_collection"}
        }
        config_data = create_test_config(temp_dir, databases=databases)
        config = Config(config_data)
        assert config.databases["essay"]["vault_subpath"] == "essays"
        assert config.databases["essay"]["collection"] == "essay_collection"
        assert config.databases["homework"]["vault_subpath"] == "homework"

    def test_default_database_fallback(self, temp_dir):
        """Test that missing databases section uses defaults."""
        from homeschool.config import Config
        config_data = create_test_config(temp_dir)
        config_data.pop("databases", None)
        config = Config(config_data)
        assert "default" in config.databases
        assert config.databases["default"]["collection"] == "test"
