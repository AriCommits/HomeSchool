#!/usr/bin/env python3
"""
Manual sync command for Homeschool project.
Run with: python -m homeschool sync
"""

import subprocess
import sys
import signal
from pathlib import Path
from .logging import configure_logging, get_logger

# Configure logging
configure_logging(log_level="INFO")
logger = get_logger(__name__)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal", signal=signum)
    sys.exit(0)

def main():
    """Main entry point for the sync command."""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    logger.info("Starting manual sync process")
    
    # Change to the .docker directory where docker-compose is located
    docker_dir = Path(__file__).parent.parent / ".docker"
    
    if not docker_dir.exists():
        logger.error("Docker directory not found", docker_dir=str(docker_dir))
        sys.exit(1)
    
    # Run docker compose to start the sync worker
    try:
        logger.info("Running docker compose", docker_dir=str(docker_dir))
        result = subprocess.run(
            ["docker", "compose", "run", "--rm", "sync_worker"],
            cwd=docker_dir,
            check=True
        )
        logger.info("Sync completed successfully")
    except subprocess.CalledProcessError as e:
        logger.error("Sync failed", exit_code=e.returncode)
        sys.exit(e.returncode)
    except FileNotFoundError:
        logger.error("Docker command not found")
        sys.exit(1)

if __name__ == "__main__":
    main()