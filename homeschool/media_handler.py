"""
Media handling module for Homeschool.
Handles wiki-link image references and copies media to Anki.
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple, Optional, Dict

from .logging import get_logger
from .path_security import is_path_within_directory

logger = get_logger(__name__)


class MediaHandler:
    """Handles media files from Obsidian notes for Anki sync."""

    # Regex pattern for Obsidian wiki-links: ![[filename.png]]
    WIKI_LINK_PATTERN = re.compile(r'!\[\[([^\]]+)\]\]')

    def __init__(
        self,
        vault_path: Path,
        anki_media_path: Optional[Path] = None,
        anki_connect=None
    ):
        """
        Initialize the media handler.
        
        Args:
            vault_path: Path to the Obsidian vault
            anki_media_path: Path to Anki's media folder (if local)
            anki_connect: Optional AnkiConnect client for remote media upload
        """
        self.vault_path = vault_path
        self.anki_media_path = anki_media_path
        self.anki_connect = anki_connect

    def extract_wiki_links(self, content: str) -> List[str]:
        """
        Extract all wiki-link media references from note content.
        
        Args:
            content: Markdown content of the note
            
        Returns:
            List of media filenames found
        """
        matches = self.WIKI_LINK_PATTERN.findall(content)
        return matches

    def _is_safe_path(self, path: Path, allowed_dir: Path) -> bool:
        """
        Check if a path is safe to access (no symlinks outside allowed directory).
        
        Args:
            path: Path to check
            allowed_dir: The directory the path should be within
            
        Returns:
            True if safe, False otherwise
        """
        try:
            resolved = path.resolve(strict=False)
            allowed_resolved = allowed_dir.resolve(strict=False)

            if not is_path_within_directory(resolved, allowed_resolved):
                return False
                
            # Check if it's a symlink pointing outside allowed directory
            if path.is_symlink():
                target = path.resolve(strict=False)
                if not is_path_within_directory(target, allowed_resolved):
                    logger.warning("Blocked symlink pointing outside vault",
                                 symlink=str(path), target=str(target))
                    return False
                    
            return True
        except (OSError, ValueError):
            return False

    def find_media_files(self, note_path: Path) -> List[Tuple[str, Path]]:
        """
        Find media files referenced in a note within the vault.
        
        Args:
            note_path: Path to the note
            
        Returns:
            List of tuples (filename, absolute_path)
        """
        note_dir = note_path.parent
        media_refs = self.extract_wiki_links(note_path.read_text())
        
        found_files = []
        for media_ref in media_refs:
            # Try various extensions
            media_path = note_dir / media_ref
            
            # Security: Check for symlink attacks before processing
            if not self._is_safe_path(media_path, self.vault_path):
                logger.warning("Skipping unsafe media path", path=str(media_path))
                continue
            
            # Use lstat to check existence without following symlinks first
            try:
                if media_path.is_file() and not media_path.is_symlink():
                    found_files.append((media_ref, media_path))
                    continue
            except OSError:
                pass
            
            # Try with common image extensions
            for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']:
                if not media_path.suffix:
                    media_with_ext = note_dir / (media_ref + ext)
                    if self._is_safe_path(media_with_ext, self.vault_path):
                        try:
                            if media_with_ext.is_file() and not media_with_ext.is_symlink():
                                found_files.append((media_ref + ext, media_with_ext))
                                break
                        except OSError:
                            pass
        
        return found_files

    def convert_wiki_link(self, wiki_link: str) -> str:
        """
        Convert Obsidian wiki-link to Anki-compatible format.
        
        Args:
            wiki_link: The wiki-link string (e.g., "image.png")
            
        Returns:
            Filename suitable for Anki
        """
        # Anki uses the same filename, just reference it directly
        return Path(wiki_link).name

    def copy_media_to_anki(
        self,
        source_path: Path,
        anki_deck: str
    ) -> Tuple[bool, str]:
        """
        Copy a media file to Anki's media folder.
        
        Args:
            source_path: Source file path in vault
            anki_deck: Target Anki deck name
            
        Returns:
            Tuple of (success, filename_or_error)
        """
        filename = source_path.name
        
        if self.anki_connect:
            try:
                # Upload via AnkiConnect
                data = source_path.read_bytes()
                result = self.anki_connect.store_media_file(
                    deck=anki_deck,
                    filename=filename,
                    data=data
                )
                logger.info("Uploaded media via AnkiConnect", filename=filename)
                return True, result
            except Exception as e:
                logger.error("Failed to upload media via AnkiConnect", 
                           filename=filename, error=str(e))
                return False, str(e)
        
        elif self.anki_media_path and self.anki_media_path.exists():
            try:
                # Copy locally
                dest_path = self.anki_media_path / filename
                shutil.copy2(source_path, dest_path)
                logger.info("Copied media to Anki folder", filename=filename)
                return True, filename
            except Exception as e:
                logger.error("Failed to copy media locally",
                           filename=filename, error=str(e))
                return False, str(e)
        
        return False, "No Anki connection or media path configured"

    def process_note_media(
        self,
        note_path: Path,
        anki_deck: str
    ) -> Dict[str, bool]:
        """
        Process all media files in a note and copy to Anki.
        
        Args:
            note_path: Path to the note
            anki_deck: Target Anki deck name
            
        Returns:
            Dict mapping filenames to success status
        """
        results = {}
        media_files = self.find_media_files(note_path)
        
        for filename, source_path in media_files:
            success, result = self.copy_media_to_anki(source_path, anki_deck)
            results[filename] = success
            
            if success:
                logger.info("Processed media file", 
                          note=str(note_path), 
                          media=filename)
            else:
                logger.warning("Failed to process media file",
                             note=str(note_path),
                             media=filename,
                             error=result)
        
        return results


def create_media_handler(config, anki_connect=None) -> MediaHandler:
    """
    Factory function to create a MediaHandler from config.
    
    Args:
        config: Homeschool Config object
        anki_connect: Optional AnkiConnect client
        
    Returns:
        Configured MediaHandler instance
    """
    # Try to find Anki media folder (platform-specific paths)
    anki_media_path = None
    
    if os.name == 'nt':  # Windows
        anki_base = Path(os.environ.get('APPDATA', '')) / 'Anki2'
    elif os.name == 'posix':
        if os.path.exists('/usr/local/share/anki'):  # Linux
            anki_base = Path.home() / '.local' / 'share' / 'anki'
        elif os.path.exists('/Applications/Anki.app'):  # macOS
            anki_base = Path.home() / 'Library' / 'Application Support' / 'Anki2'
        else:
            anki_base = Path.home() / '.local' / 'share' / 'anki'
    
    if anki_base.exists():
        # Find user profile folder
        for profile in anki_base.glob('user_1'):
            media = profile / 'collection.media'
            if media.exists():
                anki_media_path = media
                break
    
    return MediaHandler(
        vault_path=config.paths.vault,
        anki_media_path=anki_media_path,
        anki_connect=anki_connect
    )
