from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Iterable


ALLOWED_MEDIA_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".mp3",
    ".wav",
}

MAX_MEDIA_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_MEDIA_SIZE_BYTES = 100 * 1024 * 1024


class ApkgExportError(Exception):
    pass


def _stable_id(name: str, offset: int = 0) -> int:
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) + offset


def sanitize_media_filename(name: str) -> str:
    if not name or name.strip() in {"", ".", ".."}:
        raise ApkgExportError("Media filename is empty or invalid")

    if "/" in name or "\\" in name:
        raise ApkgExportError(f"Media filename must not contain path separators: {name}")

    base = Path(name).name
    if base != name:
        raise ApkgExportError(f"Media filename must be basename-only: {name}")

    ext = Path(base).suffix.lower()
    if ext not in ALLOWED_MEDIA_EXTENSIONS:
        raise ApkgExportError(f"Unsupported media extension for '{base}'")

    return base


def validate_media_file(path: Path) -> int:
    if not path.exists() or not path.is_file():
        raise ApkgExportError(f"Media path is not a file: {path}")

    sanitize_media_filename(path.name)

    size = path.stat().st_size
    if size > MAX_MEDIA_FILE_SIZE_BYTES:
        raise ApkgExportError(
            f"Media file exceeds size limit ({MAX_MEDIA_FILE_SIZE_BYTES} bytes): {path.name}"
        )

    return size


def export_apkg(
    cards: list[dict],
    output_path: Path,
    default_deck_name: str,
    media_files: Iterable[Path] | None = None,
) -> Path:
    try:
        import genanki
    except ImportError as exc:
        raise ApkgExportError(
            "Missing dependency 'genanki'. Install it before exporting .apkg files."
        ) from exc

    if not cards:
        raise ApkgExportError("Cannot export APKG: no cards were generated")

    model = genanki.Model(
        _stable_id("homeschool.basic.model", offset=1000),
        "Homeschool Basic",
        fields=[
            {"name": "Front"},
            {"name": "Back"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "{{Front}}",
                "afmt": "{{FrontSide}}<hr id=answer>{{Back}}",
            }
        ],
    )

    decks: dict[str, object] = {}
    cards_by_deck: dict[str, list[dict]] = defaultdict(list)
    for card in cards:
        front = str(card.get("question", "")).strip()
        back = str(card.get("answer", "")).strip()
        if not front or not back:
            continue

        deck = str(card.get("deck") or default_deck_name)
        cards_by_deck[deck].append({"front": front, "back": back, "tags": card.get("tags", [])})

    for deck_name, deck_cards in cards_by_deck.items():
        deck = genanki.Deck(_stable_id(f"deck::{deck_name}", offset=2000), deck_name)
        for card in deck_cards:
            tags = [str(t).strip() for t in card["tags"] if str(t).strip()]
            note = genanki.Note(
                model=model,
                fields=[card["front"], card["back"]],
                tags=tags,
            )
            deck.add_note(note)
        decks[deck_name] = deck

    if not decks:
        raise ApkgExportError("No valid cards remained after validation")

    package = genanki.Package(list(decks.values()))

    safe_media: list[str] = []
    total_media_size = 0
    for media in media_files or []:
        media_path = Path(media)
        total_media_size += validate_media_file(media_path)
        if total_media_size > MAX_TOTAL_MEDIA_SIZE_BYTES:
            raise ApkgExportError(
                f"Total media size exceeds limit ({MAX_TOTAL_MEDIA_SIZE_BYTES} bytes)"
            )
        safe_media.append(str(media_path))

    package.media_files = safe_media

    output_path.parent.mkdir(parents=True, exist_ok=True)
    package.write_to_file(str(output_path))
    return output_path
