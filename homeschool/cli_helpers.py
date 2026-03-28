# src/homeschool/cli_helpers.py
"""
Helper functions for Homeschool CLI commands.
All functions use pathlib exclusively and avoid os where possible.
"""

import secrets
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────────────────────
# Path Management
# ─────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent
DOCKER_DIR = REPO_ROOT / ".docker"
DEFAULT_MANIFEST_DIR = Path.home() / ".homeschool"


def get_repo_root() -> Path:
    """Return repository root directory."""
    return REPO_ROOT


def get_docker_dir() -> Path:
    """Return .docker directory."""
    return DOCKER_DIR


def get_manifest_dir() -> Path:
    """Return manifest directory, creating if needed."""
    manifest = DEFAULT_MANIFEST_DIR
    manifest.mkdir(parents=True, exist_ok=True)
    return manifest


# ─────────────────────────────────────────────────────────────
# User Interaction
# ─────────────────────────────────────────────────────────────

def prompt_yes_no(question: str, default: bool = False) -> bool:
    """Ask yes/no question, return boolean."""
    options = "[Y/n]" if default else "[y/N]"
    while True:
        response = input(f"{question} {options}: ").strip().lower()
        if not response:
            return default
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'")


def prompt_choice(question: str, options: list[str], default: Optional[str] = None) -> str:
    """Present numbered options, return selection."""
    for i, opt in enumerate(options, 1):
        marker = " ← default" if opt == default else ""
        print(f"  [{i}] {opt}{marker}")
    
    while True:
        response = input(f"{question}: ").strip()
        if not response and default is not None:
            return default
        try:
            idx = int(response) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        print(f"Please enter a number 1-{len(options)}")
    
    # This line should never be reached, but added for type checker
    return options[0]


def prompt_path(description: str, validate: bool = True) -> Path:
    """Prompt for path with optional validation."""
    while True:
        path_str = input(f"Enter {description}: ").strip()
        if not path_str:
            print("Path cannot be empty.")
            continue
        
        path = Path(path_str).expanduser().resolve()
        
        if validate and not path.exists():
            if not prompt_yes_no(f"Path '{path}' doesn't exist. Continue?"):
                continue
        
        return path


def prompt_token() -> str:
    """Prompt for or generate ChromaDB token."""
    if prompt_yes_no("Auto-generate a secure ChromaDB token?"):
        token = secrets.token_hex(32)
        print(f"Generated token: {token}")
        return token
    
    while True:
        token = input("Enter ChromaDB auth token (64 hex chars): ").strip()
        if len(token) == 64 and all(c in "0123456789abcdef" for c in token.lower()):
            return token.lower()
        print("Invalid token. Must be 64 hexadecimal characters.")


def prompt_database() -> str:
    """Prompt for database selection."""
    options = ["default", "essay", "homework"]
    return prompt_choice(
        "Select database",
        options,
        default="default"
    )


# ─────────────────────────────────────────────────────────────
# Docker Operations
# ─────────────────────────────────────────────────────────────

def check_docker_available() -> bool:
    """Check if Docker is installed and running."""
    try:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def start_docker_services() -> bool:
    """Start Docker services via docker compose."""
    try:
        subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=DOCKER_DIR,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


