# src/homeschool/cli.py
"""
Command-line interface for the Homeschool project.
Provides commands for initialization, status checking, log viewing, and system reset.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

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
  manifest_dir: null  # Uses default: ~/.sovereign_brain/manifest

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
        
        # Set environment variables for docker-compose
        env = os.environ.copy()
        env.update({
            "CHROMA_TOKEN": config.chromadb.auth_token,
            "VAULT_PATH": str(config.paths.vault),
            "MODEL_STORE": str(config.paths.model_store)
        })
        
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
    logger.info("Displaying recent logs")
    
    # For now, just show instructions since we don't have centralized logging yet
    print("To view logs:")
    print("1. Docker service logs: docker compose -f .docker/compose.yaml logs -f")
    print("2. Application logs: Check stdout/stderr when running commands")
    print("3. Transaction logs: Check the manifest database for sync history")
    
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
        
        docker_dir = Path(__file__).parent.parent / ".docker"
        if docker_dir.exists():
            print("Stopping Docker services...")
            subprocess.run(
                ["docker", "compose", "down"],
                cwd=docker_dir,
                check=True
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
                check=True
            )
            
        print("Reset completed successfully")
        return 0
        
    except Exception as e:
        logger.error("Failed to reset system", error=str(e))
        return 1


def main() -> int:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Homeschool - Personal Knowledge Management System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  homeschool init          # Create initial configuration
  homeschool status        # Check system status
  homeschool logs          # View log instructions
  homeschool reset         # Reset system (requires confirmation)
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