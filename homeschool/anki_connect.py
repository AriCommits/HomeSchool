"""
AnkiConnect integration module for Homeschool.
Provides interface to Anki flashcard application via AnkiConnect plugin.
"""

import os
import base64
import time
from typing import Optional
import requests
from .logging import get_logger

logger = get_logger(__name__)


class AnkiConnectError(Exception):
    """Exception raised when AnkiConnect operations fail."""
    pass


class AnkiConnect:
    """Client for AnkiConnect API."""

    ANKI_CONNECT_VERSION = 6

    def __init__(self, anki_url: str = "http://localhost:8765", max_retries: int = 3):
        """
        Initialize AnkiConnect client.

        Args:
            anki_url: URL of AnkiConnect API (prefer https:// for security)
            max_retries: Maximum retry attempts for failed requests
        """
        # Security: Validate URL scheme
        self.anki_url = anki_url
        if not anki_url.startswith(('http://', 'https://')):
            raise AnkiConnectError("AnkiConnect URL must start with http:// or https://")
        
        # Security: Warn about unencrypted HTTP
        if anki_url.startswith('http://'):
            logger.warning("Using unencrypted HTTP - consider using HTTPS for security")
        
        self.max_retries = max_retries

    def _request(self, action: str, **params):
        """Make a request to AnkiConnect API with retry logic and TLS verification."""
        payload = {
            "action": action,
            "version": self.ANKI_CONNECT_VERSION,
            "params": params
        }

        # Security: Enforce TLS verification for HTTPS connections
        verify_ssl = self.anki_url.startswith('https://')
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.anki_url, 
                    json=payload, 
                    timeout=30,
                    verify=verify_ssl,  # Enable SSL verification for HTTPS
                    cert=None  # Could add client certificates here if needed
                )
                response.raise_for_status()
                result = response.json()

                if "error" in result and result["error"]:
                    error_msg = result["error"]
                    logger.error("AnkiConnect error", action=action, error=error_msg)
                    last_error = AnkiConnectError(error_msg)
                    # Don't retry on common errors
                    if "invalid" in error_msg.lower() or "bidden" in error_msg.lower():
                        break
                    time.sleep(1 * (attempt + 1))  # Simple backoff
                    continue

                if "result" in result:
                    return result["result"]
                return None

            except requests.exceptions.ConnectionError as e:
                logger.warning("Connection error", attempt=attempt+1, error=str(e))
                last_error = AnkiConnectError(f"Connection failed: {e}")
                time.sleep(1 * (attempt + 1))
            except requests.exceptions.Timeout as e:
                logger.warning("Request timeout", attempt=attempt+1, error=str(e))
                last_error = AnkiConnectError(f"Request timeout: {e}")
                time.sleep(1 * (attempt + 1))
            except requests.exceptions.HTTPError as e:
                logger.warning("HTTP error", attempt=attempt+1, error=str(e))
                last_error = AnkiConnectError(f"HTTP error: {e}")
                time.sleep(1 * (attempt + 1))

        raise last_error

    def check_connection(self) -> bool:
        """
        Check if AnkiConnect is available and responding.

        Returns:
            True if connected successfully, False otherwise
        """
        try:
            result = self._request("ping")
            return result is not None
        except AnkiConnectError:
            return False

    def get_deck_names(self) -> list[str]:
        """Get list of all deck names in Anki."""
        return self._request("getDeckNames")

    def create_deck(self, deck: str) -> int:
        """Create a new deck in Anki."""
        return self._request("createDeck", deck=deck)

    def add_note(self, deck: str, front: str, back: str, 
                 model: str = "Basic", tags: Optional[list] = None) -> int:
        """Add a new basic note to Anki."""
        note = {
            "deckName": deck,
            "modelName": model,
            "fields": {
                "Front": front,
                "Back": back
            }
        }
        if tags:
            note["tags"] = tags

        return self._request("addNote", note=note)

    def add_cloze(self, deck: str, text: str, 
                  model: str = "Cloze", tags: Optional[list] = None) -> int:
        """Add a cloze deletion note to Anki."""
        note = {
            "deckName": deck,
            "modelName": model,
            "fields": {
                "Text": text
            }
        }
        if tags:
            note["tags"] = tags

        return self._request("addNote", note=note)

    def update_note(self, note_id: int, fields: dict) -> bool:
        """Update fields of an existing note."""
        return self._request("updateNoteFields",
                            note={"id": note_id, "fields": fields})

    def delete_notes(self, note_ids: list[int]) -> int:
        """Delete notes from Anki."""
        return self._request("deleteNotes", notes=note_ids)

    def find_notes(self, query: str) -> list[int]:
        """Find notes matching a query."""
        return self._request("findNotes", query=query)

    def store_media_file(self, deck: str, filename: str, data: bytes) -> str:
        """Store a media file in Anki's media folder."""
        import base64
        b64_data = base64.b64encode(data).decode('utf-8')
        return self._request(
            "storeMediaFile",
            deck=deck,
            filename=filename,
            data=b64_data
        )

    def get_model_names(self) -> list[str]:
        """Get list of all note model names."""
        return self._request("modelNames")


def create_anki_client(anki_url: Optional[str] = None) -> AnkiConnect:
    """
    Factory function to create an AnkiConnect client.

    Args:
        anki_url: Optional custom AnkiConnect URL

    Returns:
        Configured AnkiConnect client
    """
    anki_url = anki_url or os.environ.get("ANKICONNECT_URL", "http://localhost:8765")
    return AnkiConnect(anki_url=anki_url)