def stop_docker_services() -> bool:
    """Stop Docker services."""
    try:
        subprocess.run(
            ["docker", "compose", "down"],
            cwd=DOCKER_DIR,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


def remove_docker_volumes() -> bool:
    """Remove Docker volumes (ChromaDB data)."""
    try:
        subprocess.run(
            ["docker", "compose", "down", "-v"],
            cwd=DOCKER_DIR,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


# ─────────────────────────────────────────────────────────────
# Config Management
# ─────────────────────────────────────────────────────────────

def generate_config(vault: Path, model_store: Path, token: str, db: str) -> None:
    """Generate config.yaml with user values."""
    config_content = f"""# Homeschool Configuration
# Generated by: python -m homeschool setup

hardware:
  gpu: "cpu"

network:
  bind_host: "localhost"
  ports:
    chromadb: 8000

paths:
  vault: "{vault}"
  model_store: "{model_store}"
  manifest_dir: null

embedding:
  model_file: "nomic-embed-text-v1.5.Q4_K_M.gguf"
  n_ctx: 512
  n_gpu_layers: 32
  split_headers:
    - "#"
    - "##"
    - "###"
  embed_batch_size: 32

chromadb:
  collection_name: "mcat"
  distance_metric: "cosine"
  auth_token: "{token}"

databases:
  default:
    vault_subpath: ""
    collection: "homeschool"
  essay:
    vault_subpath: "essays"
    collection: "essay_collection"
  homework:
    vault_subpath: "homework"
    collection: "homework_collection"

sync:
  exclude_patterns:
    - "**/*.tmp"
    - "**/*.log"
    - "**/.git/**"
  prune_deleted: true
  embed_batch_size: 32

jan:
  base_url: "http://localhost:1337/v1"
  inference_model: "Jan-v3.5-4B-Q4_K_XL"
  embedding_model: "Nomic_embedding"
"""
    (REPO_ROOT / "config.yaml").write_text(config_content)


# ─────────────────────────────────────────────────────────────
# Uninstall Operations
# ─────────────────────────────────────────────────────────────

def export_token_to_downloads(token: str) -> Optional[Path]:
    """Export ChromaDB token to Downloads folder."""
    downloads = Path.home() / "Downloads"
    
    # Fallback for Linux/other platforms
    if not downloads.exists():
        downloads = Path.home()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = downloads / f"homeschool_token_backup_{timestamp}.txt"
    
    content = f"""Homeschool ChromaDB Token Backup
================================
Generated: {datetime.now().isoformat()}
Repository: {REPO_ROOT}

This token will no longer be valid after uninstalling Homeschool.

TOKEN:
{token}
"""
    backup_file.write_text(content)
    return backup_file


def nuke_homeschool_data() -> dict[str, bool]:
    """Remove all data created by Homeschool CLI."""
    results = {}
    
    # 1. Docker volumes
    results["docker_volumes"] = remove_docker_volumes()
    
    # 2. Manifest database
    manifest = get_manifest_dir()
    if manifest.exists():
        shutil.rmtree(manifest, ignore_errors=True)
    results["manifest_db"] = manifest.exists()
    
    # 3. Config files
    for filename in ["config.yaml", ".env"]:
        config_path = REPO_ROOT / filename
        if config_path.exists():
            config_path.unlink()
    results["config"] = (REPO_ROOT / "config.yaml").exists()
    
    return results


def remove_repository(include_git: bool = False) -> None:
    """Remove repository directory."""
    if not include_git:
        # Remove everything except .git
        for item in REPO_ROOT.iterdir():
            if item.name == ".git":
                continue
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
    else:
        shutil.rmtree(REPO_ROOT, ignore_errors=True)


# ─────────────────────────────────────────────────────────────
# Version & Updates
# ─────────────────────────────────────────────────────────────

def get_version() -> str:
    """Get current Homeschool version."""
    version_file = REPO_ROOT / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    
    # Fallback to git tag or "unknown"
    try:
        result = subprocess.run(
            ["git", "describe", "--tags"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    
    return "0.1.0"  # Default version


def check_for_updates() -> tuple[bool, Optional[str]]:
    """Check if updates are available. Returns (update_available, latest_version)."""
    try:
        # Fetch latest tag from GitHub
        result = subprocess.run(
            ["git", "ls-remote", "--tags", "https://github.com/anomalyco/HomeSchool.git"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            tags = [line.split("refs/tags/")[1] for line in result.stdout.split("\n") if "refs/tags/" in line]
            if tags:
                latest = max(tags)
                current = get_version()
                return (latest != current, latest)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return (False, None)