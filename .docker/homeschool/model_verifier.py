"""
Model integrity verification for Homeschool.
Provides SHA256 hash verification to detect tampered model files.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class ModelIntegrityError(Exception):
    """Raised when model integrity verification fails."""
    pass


def compute_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """
    Compute hash of a file.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use (sha256, sha512, md5)
        
    Returns:
        Hex digest of the file hash
    """
    if algorithm == "sha256":
        hasher = hashlib.sha256()
    elif algorithm == "sha512":
        hasher = hashlib.sha512()
    elif algorithm == "md5":
        hasher = hashlib.md5()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    
    return hasher.hexdigest()


def verify_model_integrity(
    model_path: Path,
    expected_hash: Optional[str] = None,
    known_hashes_file: Optional[Path] = None
) -> bool:
    """
    Verify that a model file hasn't been tampered with.
    
    Args:
        model_path: Path to the model file
        expected_hash: Expected SHA256 hash (if known)
        known_hashes_file: Path to a JSON file with known good hashes
        
    Returns:
        True if verified, False otherwise
    """
    if not model_path.exists():
        logger.error("Model file not found", path=str(model_path))
        return False
    
    # Compute actual hash
    try:
        actual_hash = compute_file_hash(model_path)
    except Exception as e:
        logger.error("Failed to compute model hash", error=str(e))
        return False
    
    # If expected hash provided, verify directly
    if expected_hash:
        if actual_hash.lower() != expected_hash.lower():
            logger.error("Model hash mismatch!", 
                        expected=expected_hash[:16] + "...",
                        actual=actual_hash[:16] + "...")
            return False
        logger.info("Model integrity verified", path=str(model_path))
        return True
    
    # Check against known hashes file
    if known_hashes_file and known_hashes_file.exists():
        try:
            known_hashes = json.loads(known_hashes_file.read_text())
            model_name = model_path.name
            
            if model_name in known_hashes:
                expected = known_hashes[model_name].lower()
                if actual_hash.lower() != expected:
                    logger.error("Model hash mismatch!", 
                                expected=expected[:16] + "...",
                                actual=actual_hash[:16] + "...")
                    return False
                logger.info("Model integrity verified", path=str(model_path))
                return True
        except Exception as e:
            logger.warning("Failed to verify against known hashes", error=str(e))
    
    # No verification possible - warn but don't block
    logger.warning("No hash available for verification", path=str(model_path))
    return True


def verify_model_directory(
    model_dir: Path,
    known_hashes_file: Optional[Path] = None
) -> Dict[str, bool]:
    """
    Verify all model files in a directory.
    
    Args:
        model_dir: Directory containing model files
        known_hashes_file: Path to JSON file with known good hashes
        
    Returns:
        Dict mapping model filenames to verification status
    """
    results = {}
    
    if not model_dir.exists() or not model_dir.is_dir():
        logger.warning("Model directory not found", path=str(model_dir))
        return results
    
    model_extensions = {'.gguf', '.bin', '.pt', '.onnx', '.model'}
    
    for model_file in model_dir.iterdir():
        if model_file.is_file() and model_file.suffix.lower() in model_extensions:
            try:
                verified = verify_model_integrity(
                    model_file,
                    known_hashes_file=known_hashes_file
                )
                results[model_file.name] = verified
            except Exception:
                results[model_file.name] = False
    
    return results


def generate_hashes_file(model_dir: Path, output_file: Path) -> None:
    """
    Generate a hashes file for known-good models.
    
    Args:
        model_dir: Directory containing model files
        output_file: Path to save the hashes JSON file
    """
    hashes = {}
    
    if not model_dir.exists():
        logger.error("Model directory not found", path=str(model_dir))
        return
    
    model_extensions = {'.gguf', '.bin', '.pt', '.onnx', '.model'}
    
    for model_file in model_dir.iterdir():
        if model_file.is_file() and model_file.suffix.lower() in model_extensions:
            model_hash = compute_file_hash(model_file)
            hashes[model_file.name] = model_hash
            logger.info("Computed hash for model", model=model_file.name, 
                       hash=model_hash[:16] + "...")
    
    output_file.write_text(json.dumps(hashes, indent=2))
    logger.info("Generated model hashes file", path=str(output_file))
