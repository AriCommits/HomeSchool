from pathlib import Path

import pytest

from homeschool.apkg_exporter import (
    ApkgExportError,
    sanitize_media_filename,
    validate_media_file,
)


def test_sanitize_media_filename_rejects_path():
    with pytest.raises(ApkgExportError):
        sanitize_media_filename("../secret.png")


def test_sanitize_media_filename_rejects_extension():
    with pytest.raises(ApkgExportError):
        sanitize_media_filename("payload.exe")


def test_validate_media_file_ok(temp_dir):
    media = temp_dir / "image.png"
    media.write_bytes(b"\x89PNG\r\n")
    size = validate_media_file(media)
    assert size > 0
