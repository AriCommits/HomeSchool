#!/usr/bin/env python3
"""
Manual sync command for Homeschool project.
Run with: python -m homeschool sync
"""

import os
import sys
import signal
from datetime import datetime
from pathlib import Path

from .logging import configure_logging, get_logger
from .config import load, ConfigError
from .path_security import is_path_within_directory
from .apkg_exporter import export_apkg, ApkgExportError

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
    
    try:
        # Load configuration (from /app/config.yaml in the container, which is mounted from the host)
        config = load()
        logger.info("Configuration loaded successfully")
        
        # Get database name from environment (defaults to "default")
        database_name = os.environ.get("SYNC_DATABASE", "default")
        logger.info("Selected database", database=database_name)
        
        # Validate database exists in configuration
        if database_name not in config.databases:
            logger.error("Database not found in configuration", 
                        database=database_name,
                        available_databases=list(config.databases.keys()))
            sys.exit(1)
        
        # Get database configuration
        db_config = config.databases[database_name]
        vault_subpath = db_config.get("vault_subpath", "")
        collection_name = db_config.get("collection", "homeschool")
        
        logger.info("Database configuration", 
vault_subpath=vault_subpath,
                    collection=collection_name)
        
        # Calculate sync directory with path traversal protection
        vault_path = config.paths.vault
        if vault_subpath:
            sync_directory = (vault_path / vault_subpath).resolve()
        else:
            sync_directory = vault_path.resolve()
        
        # Security: Validate resolved path is within vault bounds
        vault_resolved = vault_path.resolve()
        if not is_path_within_directory(sync_directory, vault_resolved):
            logger.error("Path traversal attempt detected", 
                        requested=str(sync_directory),
                        vault=str(vault_resolved))
            print(f"Error: Invalid vault_subpath - path traversal not allowed")
            sys.exit(1)
        
        logger.info("Sync directory", path=str(sync_directory))
        
        # Import ChromaDB client
        try:
            import chromadb
        except ImportError:
            logger.error("ChromaDB client not available")
            sys.exit(1)
        
        # Connect to ChromaDB server
        host = os.environ.get("CHROMA_HOST", "chromadb")
        port = int(os.environ.get("CHROMA_PORT", "8000"))
        
        logger.info("Connecting to ChromaDB", host=host, port=port)
        client = chromadb.HttpClient(
            host=host,
            port=port,
        )
        
        # Test connection
        try:
            client.heartbeat()
            logger.info("Connected to ChromaDB successfully")
        except Exception as e:
            logger.error("Failed to connect to ChromaDB", error=str(e))
            sys.exit(1)
        
        # Get or create collection
        try:
            collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": config.chromadb.distance_metric}
            )
            logger.info("Using collection", name=collection_name, count=collection.count())
        except Exception as e:
            logger.error("Failed to get/create collection", error=str(e))
            sys.exit(1)

        force_regen = os.environ.get("FORCE_REGEN", "0") == "1"
        if force_regen:
            try:
                logger.info("Force regeneration enabled; clearing collection before sync", collection=collection_name)
                collection.delete(where={})
            except Exception as e:
                logger.error("Failed to clear collection for force regeneration", error=str(e))
                sys.exit(1)
        
        # Walk the sync directory for markdown files, excluding patterns
        exclude_patterns = config.sync.exclude_patterns
        prune_deleted = config.sync.prune_deleted  # We are not implementing pruning in this version
        
        logger.info("Scanning for markdown files", 
                   directory=str(sync_directory),
                   exclude_patterns=exclude_patterns)
        
        # Security: Don't follow symlinks to prevent directory traversal attacks
        files_to_process = []
        for root, dirs, files in os.walk(sync_directory, followlinks=False):
            # Security: Check that root is within sync_directory (prevent symlink escapes)
            root_path = Path(root).resolve()
            if not is_path_within_directory(root_path, sync_directory):
                logger.warning("Skipping directory outside sync scope", path=str(root_path))
                dirs.clear()  # Don't descend into this directory
                continue
            
            # Skip symlinked directories
            dirs[:] = [d for d in dirs if not (Path(root) / d).is_symlink()]
            
            # Process files
            for file in files:
                if file.endswith(".md"):
                    file_path = Path(root) / file
                    
                    # Security: Skip symlinked files to prevent symlink attacks
                    if file_path.is_symlink():
                        logger.warning("Skipping symlinked file", path=str(file_path))
                        continue
                    
                    # Check if the file matches any exclude pattern
                    excluded = False
                    for pattern in exclude_patterns:
                        # Simple wildcard matching: we only support suffix matching for simplicity
                        if pattern.endswith('*'):
                            if file_path.name.startswith(pattern[:-1]):
                                excluded = True
                                break
                        elif pattern == file_path.name:
                            excluded = True
                            break
                    if not excluded:
                        files_to_process.append(file_path)
        
        logger.info("Found files to process", count=len(files_to_process))
        
        # Process files and add them to ChromaDB
        # For each file, we would:
        # 1. Read the markdown content
        # 2. Extract frontmatter (for metadata like deck, tags)
        # 3. Parse the content into flashcards
        # 4. Generate embeddings for the cards
        # 5. Add to ChromaDB collection
        
        logger.info("Processing files for ChromaDB storage")
        
        # Initialize sentence transformer for embeddings (lighter alternative to llama-cpp for embeddings)
        try:
            from sentence_transformers import SentenceTransformer
            embedder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Initialized sentence transformer for embeddings")
        except ImportError:
            logger.warning("sentence-transformers not available, using simple hash-based embeddings for demo")
            embedder = None
        
        # Process each file
        processed_count = 0
        cards_for_export = []
        for file_path in files_to_process:
            try:
                logger.info("Processing file", file=str(file_path))
                
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract frontmatter (simple implementation)
                frontmatter = {}
                main_content = content
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        frontmatter_text = parts[1]
                        main_content = parts[2]
                        # Parse simple key:value pairs
                        for line in frontmatter_text.strip().split('\n'):
                            if ':' in line:
                                key, value = line.split(':', 1)
                                frontmatter[key.strip()] = value.strip()
                
                logger.info("File frontmatter", frontmatter=frontmatter)
                
                # Security: Limit content size before processing
                MAX_CONTENT_LENGTH = 1000000  # 1MB per note
                MAX_QUESTION_LENGTH = 1000
                MAX_ANSWER_LENGTH = 5000
                if len(content) > MAX_CONTENT_LENGTH:
                    logger.warning("Note too large, skipping", file=str(file_path), size=len(content))
                    continue
                
                # Simple flashcard extraction (look for :: patterns)
                import re
                # Pattern for flashcards: question::answer
                flashcard_pattern = r'(.+?)::(.+?)(?=\n(?:\w+::|\Z))'
                matches = re.findall(flashcard_pattern, main_content, re.DOTALL)
                
                flashcards = []
                for match in matches:
                    question = match[0].strip()
                    answer = match[1].strip()
                    # Security: Validate flashcard content length
                    if len(question) > MAX_QUESTION_LENGTH:
                        logger.warning("Question too long, truncating", question=question[:50])
                        question = question[:MAX_QUESTION_LENGTH]
                    if len(answer) > MAX_ANSWER_LENGTH:
                        logger.warning("Answer too long, truncating", answer=answer[:50])
                        answer = answer[:MAX_ANSWER_LENGTH]
                    if question and answer:
                        tags = []
                        raw_tags = frontmatter.get("tags")
                        if isinstance(raw_tags, list):
                            tags = [str(t) for t in raw_tags]
                        elif isinstance(raw_tags, str) and raw_tags.strip():
                            tags = [raw_tags.strip()]

                        deck_name = str(frontmatter.get("deck") or f"Homeschool::{database_name}")

                        flashcards.append({
                            'question': question,
                            'answer': answer,
                            'source_file': str(file_path.relative_to(vault_path)) if file_path.is_relative_to(vault_path) else str(file_path),
                            'frontmatter': frontmatter,
                            'deck': deck_name,
                            'tags': tags,
                        })
                
                logger.info("Found flashcards in file", count=len(flashcards), file=str(file_path))
                
                # For each flashcard, create embedding and store in ChromaDB
                for i, card in enumerate(flashcards):
                    # Combine question and answer for embedding
                    text_to_embed = f"Question: {card['question']} Answer: {card['answer']}"
                    
                    # Generate embedding
                    if embedder:
                        embedding = embedder.encode([text_to_embed])[0].tolist()
                    else:
                        # Simple hash-based embedding for demo (not suitable for production)
                        import hashlib
                        hash_obj = hashlib.md5(text_to_embed.encode())
                        hash_hex = hash_obj.hexdigest()
                        # Convert hex to list of floats (simple approach)
                        embedding = [float(int(hash_hex[i:i+2], 16)) / 255.0 for i in range(0, min(len(hash_hex), 32), 2)]
                        # Pad or truncate to 384 dimensions (typical for sentence transformers)
                        if len(embedding) < 384:
                            embedding.extend([0.0] * (384 - len(embedding)))
                        else:
                            embedding = embedding[:384]
                    
                    # Prepare metadata
                    metadata = {
                        "source": card['source_file'],
                        "question": card['question'],
                        "answer": card['answer'],
                        **card['frontmatter']  # Include frontmatter as metadata
                    }
                    
                    # Create unique ID for this card
                    card_id = f"{card['source_file']}::{i}"

                    cards_for_export.append(
                        {
                            "question": card["question"],
                            "answer": card["answer"],
                            "deck": card.get("deck", f"Homeschool::{database_name}"),
                            "tags": card.get("tags", []),
                        }
                    )
                    
                    # Add to ChromaDB collection
                    try:
                        collection.add(
                            embeddings=[embedding],
                            metadatas=[metadata],
                            documents=[text_to_embed],
                            ids=[card_id]
                        )
                        logger.info("Added flashcard to ChromaDB", 
                                  card_id=card_id, 
                                  question=card['question'][:50] + "..." if len(card['question']) > 50 else card['question'])
                    except Exception as e:
                        logger.error("Failed to add card to ChromaDB", 
                                   card_id=card_id, error=str(e))
                
                processed_count += 1
                
            except Exception as e:
                logger.error("Failed to process file", 
                           file=str(file_path), error=str(e))
                continue
        
        logger.info("File processing completed", 
                   files_processed=processed_count,
                   total_files=len(files_to_process))

        # Export a local Anki package for manual import (default workflow)
        if cards_for_export:
            export_dir = config.paths.manifest_dir / "exports"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            apkg_path = export_dir / f"{database_name}_{timestamp}.apkg"
            try:
                final_apkg = export_apkg(
                    cards=cards_for_export,
                    output_path=apkg_path,
                    default_deck_name=f"Homeschool::{database_name}",
                    media_files=[],
                )
                logger.info("APKG export completed", path=str(final_apkg), card_count=len(cards_for_export))
                print(f"\nCreated Anki package: {final_apkg}")
                print("Import it manually in Anki: File -> Import")
            except ApkgExportError as e:
                logger.error("Failed to export APKG", error=str(e))
                print(f"Warning: APKG export failed: {e}")
        else:
            logger.info("No cards generated; skipping APKG export")

        # Get final count
        try:
            final_count = collection.count()
            logger.info("ChromaDB collection now contains", count=final_count, collection=collection_name)
        except Exception as e:
            logger.error("Failed to get collection count", error=str(e))
        
    except ConfigError as e:
        logger.error("Configuration error", error=str(e))
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error in sync process", error=str(e), exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
