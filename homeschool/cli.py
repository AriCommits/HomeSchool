# src/homeschool/cli.py
"""
Command-line interface for the Homeschool project.
Provides commands for initialization, status checking, log viewing, system reset,
setup, uninstall, version, and shell completions.
"""

import argparse
import os
import platform
import secrets
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .cli_helpers import (
    REPO_ROOT,
    check_docker_available, prompt_yes_no, prompt_choice,
    prompt_path, prompt_token, prompt_database,
    generate_config, start_docker_services, compose_env_from_config,
    export_token_to_downloads, nuke_homeschool_data,
    remove_repository, get_version, check_for_updates,
    get_manifest_dir
)
from .logging import configure_logging, get_logger
from .config import load, ConfigError

logger = get_logger(__name__)


def init_command(args: argparse.Namespace) -> int:
    """Initialize the Homeschool project."""
    logger.info("Initializing Homeschool project")
    
    config_path = Path.cwd() / "config.yaml"
    if config_path.exists() and not args.force:
        logger.error("Configuration file already exists", 
                    config_path=str(config_path),
                    hint="Use --force to overwrite")
        return 1
    
    # Create example configuration
    example_config = """# Homeschool Configuration
# Copy this file to config.yaml and customize the values
 
hardware:
  gpu: "cpu"  # Options: cpu, nvidia, metal
 
network:
  bind_host: "localhost"
  ports:
    chromadb: 8000
 
paths:
  vault: "/path/to/your/obsidian/vault"
  model_store: "/path/to/your/ModelStore"
  manifest_dir: null  # Uses default: ~/.homeschool
 
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
  collection_name: "homeschool"
  distance_metric: "cosine"
  auth_token: "CHANGE_ME"  # Generate with: python3 -c "import secrets; print(secrets.token_hex(32))"
 
sync:
  exclude_patterns:
    - "**/*.tmp"
    - "**/*.log"
    - "**/.git/**"
  prune_deleted: true
  embed_batch_size: 32
 
jan:
  base_url: "http://localhost:1337"
  inference_model: "nemotron-3-super"
  embedding_model: "nomic-embed-text"
"""
    
    try:
        config_path.write_text(example_config)
        logger.info("Created example configuration file", 
                   config_path=str(config_path))
        print(f"Created example configuration at {config_path}")
        print("Please edit this file to set your vault path, model store, and authentication token.")
        return 0
    except Exception as e:
        logger.error("Failed to create configuration file", error=str(e))
        return 1


def status_command(args: argparse.Namespace) -> int:
    """Check the status of the Homeschool system."""
    logger.info("Checking Homeschool system status")
    
    try:
        # Load configuration
        config = load()
        logger.info("Configuration loaded successfully")
        
        # Check Docker services
        import subprocess
        from pathlib import Path
        
        docker_dir = Path(__file__).parent.parent / ".docker"
        if not docker_dir.exists():
            logger.error("Docker directory not found")
            return 1
        
        env = compose_env_from_config(config)
        
        # Check if docker-compose is available
        try:
            result = subprocess.run(
                ["docker", "compose", "ps"],
                cwd=docker_dir,
                capture_output=True,
                text=True,
                check=True,
                env=env
            )
            print("Docker services status:")
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error("Failed to check Docker services", 
                        error=e.stderr)
            return 1
        except FileNotFoundError:
            logger.error("Docker command not found")
            return 1
        
        # Check manifest database
        manifest_dir = config.paths.manifest_dir
        manifest_db = manifest_dir / "manifest.db"
        if manifest_db.exists():
            print(f"Manifest database found at {manifest_db}")
            print(f"Size: {manifest_db.stat().st_size} bytes")
        else:
            print(f"No manifest database found at {manifest_db}")
            
        return 0
        
    except ConfigError as e:
        logger.error("Configuration error", error=str(e))
        return 1
    except Exception as e:
        logger.error("Unexpected error checking status", error=str(e))
        return 1


def logs_command(args: argparse.Namespace) -> int:
    """View recent logs from the Homeschool system."""
    docker_dir = Path(__file__).parent.parent / ".docker"
    if not docker_dir.exists():
        print("Error: Docker directory not found.")
        return 1

    try:
        config = load()
    except ConfigError as e:
        print(f"Error loading config: {e}")
        return 1

    env = compose_env_from_config(config)

    subprocess.run(
        ["docker", "compose", "logs", "--tail=100", "-f"],
        cwd=docker_dir,
        env=env,
    )
    return 0


