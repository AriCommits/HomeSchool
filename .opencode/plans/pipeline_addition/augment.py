"""
augment.py

Opens the cleaned transcript for manual slide annotation,
then writes the final markdown to the HomeSchool vault.

This step intentionally pauses for user interaction:
  1. Opens the cleaned transcript in the system default editor.
  2. Waits for the user to save and close.
  3. Writes the final file to the vault output path.

Config keys used:
  paths.vault_output
  paths.scratch_dir
"""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from pipeline.config import get

console = Console()


def _open_in_editor(file_path: Path) -> None:
    """Open a file in the system default editor."""
    system = platform.system()
    if system == "Windows":
        os.startfile(str(file_path))
    elif system == "Darwin":
        subprocess.run(["open", str(file_path)])
    else:
        editor = os.environ.get("EDITOR", "xdg-open")
        subprocess.run([editor, str(file_path)])


def run(
    cleaned_transcript_path: Path,
    output_filename: str,
) -> Path:
    """
    Main entry point for the augmentation step.

    Args:
        cleaned_transcript_path: Path to cleaned_transcript.md from clean.py
        output_filename:         Final filename for the vault e.g. BIOL101_Lecture03_2026-04-06.md

    Returns:
        Path to the final markdown file written to the vault.
    """
    cleaned_transcript_path = Path(cleaned_transcript_path)
    if not cleaned_transcript_path.exists():
        raise FileNotFoundError(f"Cleaned transcript not found: {cleaned_transcript_path}")

    console.print("\n[bold yellow]── Manual Annotation Step ──[/]")
    console.print(
        "The cleaned transcript will open in your editor.\n"
        "Add your slide content under each [bold]## Segment[/] header.\n"
        "Use [bold]### Slide N[/] headers to mark slide boundaries.\n"
        "Save and close the file when done.\n"
    )

    _open_in_editor(cleaned_transcript_path)

    Confirm.ask("Press Enter when you have finished annotating", default=True)

    # Read the annotated content
    final_content = cleaned_transcript_path.read_text(encoding="utf-8")

    # Write to vault
    vault_path = Path(get("paths.vault_output"))
    vault_path.mkdir(parents=True, exist_ok=True)

    output_path = vault_path / output_filename

    # If a file already exists at this path, ask before overwriting
    if output_path.exists():
        overwrite = Confirm.ask(
            f"[yellow]{output_filename}[/] already exists in vault. Overwrite?",
            default=False,
        )
        if not overwrite:
            # Write to scratch instead so nothing is lost
            fallback = cleaned_transcript_path.parent / output_filename
            fallback.write_text(final_content, encoding="utf-8")
            console.print(f"[yellow]Saved to scratch instead:[/] {fallback}")
            return fallback

    output_path.write_text(final_content, encoding="utf-8")
    console.print(f"\n[green]✓ Final notes written to vault:[/] {output_path}")
    return output_path
