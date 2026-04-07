"""
run.py — lecture-pipeline CLI entrypoint

Usage examples:

  # Full pipeline (transcribe -> clean -> annotate -> vault)
  python run.py --input ~/Downloads/BIOL101_Week3/ --course BIOL101 --lecture 3

  # Run individual steps
  python run.py --input ~/Downloads/BIOL101_Week3/ --course BIOL101 --lecture 3 --transcribe
  python run.py --input ~/Downloads/BIOL101_Week3/ --course BIOL101 --lecture 3 --clean
  python run.py --input ~/Downloads/BIOL101_Week3/ --course BIOL101 --lecture 3 --augment

  # Verify config is loading correctly
  python run.py --show-config
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console

from pipeline import augment, clean, transcribe
from pipeline.config import get, load_config
from pipeline.transcribe import _build_output_filename

console = Console()


def _resolve_scratch(course: str, lecture: int) -> Path:
    scratch_root = Path(get("paths.scratch_dir", "~/Downloads/lecture-pipeline"))
    return scratch_root / f"{course.upper()}_Lecture{str(lecture).zfill(2)}"


@click.command()
@click.option(
    "--input", "input_folder",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Folder containing lecture video segments.",
)
@click.option("--course", default=None, help="Course identifier e.g. BIOL101.")
@click.option("--lecture", default=1, type=int, help="Lecture number.")
@click.option("--transcribe", "run_transcribe", is_flag=True, help="Run transcription step only.")
@click.option("--clean", "run_clean", is_flag=True, help="Run cleaning step only.")
@click.option("--augment", "run_augment", is_flag=True, help="Run augmentation/vault step only.")
@click.option("--show-config", is_flag=True, help="Print merged config and exit.")
def main(
    input_folder: Path | None,
    course: str | None,
    lecture: int,
    run_transcribe: bool,
    run_clean: bool,
    run_augment: bool,
    show_config: bool,
):
    # --show-config: dump merged config and exit
    if show_config:
        console.print_json(json.dumps(load_config(), indent=2, default=str))
        sys.exit(0)

    # Resolve course from config if not passed
    course = course or get("project.name", "UNGROUPED")
    output_filename = _build_output_filename(course, lecture)
    scratch_dir = _resolve_scratch(course, lecture)

    # Determine which steps to run
    run_all = not any([run_transcribe, run_clean, run_augment])

    # ── Step 1: Transcribe ──────────────────────────────────────────────────
    if run_all or run_transcribe:
        if input_folder is None:
            console.print("[red]--input is required for the transcription step.[/]")
            sys.exit(1)
        raw_path = transcribe.run(input_folder, course, lecture)
    else:
        raw_path = scratch_dir / "raw_transcript.md"

    # ── Step 2: Clean ───────────────────────────────────────────────────────
    if run_all or run_clean:
        cleaned_path = clean.run(raw_path)
    else:
        cleaned_path = scratch_dir / "cleaned_transcript.md"

    # ── Step 3: Augment → Vault ─────────────────────────────────────────────
    if run_all or run_augment:
        augment.run(cleaned_path, output_filename)


if __name__ == "__main__":
    main()
