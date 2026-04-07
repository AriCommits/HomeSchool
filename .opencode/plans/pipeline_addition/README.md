# lecture-pipeline

Turns a folder of lecture video segments into a cleaned, annotated markdown file
ready for import into the [HomeSchool](../HomeSchool/) vault.

```
videos/ (your downloaded segments)
    │
    ▼
transcribe.py       faster-whisper → raw_transcript.md
    │
    ▼
clean.py            qwen3 via ollama → cleaned_transcript.md
    │
    ▼
augment.py          you add slide content → COURSE_LectureNN_DATE.md → vault
```

Intermediate files land in `~/Downloads/lecture-pipeline/<COURSE>_LectureNN/`.
Only the final annotated markdown touches your HomeSchool vault.

---

## Setup

```bash
conda env create -f environment.yml
conda activate lecture-pipeline
```

Pull the LLM you want to use for cleaning (default: qwen3:8b):
```bash
ollama pull qwen3:8b
```

Edit `config.yml` to set your vault path and scratch directory.
Edit `pipeline/config.yml` to change the Whisper model, LLM, or cleaning prompt.

---

## Configuration

Configuration is hierarchical — `pipeline/config.yml` deep-merges over `config.yml`.
You only need to declare what you want to override in the pipeline config.

### Base `config.yml` (shared project settings)
| Key | Default | Description |
|-----|---------|-------------|
| `paths.vault_output` | `~/Repos/HomeSchool/vault/lectures/` | Where final .md lands |
| `paths.scratch_dir` | `~/Downloads/lecture-pipeline/` | Intermediate files |
| `chroma.collection` | `lecture_pipeline` | ChromaDB collection name |

### `pipeline/config.yml` (transcription-specific settings)
| Key | Default | Description |
|-----|---------|-------------|
| `transcribe.model` | `medium.en` | Whisper model size |
| `transcribe.device` | `cuda` | `cuda` or `cpu` |
| `transcribe.compute_type` | `float16` | `float16` (cuda) or `int8` (cpu) |
| `transcribe.models_dir` | `~/models/whisper` | Where Whisper weights are cached |
| `transcribe.language` | `en` | Language code or `null` to auto-detect |
| `clean.model` | `qwen3:8b` | Ollama model for transcript cleaning |
| `clean.ollama_host` | `http://localhost:11434` | Ollama server URL |
| `clean.prompt` | *(see file)* | Full prompt template — `{transcript}` is replaced at runtime |

To switch Whisper model to large-v3, just change one line in `pipeline/config.yml`:
```yaml
transcribe:
  model: large-v3
  compute_type: float16
```

To switch the cleaning LLM to qwen3.5 when it becomes available on Ollama:
```yaml
clean:
  model: qwen3.5:8b
```

---

## Usage

```bash
# Full pipeline: transcribe -> clean -> annotate -> vault
python run.py --input ~/Downloads/BIOL101_Week3/ --course BIOL101 --lecture 3

# Individual steps (useful if a step fails mid-run)
python run.py --input ~/Downloads/BIOL101_Week3/ --course BIOL101 --lecture 3 --transcribe
python run.py --course BIOL101 --lecture 3 --clean
python run.py --course BIOL101 --lecture 3 --augment

# Verify your config is merging correctly
python run.py --show-config
```

### Output filename format

```
BIOL101_Lecture03_2026-04-06.md
```

Derived from `--course`, `--lecture`, and today's date. Deterministic and sortable.

---

## Intermediate files (scratch directory)

```
~/Downloads/lecture-pipeline/
└── BIOL101_Lecture03/
    ├── segment_01_intro.txt          # individual whisper outputs
    ├── segment_02_main.txt
    ├── raw_transcript.md             # concatenated segments
    └── cleaned_transcript.md         # after LLM cleaning pass
```

These are safe to delete after the vault file is written.

---

## Relation to HomeSchool

This pipeline is the **upstream** input layer. It produces markdown files that
HomeSchool picks up during its next sync. No changes are needed to HomeSchool.

The only contract between them is that the final markdown contains
`question::answer` formatted flashcard pairs, which HomeSchool extracts automatically.

Future MCP integration will expose `transcribe_lecture()` and `sync_flashcards()`
as agent-callable tools, allowing orchestration across both pipelines from a single
natural language interface.