def reset_command(args: argparse.Namespace) -> int:
    """Reset the Homeschool system to a clean state."""
    logger.info("Resetting Homeschool system")
    
    if not args.confirm:
        logger.error("Reset requires confirmation")
        print("This operation will:")
        print("- Stop all Docker services")
        print("- Remove the manifest database")
        print("- Remove Docker volumes (unless --keep-volumes is specified)")
        print("\nTo proceed, run with --confirm flag")
        return 1
    
    try:
        # Stop Docker services
        import subprocess
        from pathlib import Path

        env = compose_env_from_config()
        
        docker_dir = Path(__file__).parent.parent / ".docker"
        if docker_dir.exists():
            print("Stopping Docker services...")
            subprocess.run(
                ["docker", "compose", "down"],
                cwd=docker_dir,
                check=True,
                env=env,
            )
        
        # Remove manifest database unless --keep-data is specified
        if not args.keep_data:
            config = load()
            manifest_dir = config.paths.manifest_dir
            if manifest_dir.exists():
                import shutil
                print(f"Removing manifest directory: {manifest_dir}")
                shutil.rmtree(manifest_dir)
        
        # Remove Docker volumes unless --keep-volumes is specified
        if not args.keep_volumes and docker_dir.exists():
            print("Removing Docker volumes...")
            subprocess.run(
                ["docker", "compose", "down", "-v"],
                cwd=docker_dir,
                check=True,
                env=env,
            )
        
        print("Reset completed successfully")
        return 0
        
    except Exception as e:
        logger.error("Failed to reset system", error=str(e))
        return 1


def _validate_database_name(database: str) -> bool:
    """
    Validate database name to prevent command injection.
    Only allows alphanumeric characters, hyphens, and underscores.
    """
    import re
    if not database or len(database) > 64:
        return False
    # Strict whitelist: alphanumeric, hyphens, underscores only
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', database))


def setup_command(args: argparse.Namespace) -> int:
    """Interactive setup wizard."""
    print("Welcome to Homeschool Setup!")
    print("This will guide you through initial configuration.\n")
    
    if args.non_interactive:
        choice = "I'll edit config.yaml manually"
    else:
        choice = prompt_choice(
            "Choose setup mode",
            ["Interactive setup (recommended)", "I'll edit config.yaml manually"]
        )

    if choice == "I'll edit config.yaml manually":
        config_path = REPO_ROOT / "config.yaml"
        if not config_path.exists():
            print("\nError: config.yaml not found.")
            print("Run: python -m homeschool init")
            return 1

        print(f"\nUsing config at: {config_path}")

        try:
            load.cache_clear()
            load()
            print("\u2713 config.yaml validation passed")
        except ConfigError as e:
            print(f"Error: config.yaml is invalid:\n{e}")
            return 1

        if args.no_start:
            print("\nNo-start mode enabled. Skipping Docker startup.")
            print("Next: python -m homeschool sync")
            return 0

        print("\nStarting Docker services...")
        if start_docker_services():
            print("\u2713 Docker services started")
            print("\n\u2713 Setup complete! Next: python -m homeschool sync")
            return 0

        print("\u26a0 Docker services could not be started")
        print("  Run 'cd .docker && docker compose up -d' manually")
        return 1

    vault = prompt_path("Obsidian vault path")
    model_store = prompt_path("model store path")
    token = prompt_token()
    database = prompt_database()
    
    print("\nCreating config.yaml...")
    generate_config(vault, model_store, token, database)
    print("✓ Configuration saved")
    
    if not args.no_start:
        print("\nStarting Docker services...")
        if start_docker_services():
            print("✓ Docker services started")
        else:
            print("⚠ Docker services could not be started")
            print("  Run 'cd .docker && docker compose up -d' manually")
    
    print("\n✓ Setup complete! Next: python -m homeschool sync")
    return 0


def uninstall_command(args: argparse.Namespace) -> int:
    """Uninstall Homeschool."""
    print("This will uninstall Homeschool.\n")
    
    # Determine removal level
    if args.keep_data:
        level = 1
    elif args.confirm:
        level = args.confirm
    else:
        level = prompt_choice(
            "Select removal level",
            [
                "Soft uninstall - Keep all data",
                "Full uninstall - Remove data, keep repo",
                "Complete removal - Remove everything"
            ],
            default="Full uninstall - Remove data, keep repo"
        )
        if level.startswith("Soft"):
            level = 1
        elif level.startswith("Full"):
            level = 2
        else:
            level = 3
    
    # Get current token for export prompt
    token = None
    if level >= 2:
        try:
            config = load()
            token = config.chromadb.auth_token
        except:
            pass
        
        if token and prompt_yes_no("Export ChromaDB token before deletion?"):
            backup_path = export_token_to_downloads(token)
            print(f"✓ Token saved to: {backup_path}")
    
    # Execute removal
    print("\nRemoving Homeschool data...")
    results = nuke_homeschool_data()
    
    if level >= 3:
        print("\nRemoving repository...")
        if args.remove_git is None:
            remove_git = prompt_yes_no("Delete .git directory?", default=False)
        else:
            remove_git = args.remove_git
        remove_repository(include_git=remove_git)
    
    print("\n✓ Uninstall complete!")
    return 0


