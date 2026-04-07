"""
transcribe.py

Transcribes a folder of video files using faster-whisper.
Outputs one raw .txt transcript per video into the scratch directory,
then concatenates them into a single segmented markdown file.

Config keys used (pipeline/config.yml > config.yml):
  transcribe.model
  transcribe.device
  transcribe.compute_type
  transcribe.models_dir
  transcribe.language
  paths.scratch_dir
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from faster_whisper import WhisperModel
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from pipeline.config import get

console = Console()

SUPPORTED_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".zoom"}


def _load_model() -> WhisperModel:
    model_name = get("transcribe.model", "medium.en")
    device = get("transcribe.device", "cuda")
    compute_type = get("transcribe.compute_type", "float16")
    models_dir = get("transcribe.models_dir", os.path.expanduser("~/models/whisper"))

    console.print(f"[bold cyan]Loading Whisper model:[/] {model_name} on {device}")
    return WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
        download_root=str(models_dir),
    )


def _transcribe_file(model: WhisperModel, video_path: Path) -> str:
    """Transcribe a single video file, return raw transcript string."""
    language = get("transcribe.language", "en") or None
    segments, _ = model.transcribe(str(video_path), language=language)
    return "\n".join(segment.text.strip() for segment in segments)


def _build_output_filename(course: str, lecture: int) -> str:
    """
    Generate a deterministic markdown filename.
    Format: COURSE_LectureNN_YYYY-MM-DD.md
    """
    today = date.today().strftime("%Y-%m-%d")
    lecture_num = str(lecture).zfill(2)
    safe_course = course.replace(" ", "_").upper()
    return f"{safe_course}_Lecture{lecture_num}_{today}.md"


def run(
    input_folder: Path,
    course: str,
    lecture: int,
) -> Path:
    """
    Main entry point for the transcription step.

    Args:
        input_folder: Path to folder containing video segments.
        course:       Course identifier e.g. "BIOL101".
        lecture:      Lecture number e.g. 3.

    Returns:
        Path to the combined segmented markdown transcript.
    """
    input_folder = Path(input_folder)
    videos = sorted(
        f for f in input_folder.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not videos:
        raise FileNotFoundError(
            f"No supported video files found in {input_folder}\n"
            f"Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    console.print(f"[bold]Found {len(videos)} video segment(s)[/] in {input_folder}")

    # Set up scratch directory for this lecture
    scratch_root = Path(get("paths.scratch_dir", "~/Downloads/lecture-pipeline"))
    lecture_scratch = scratch_root / f"{course.upper()}_Lecture{str(lecture).zfill(2)}"
    lecture_scratch.mkdir(parents=True, exist_ok=True)

    model = _load_model()
    segments_text: list[str] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for i, video in enumerate(videos, start=1):
            task = progress.add_task(f"Transcribing segment {i}/{len(videos)}: {video.name}", total=None)

            transcript = _transcribe_file(model, video)

            # Save individual segment transcript for debugging/reference
            segment_file = lecture_scratch / f"segment_{str(i).zfill(2)}_{video.stem}.txt"
            segment_file.write_text(transcript, encoding="utf-8")

            # Accumulate with visible segment header
            segments_text.append(f"## Segment {i}: {video.stem}\n\n{transcript}")
            progress.remove_task(task)

    # Write combined raw transcript
    combined = "\n\n---\n\n".join(segments_text)
    raw_output = lecture_scratch / "raw_transcript.md"
    raw_output.write_text(combined, encoding="utf-8")

    console.print(f"[green]✓ Raw transcript written to:[/] {raw_output}")
    return raw_output
