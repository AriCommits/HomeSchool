"""
clean.py

Passes the raw transcript through a local LLM (via Ollama) to remove
filler, repetition, and noise while preserving all factual content
and segment markers.

Config keys used (pipeline/config.yml > config.yml):
  clean.model
  clean.ollama_host
  clean.prompt
  paths.scratch_dir
"""

from __future__ import annotations

from pathlib import Path

import ollama
from rich.console import Console

from pipeline.config import get

console = Console()

DEFAULT_PROMPT = """\
Clean this lecture transcript into structured markdown notes.
- Remove filler words, false starts, and repetition
- Preserve all specific facts, definitions, numbers, and examples exactly
- Use ## headers to separate distinct topics as they appear
- Preserve the segment markers (e.g. ## Segment 1: filename) exactly as they are
- Do not summarize away any detail — only remove noise

Transcript:
{transcript}
"""


def run(raw_transcript_path: Path) -> Path:
    """
    Main entry point for the cleaning step.

    Args:
        raw_transcript_path: Path to the raw_transcript.md produced by transcribe.py

    Returns:
        Path to the cleaned markdown file in the same scratch directory.
    """
    raw_transcript_path = Path(raw_transcript_path)
    if not raw_transcript_path.exists():
        raise FileNotFoundError(f"Raw transcript not found: {raw_transcript_path}")

    model = get("clean.model", "qwen3:8b")
    host = get("clean.ollama_host", "http://localhost:11434")
    prompt_template = get("clean.prompt", DEFAULT_PROMPT)

    transcript_text = raw_transcript_path.read_text(encoding="utf-8")
    prompt = prompt_template.format(transcript=transcript_text)

    console.print(f"[bold cyan]Cleaning transcript with:[/] {model}")
    console.print(f"[dim]Input length: {len(transcript_text.split())} words[/]")

    client = ollama.Client(host=host)
    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"num_predict": -1},  # no token limit
    )

    cleaned_text = response["message"]["content"]

    # Write cleaned output alongside the raw transcript
    output_path = raw_transcript_path.parent / "cleaned_transcript.md"
    output_path.write_text(cleaned_text, encoding="utf-8")

    console.print(f"[green]✓ Cleaned transcript written to:[/] {output_path}")
    return output_path