def version_command(args: argparse.Namespace) -> int:
    """Show version information."""
    current = get_version()
    print(f"Homeschool version: {current}")
    
    update_available, latest = check_for_updates()
    if update_available:
        print(f"⚠ Update available: {latest}")
        print(f"  Run: pip install --upgrade homeschool")
    else:
        print("✓ You have the latest version")
    
    return 0


def completions_command(args: argparse.Namespace) -> int:
    """Install shell completions."""
    shell = args.shell
    
    completions_dir = REPO_ROOT / "completions"
    install_path = None
    
    if shell == "bash":
        content = (completions_dir / "bash" / "homeschool").read_text()
        dest = Path.home() / ".bash_completions" / "homeschool"
        dest.parent.mkdir(exist_ok=True)
        dest.write_text(content)
        print(f"✓ Installed bash completions to: {dest}")
        print("  Add to ~/.bashrc: source ~/.bash_completions/homeschool")
    
    elif shell == "zsh":
        content = (completions_dir / "zsh" / "_homeschool").read_text()
        dest = Path.home() / ".zsh_completions" / "_homeschool"
        dest.parent.mkdir(exist_ok=True)
        dest.write_text(content)
        print(f"✓ Installed zsh completions to: {dest}")
        print("  Add to ~/.zshrc: fpath+=(~/.zsh_completions) && compinit")
    
    elif shell == "powershell":
        content = (completions_dir / "powershell" / "homeschool.ps1").read_text()
        dest = Path.home() / "Documents" / "PowerShell" / "homeschool.ps1"
        dest.parent.mkdir(exist_ok=True)
        dest.write_text(content)
        print(f"✓ Installed PowerShell completions to: {dest}")
        print("  Add to $PROFILE: . ~/Documents/PowerShell/homeschool.ps1")
    
    return 0


def sync_command(args: argparse.Namespace) -> int:
    """Manually trigger synchronization process."""
    
    # Validate database name before use (Security: prevent command injection)
    if not _validate_database_name(args.database):
        logger.error("Invalid database name - must be alphanumeric with hyphens/underscores only",
                     database=args.database)
        print(f"Error: Invalid database name '{args.database}'.")
        print("Database names can only contain letters, numbers, hyphens, and underscores.")
        return 1
    
    logger.info("Starting manual sync process", database=args.database)
    
    # Load configuration to validate database exists
    try:
        config = load()
        if args.database not in config.databases:
            logger.error("Database not found in configuration", 
                        database=args.database,
                        available_databases=list(config.databases.keys()))
            print(f"Error: Database '{args.database}' not found in configuration.")
            print(f"Available databases: {', '.join(config.databases.keys())}")
            return 1
    except Exception as e:
        logger.error("Failed to load configuration", error=str(e))
        return 1
    
    # Change to the .docker directory where docker-compose is located
    import subprocess
    from pathlib import Path
    
    docker_dir = Path(__file__).parent.parent / ".docker"
    
    if not docker_dir.exists():
        logger.error("Docker directory not found", docker_dir=str(docker_dir))
        return 1
    
    # Set environment variables for docker-compose
    # Security Note: Tokens in environment variables are visible via /proc
    # This is a known limitation of container orchestration
    env = compose_env_from_config(config)
    env.update(
        {
            "SYNC_DATABASE": args.database,
            "FORCE_REGEN": "1" if args.force_regen else "0",
        }
    )
    
    # Run docker compose to start the sync worker
    try:
        # Step 1: Ensure ChromaDB is running
        logger.info("Ensuring ChromaDB is running", docker_dir=str(docker_dir))
        subprocess.run(
            ["docker", "compose", "up", "-d", "chromadb"],
            cwd=docker_dir,
            check=True,
            env=env,
        )

        # Step 2: Wait for ChromaDB to be healthy (up to 30 seconds)
        logger.info("Waiting for ChromaDB to be healthy")
        for _ in range(30):
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json", "chromadb"],
                cwd=docker_dir,
                capture_output=True,
                text=True,
                env=env,
            )
            if '"healthy"' in result.stdout or '"running"' in result.stdout:
                break
            import time

            time.sleep(1)
        else:
            print("Error: ChromaDB did not become healthy within 30 seconds.")
            print("Check logs with: docker compose -f .docker/compose.yaml logs chromadb")
            return 1

        # Step 3: Run sync worker with live streaming output
        logger.info("Running sync worker", docker_dir=str(docker_dir))
        subprocess.run(
            ["docker", "compose", "run", "--rm", "sync_worker"],
            cwd=docker_dir,
            check=True,
            env=env,
        )
        logger.info("Sync completed successfully")
        return 0
    except subprocess.CalledProcessError as e:
        logger.error("Sync failed", exit_code=e.returncode)
        print(f"Sync failed with exit code {e.returncode}")
        print("Run 'homeschool status' for diagnostics.")
        return e.returncode
    except FileNotFoundError:
        logger.error("Docker command not found")
        print("Error: Docker is not installed or not on PATH.")
        return 1


