import pytest
import tempfile
import shutil
from pathlib import Path
import yaml
from homeschool.config import load


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_vault(temp_dir):
    """Create a sample Obsidian vault structure."""
    vault_path = temp_dir / "vault"
    vault_path.mkdir()
    
    # Create sample notes
    (vault_path / "note1.md").write_text("""---
deck: "Test::Deck"
tags: [test, sample]
---

What is the capital of France?::Paris

This is a sample note for testing.
""")
    
    (vault_path / "note2.md").write_text("""# Another Note

This note has ==cloze deletion== and some other content.

- Bullet point 1
- Bullet point 2

What is 2+2?::4
""")
    
    return vault_path


@pytest.fixture
def sample_config(temp_dir, sample_vault):
    """Create a sample configuration for testing."""
    config_data = {
        "hardware": {
            "gpu": "cpu"
        },
        "network": {
            "bind_host": "localhost",
            "ports": {
                "chromadb": 8000
            }
        },
        "paths": {
            "vault": str(sample_vault),
            "model_store": str(temp_dir / "models"),
            "manifest_dir": str(temp_dir / "manifest")
        },
        "embedding": {
            "model_file": "test-model.gguf",
            "n_ctx": 512,
            "n_gpu_layers": 0,
            "split_headers": ["#", "##"],
            "embed_batch_size": 32
        },
        "chromadb": {
            "collection_name": "test_collection",
            "distance_metric": "cosine",
            "auth_token": "test-token"
        },
        "sync": {
            "exclude_patterns": ["*.tmp", "Temp*"],
            "prune_deleted": True,
            "embed_batch_size": 32
        },
        "jan": {
            "base_url": "http://localhost:1337",
            "inference_model": "test-model",
            "embedding_model": "test-embed-model"
        }
    }
    
    config_path = temp_dir / "config.yaml"
    config_path.write_text(yaml.dump(config_data))
    
    # Temporarily override the config path
    import homeschool.config
    original_config_path = homeschool.config.CONFIG_PATH
    homeschool.config.CONFIG_PATH = config_path
    
    yield homeschool.config.load()
    
    # Restore original config path
    homeschool.config.CONFIG_PATH = original_config_path


@pytest.fixture
def anki_connect_mock():
    """Mock AnkiConnect responses."""
    return {
        "addNote": {"result": 1234567890},
        "updateNoteFields": {"result": True},
        "deleteNotes": {"result": True},
        "findNotes": {"result": [1, 2, 3]},
        "getDeckNames": {"result": ["Test::Deck", "Another::Deck"]},
        "modelNames": {"result": ["Basic", "Cloze"]},
        "storeMediaFile": {"result": "image.png"}
    }