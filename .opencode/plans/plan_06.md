# Improvement Plan 06: Implementation Roadmap

## Overview
This plan implements the pending improvements from plans 01-05, prioritizing foundational infrastructure (testing) followed by user-facing features.

## Priority Ordering

### Phase 1: Testing Infrastructure (Week 1)
- [x] Create test directory structure
- [x] Set up pytest and conftest.py with fixtures
- [x] Write unit tests for core modules (config.py, note parsing)
- [x] Add mocked AnkiConnect integration tests
- [ ] Set up CI/CD workflow

### Phase 2: ID Tracking & Change Detection (Week 2)
- [x] Add unique ID generation to note frontmatter
- [x] Implement content hash comparison
- [x] Add `--force-regen` CLI flag
- [x] Store note ID mappings in manifest database

### Phase 3: Semantic Deduplication (Week 3)
- [x] Add similarity detection using sentence-transformers/ChromaDB
- [x] Implement config option `skip_similar_cards: true`
- [x] Add threshold configuration (default 85%)
- [x] Integrate with sync pipeline

### Phase 4: Media Handling (Week 4)
- [x] Detect wiki-link media references
- [x] Copy media files to Anki media folder
- [x] Convert Obsidian paths to Anki-compatible paths

### Phase 5: Local AI Abstraction (Week 5)
- [ ] Add Ollama provider support
- [ ] Abstract AI provider interface
- [ ] Add config: `ai_provider` options
- [ ] Implement offline queue system

## Implementation Status

### Completed (from previous plans)
- [x] Docker health checks and restart policies (compose.yaml)
- [x] Structured logging (logging.py)
- [x] One-command operations: init, status, logs, reset (cli.py)
- [x] --database argument for multi-database support (cli.py, sync.py)
- [x] Configuration schema (config.py)
- [x] Multiple ChromaDB databases (config databases section)

### Completed (This Session)
- [x] Testing framework setup (27 unit tests passing)
- [x] Sample notes fixtures (basic_flashcards.md, cloze_deletions.md, with_media.md)
- [x] AnkiConnect module (homeschool/anki_connect.py)
- [x] Config validation tests (GPU, auth token, sync, databases)
- [x] Configuration templates (open_config.yaml, locked_down_config.yaml exist)
- [x] ID Tracking module (homeschool/note_tracker.py)
- [x] Semantic Deduplication module (homeschool/deduplication.py)
- [x] Media Handling module (homeschool/media_handler.py)
- [x] FSRS Scheduler module (homeschool/fsrs_scheduler.py)
- [x] Config: DeduplicationConfig class

### Not Started
- [ ] AI provider abstraction (Ollama integration)
- [ ] CI/CD workflow setup

## New Modules Created

| Module | File | Purpose |
|--------|------|---------|
| AnkiConnect | `homeschool/anki_connect.py` | Anki integration with retry logic |
| Note Tracker | `homehscool/note_tracker.py` | ID & hash tracking for change detection |
| Deduplication | `homeschool/deduplication.py` | Semantic similarity checking |
| Media Handler | `homeschool/media_handler.py` | Wiki-link conversion, media copy |
| FSRS Scheduler | `homeschool/fsrs_scheduler.py` | Spaced repetition scheduling |

## CLI Changes
- Added `--force-regen` flag to sync command

## Dependencies
```
# Testing
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
requests-mock>=1.10.0

# Semantic Deduplication
sentence-transformers>=2.2.0
numpy>=1.24.0

# Optional: Local AI
ollama>=0.1.0

# Optional: FSRS
py-fsrs>=0.0.1
```

## Acceptance Criteria

### Testing
- [x] All unit tests pass (27 tests)
- [x] Config validation tests cover GPU, auth token, sync, databases
- [ ] 80%+ coverage on core modules
- [ ] CI/CD pipeline runs tests on PR

### ID Tracking
- [x] Unique ID added to notes on first sync
- [x] Content hash detects changes reliably
- [x] --force-regen bypasses cache

### Deduplication
- [x] Similarity detection with configurable threshold
- [x] Works offline with local embeddings
- [x] Config option in config.yaml

### Media Handling
- [x] Images copy to Anki media folder
- [x] Wiki-links converted correctly
- [x] Platform-specific Anki path detection

### FSRS Integration
- [x] Basic scheduler with presets (aggressive, balanced, conservative)
- [x] Falls back to basic scheduling if py-fsrs not available
- [x] Anki-compatible field generation

## Related Plans
- improvement_plan_01.md - Comprehensive improvements
- improvement_plan_03.md - User-driven enhancements
- improvement_plan_03_b.md - Testing framework
- improvement_plan_05.md - Multiple databases (completed)