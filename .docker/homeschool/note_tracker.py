"""
Note tracking module for Homeschool.
Handles unique ID generation, content hash tracking, and change detection.
"""

import hashlib
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple

from .logging import get_logger

logger = get_logger(__name__)


class NoteTracker:
    """Tracks notes and their content hashes for change detection."""

    def __init__(self, tracker_path: Optional[Path] = None):
        """
        Initialize the note tracker.
        
        Args:
            tracker_path: Path to the tracker file (JSON)
        """
        self._tracker_path = tracker_path or (Path.home() / ".homeschool" / "note_tracker.json")
        self._notes: Dict[str, dict] = {}
        self._load_tracker()

    def _safe_load_json(self, text: str) -> dict:
        """
        Safely load JSON with type validation.
        Prevents arbitrary object construction via JSON.
        """
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                logger.warning("Invalid tracker format, starting fresh")
                return {}
            return data
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse tracker JSON, starting fresh", error=str(e))
            return {}

    def _load_tracker(self):
        """Load the tracker data from disk."""
        if self._tracker_path.exists():
            try:
                text = self._tracker_path.read_text()
                self._notes = self._safe_load_json(text)
                logger.info("Loaded note tracker", entries=len(self._notes))
            except Exception as e:
                logger.warning("Failed to load tracker, starting fresh", error=str(e))
                self._notes = {}
        else:
            self._notes = {}

    def _save_tracker(self):
        """Save the tracker data to disk with secure permissions."""
        try:
            # Create directory with secure permissions (700 - owner only)
            self._tracker_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Set directory permissions to 700 (owner read/write/execute only)
            import stat
            self._tracker_path.parent.chmod(stat.S_IRWXU)
            
            # Write file with secure permissions
            self._tracker_path.write_text(json.dumps(self._notes, indent=2))
            self._tracker_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600 - owner only
        except Exception as e:
            logger.error("Failed to save tracker", error=str(e))

    def generate_note_id(self) -> str:
        """Generate a new unique note ID."""
        return str(uuid.uuid4())

    def compute_content_hash(self, content: str) -> str:
        """
        Compute SHA-256 hash of note content.
        
        Args:
            content: Full note content (including frontmatter)
            
        Returns:
            Hex digest of the content hash
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def get_note_id(self, note_path: Path) -> Optional[str]:
        """Get the stored ID for a note."""
        key = str(note_path)
        return self._notes.get(key, {}).get("note_id")

    def get_note_hash(self, note_path: Path) -> Optional[str]:
        """Get the stored content hash for a note."""
        key = str(note_path)
        return self._notes.get(key, {}).get("content_hash")

    def register_note(self, note_path: Path, note_id: str, content_hash: str):
        """Register a note with its ID and content hash."""
        key = str(note_path)
        self._notes[key] = {
            "note_id": note_id,
            "content_hash": content_hash,
            "last_processed": datetime.now().isoformat()
        }
        logger.info("Registered note", path=key, note_id=note_id)
        self._save_tracker()

    def update_note_hash(self, note_path: Path, new_hash: str):
        """Update the content hash for an existing note."""
        key = str(note_path)
        if key in self._notes:
            self._notes[key]["content_hash"] = new_hash
            self._notes[key]["last_processed"] = datetime.now().isoformat()
            self._save_tracker()

    def has_changed(self, note_path: Path, new_hash: str) -> bool:
        """
        Check if note content has changed.
        
        Args:
            note_path: Path to the note
            new_hash: New content hash to compare
            
        Returns:
            True if content has changed, False otherwise
        """
        stored_hash = self.get_note_hash(note_path)
        if stored_hash is None:
            return True  # New note
        return stored_hash != new_hash

    def remove_note(self, note_path: Path):
        """Remove a note from tracking."""
        key = str(note_path)
        if key in self._notes:
            del self._notes[key]
            self._save_tracker()
            logger.info("Removed note from tracker", path=key)

    def get_all_note_ids(self) -> Dict[str, str]:
        """Get all note IDs and their paths."""
        return {k: v["note_id"] for k, v in self._notes.items()}


def read_note_content(note_path: Path) -> Tuple[dict, str, str]:
    """
    Read a note file and extract frontmatter and content.
    
    Args:
        note_path: Path to the markdown note
        
    Returns:
        Tuple of (frontmatter dict, main content, note path as string for ID)
    """
    content = note_path.read_text(encoding='utf-8')
    frontmatter = {}
    main_content = content
    
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter_text = parts[1]
            main_content = parts[2]
            
            for line in frontmatter_text.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip()
    
    return frontmatter, main_content, str(note_path)


def add_note_id_to_frontmatter(note_path: Path, note_id: str) -> bool:
    """
    Add a unique ID to the note's frontmatter.
    
    Args:
        note_path: Path to the note
        note_id: Unique ID to add
        
    Returns:
        True if successful, False otherwise
    """
    try:
        content = note_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        if content.startswith('---'):
            frontmatter_end = None
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    frontmatter_end = i
                    break
            
            if frontmatter_end:
                lines.insert(frontmatter_end, f"homeschool_id: {note_id}")
                new_content = '\n'.join(lines)
                note_path.write_text(new_content, encoding='utf-8')
                return True
        
        return False
        
    except Exception as e:
        logger.error("Failed to add note ID to frontmatter", path=str(note_path), error=str(e))
        return False


def get_note_id_from_frontmatter(note_path: Path) -> Optional[str]:
    """
    Get the homeschool_id from note frontmatter if it exists.
    
    Args:
        note_path: Path to the note
        
    Returns:
        Note ID if found, None otherwise
    """
    try:
        content = note_path.read_text(encoding='utf-8')
        
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter_text = parts[1]
                for line in frontmatter_text.strip().split('\n'):
                    if line.startswith('homeschool_id:'):
                        return line.split(':', 1)[1].strip()
        return None
    except Exception:
        return None


# Audit trail storage (shared with NoteTracker)
AUDIT_LOG_PATH = Path.home() / ".homeschool" / "audit_log.jsonl"


def log_audit_event(event_type: str, note_path: str, details: dict):
    """
    Log an audit event for tracking note modifications.
    Uses JSONL format for efficient append-only logging.
    """
    import stat
    try:
        # Ensure directory exists with secure permissions
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        AUDIT_LOG_PATH.parent.chmod(stat.S_IRWXU)
        
        # Prune if file too large (>10MB)
        if AUDIT_LOG_PATH.exists() and AUDIT_LOG_PATH.stat().st_size > 10_000_000:
            with open(AUDIT_LOG_PATH, 'r') as f:
                lines = f.readlines()
            if len(lines) > 1000:
                with open(AUDIT_LOG_PATH, 'w') as f:
                    f.writelines(lines[-1000:])
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "note_path": note_path,
            "details": details
        }
        with open(AUDIT_LOG_PATH, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception as e:
        # Don't fail main functionality for audit
        pass
