import argparse
from pathlib import Path

import yaml

import homeschool.cli as cli_module
import homeschool.config as config_module


def _write_config(config_path: Path, temp_dir: Path, auth_token: str = "test_token_12345678901234567890") -> None:
    vault_path = temp_dir / "vault"
    model_path = temp_dir / "models"
    manifest_path = temp_dir / "manifest"
    vault_path.mkdir(exist_ok=True)
    model_path.mkdir(exist_ok=True)
    manifest_path.mkdir(exist_ok=True)

    config_data = {
        "hardware": {"gpu": "cpu"},
        "network": {"bind_host": "localhost", "ports": {"chromadb": 8000}},
        "paths": {
            "vault": str(vault_path),
            "model_store": str(model_path),
            "manifest_dir": str(manifest_path),
        },
        "embedding": {
            "model_file": "test.gguf",
            "n_ctx": 512,
            "n_gpu_layers": 0,
            "split_headers": ["#"],
            "embed_batch_size": 32,
        },
        "chromadb": {
            "collection_name": "test",
            "distance_metric": "cosine",
            "auth_token": auth_token,
        },
        "sync": {
            "exclude_patterns": ["*.tmp"],
            "prune_deleted": True,
            "embed_batch_size": 32,
        },
        "jan": {
            "base_url": "http://localhost:1337",
            "inference_model": "test",
            "embedding_model": "test",
        },
    }

    config_path.write_text(yaml.dump(config_data))


def test_setup_manual_no_start_validates_and_skips_docker(temp_dir, monkeypatch, capsys):
    config_path = temp_dir / "config.yaml"
    _write_config(config_path, temp_dir)

    monkeypatch.setattr(cli_module, "REPO_ROOT", temp_dir)
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)
    monkeypatch.setattr(
        cli_module,
        "prompt_choice",
        lambda *args, **kwargs: "I'll edit config.yaml manually",
    )

    def _unexpected_start() -> bool:
        raise AssertionError("start_docker_services should not be called with --no-start")

    monkeypatch.setattr(cli_module, "start_docker_services", _unexpected_start)

    config_module.load.cache_clear()
    try:
        args = argparse.Namespace(non_interactive=False, no_start=True)
        result = cli_module.setup_command(args)
    finally:
        config_module.load.cache_clear()

    output = capsys.readouterr().out
    assert result == 0
    assert "config.yaml validation passed" in output
    assert "No-start mode enabled. Skipping Docker startup." in output


def test_setup_manual_no_start_fails_on_invalid_config(temp_dir, monkeypatch, capsys):
    config_path = temp_dir / "config.yaml"
    _write_config(config_path, temp_dir, auth_token="CHANGE_ME")

    monkeypatch.setattr(cli_module, "REPO_ROOT", temp_dir)
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)
    monkeypatch.setattr(
        cli_module,
        "prompt_choice",
        lambda *args, **kwargs: "I'll edit config.yaml manually",
    )

    config_module.load.cache_clear()
    try:
        args = argparse.Namespace(non_interactive=False, no_start=True)
        result = cli_module.setup_command(args)
    finally:
        config_module.load.cache_clear()

    output = capsys.readouterr().out
    assert result == 1
    assert "config.yaml is invalid" in output