def main() -> int:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Homeschool - Personal Knowledge Management System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  homeschool init          # Create initial configuration
  homeschool setup        # Interactive setup wizard
  homeschool sync          # Sync notes to Anki
  homeschool status        # Check system status
  homeschool logs          # View log instructions
  homeschool reset         # Reset system (requires confirmation)
  homeschool version       # Show version and check for updates
  homeschool uninstall     # Uninstall Homeschool
        """
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Path to log file (if not set, logs go to stdout)"
    )
    
    parser.add_argument(
        "--json-logs",
        action="store_true",
        help="Output logs in JSON format"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize Homeschool configuration")
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing configuration file"
    )
    init_parser.set_defaults(func=init_command)
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check system status")
    status_parser.set_defaults(func=status_command)
    
    # Logs command
    logs_parser = subparsers.add_parser("logs", help="View log instructions")
    logs_parser.set_defaults(func=logs_command)
    
    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset system to clean state")
    reset_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm that you want to reset the system"
    )
    reset_parser.add_argument(
        "--keep-data",
        action="store_true",
        help="Keep manifest data when resetting"
    )
    reset_parser.add_argument(
        "--keep-volumes",
        action="store_true",
        help="Keep Docker volumes when resetting"
    )
    reset_parser.set_defaults(func=reset_command)
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Interactive setup wizard")
    setup_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip interactive prompts"
    )
    setup_parser.add_argument(
        "--no-start",
        action="store_true",
        help="Create config but don't start Docker"
    )
    setup_parser.set_defaults(func=setup_command)
    
    # Uninstall command
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall Homeschool")
    uninstall_parser.add_argument(
        "--confirm",
        type=int,
        choices=[1, 2, 3],
        metavar="LEVEL",
        help="Uninstall level: 1=soft, 2=full, 3=complete"
    )
    uninstall_parser.add_argument(
        "--keep-data",
        action="store_true",
        help="Skip data removal (same as --confirm 1)"
    )
    uninstall_parser.add_argument(
        "--remove-repo",
        action="store_true",
        help="Also remove repository directory"
    )
    uninstall_parser.add_argument(
        "--remove-git",
        action="store_true",
        help="Include .git in repository removal"
    )
    uninstall_parser.set_defaults(func=uninstall_command)
    
    # Version command
    version_parser = subparsers.add_parser("version", help="Show version info")
    version_parser.set_defaults(func=version_command)
    
    # Completions command
    comp_parser = subparsers.add_parser("completions", help="Install shell completions")
    comp_parser.add_argument(
        "shell",
        choices=["bash", "zsh", "powershell"],
        help="Shell type"
    )
    comp_parser.set_defaults(func=completions_command)
    
    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Manually trigger synchronization")
    sync_parser.add_argument(
        "--database",
        type=str,
        default="default",
        help="Specify which database to sync to (default: default)"
    )
    sync_parser.add_argument(
        "--force-regen",
        action="store_true",
        help="Force regeneration of all flashcards, bypassing change detection"
    )
    sync_parser.set_defaults(func=sync_command)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Configure logging
    configure_logging(
        log_level=args.log_level,
        log_file=args.log_file,
        json_logs=args.json_logs
    )
    
    # Handle no command case
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    try:
        return args.func(args)
    except Exception as e:
        logger.error("Command failed", error=str(e), exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
