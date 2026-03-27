# Improvement Plan 03-B: Testing Framework

## Overview
This plan outlines a comprehensive testing framework for the Homeschool project based on the features and improvements defined in improvement_plan_02.md and improvement_plan_03.md. The testing framework ensures reliability, correctness, and regression prevention across all core functionality.

## Testing Philosophy

- **Test First**: Write tests before implementing new features per improvement plans
- **Fast Feedback**: Unit tests for core logic, integration tests for workflows
- **CI/CD Integration**: All tests must pass before merging changes
- **Coverage Goals**: Core logic >90%, integration >80%

---

## Test Pyramid

```
        ╱╲
       ╱  ╲        E2E Tests (5%)
      ╱────╲
     ╱      ╲      Integration Tests (20%)
    ╱────────╲
   ╱          ╲    Unit Tests (75%)
  ╱────────────╲
```

---

## Unit Test Categories

### 1. Core Logic Tests

#### 1.1 Note Processing
| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| Parse basic flashcard | `Question::Answer` | Flashcard(front="Question", back="Answer") |
| Parse cloze deletion | `==highlight==` | ClozeCard(content="highlight") |
| Parse multi-line | `Q?\nA` | MultiLineCard(question="Q", answer="A") |
| Extract frontmatter | YAML header | Dict of key-value pairs |
| Hash note content | Note text | SHA256 hash string |

#### 1.2 AnkiConnect Integration
| Test Case | Mock Response | Expected |
|-----------|---------------|----------|
| Create card | `{"result": 1234567890}` | Card created with ID |
| Update card | `{"result": true}` | Success boolean |
| Delete card | `{"result": true}` | Success boolean |
| Find cards | `{"result": [1,2,3]}` | List of card IDs |
| Get deck names | `{"result": ["Deck1", "Deck2"]}` | List of decks |

#### 1.3 AI Flashcard Generation
| Test Case | Input | Expected |
|-----------|-------|----------|
| Generate basic cards | Note with 3 paragraphs | List of 3+ flashcards |
| Quality scoring | Generated card | Score 0-100 |
| Deduplication check | Card A, Card B (similar) | Similarity percentage |
| Confidence scoring | Card content | Confidence 0-1 |

#### 1.4 Configuration Validation
| Test Case | Input | Expected |
|-----------|-------|----------|
| Valid config | Complete config dict | Valid() returns True |
| Missing required | Config without `anki_url` | ValidationError |
| Invalid path | Non-existent `vault_path` | ValidationError |
| Invalid AI provider | Unknown provider | ValidationError |

### 2. Error Handling Tests

#### 2.1 Network Failures
| Test Scenario | Given | When | Then |
|---------------|-------|------|------|
| AnkiConnect timeout | HTTP timeout | `create_card()` | Retry 3x, then raise |
| Connection refused | ConnectionError | `connect()` | Raise clear error |
| Invalid response | Malformed JSON | `create_card()` | Raise ParseError |

#### 2.2 Data Integrity
| Test Scenario | Given | When | Then |
|---------------|-------|------|------|
| ChromaDB unavailable | Connection fails | `query_db()` | Fallback to SQLite |
| Checksum mismatch | File corrupted | `verify_file()` | Raise IntegrityError |
| Concurrent write | Two processes sync | `sync_notes()` | Lock acquired / fail |

---

## Integration Test Categories

### 3. Anki Integration Tests

#### 3.1 Card Sync Workflow
```
Test: Full sync pipeline
1. Load note with 5 flashcards
2. Call generate_cards()
3. Call sync_to_anki()
4. Verify 5 cards exist in Anki deck
5. Verify card content matches note
```

#### 3.2 Update Detection
```
Test: Detect note changes
1. Create note, sync to Anki
2. Modify note content
3. Call sync_to_anki() with --force-regen=false
4. Verify cards are updated (not duplicated)
```

#### 3.3 Media Handling
```
Test: Image sync
1. Note with ![[image.png]]
2. Call sync_to_anki()
3. Verify image copied to Anki media folder
4. Verify card renders image in Anki
```

### 4. Obsidian Integration Tests

#### 4.1 Note Discovery
```
Test: Find all notes with flashcards
1. Create notes in various folders
2. Call discover_notes()
3. Verify all flashcard-containing notes found
```

#### 4.2 Frontmatter Parsing
```
Test: Deck assignment from YAML
1. Note with deck: "MyDeck::SubDeck"
2. Call parse_frontmatter()
3. Verify deck correctly parsed
```

### 5. AI Integration Tests

#### 5.1 Local AI (Ollama)
```
Test: Offline generation
1. Set ai_provider: "ollama"
2. Network unavailable
3. Call generate_flashcards()
4. Verify cards generated locally
```

#### 5.2 Deduplication
```
Test: Semantic similarity detection
1. Existing card: "What is Python?"
2. New card: "What is the Python language?"
3. Call check_similarity()
4. Verify >80% similarity detected, card skipped
```

---

## E2E Test Scenarios

### 6. Complete Workflow Tests

#### 6.1 Happy Path: Note to Anki
```
Feature: Full homeschool pipeline
Given:
  - Obsidian vault with note containing flashcards
  - Anki running with AnkiConnect enabled
When:
  - User runs: homeschool sync
Then:
  - Notes discovered and parsed
  - Flashcards generated via AI
  - Cards synced to Anki deck
  - Success message displayed
```

#### 6.2 Error Recovery Path
```
Feature: Retry on AnkiConnect failure
Given:
  - AnkiConnect fails first 2 attempts
When:
  - User runs: homeschool sync
Then:
  - Retry with exponential backoff
  - Third attempt succeeds
  - Sync completes with warning log
```

#### 6.3 Offline Mode
```
Feature: Queue cards when offline
Given:
  - ai_provider: "ollama"
  - Network disconnected
When:
  - User runs: homeschool sync
Then:
  - Cards generated using local AI
  - Sync queued for later
  - Success message with "queued" status
```

---

## Test Infrastructure

### 7. Test Setup

#### 7.1 Dependencies
```python
# requirements-dev.txt
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
pytest-asyncio>=0.21.0
requests-mock>=1.10.0
vcrpy>=5.0.0  # For recording HTTP interactions
httpx>=0.24.0  # Async HTTP client
```

#### 7.2 Fixtures
```python
# tests/fixtures/
anki_connect_mock.yaml    # Recorded AnkiConnect responses
sample_notes/             # Sample markdown notes
test_config.yaml          # Test configuration
```

#### 7.3 Test Databases
- **SQLite**: In-memory test database for unit tests
- **ChromaDB**: Ephemeral temp directory for integration tests
- **Anki**: Mock responses, not real Anki instance

### 8. Fixtures Structure
```
tests/
├── __init__.py
├── conftest.py           # Shared fixtures
├── unit/
│   ├── __init__.py
│   ├── test_note_parser.py
│   ├── test_anki_connect.py
│   ├── test_ai_generator.py
│   └── test_config_validation.py
├── integration/
│   ├── __init__.py
│   ├── test_sync_workflow.py
│   ├── test_anki_integration.py
│   └── test_media_handling.py
├── e2e/
│   ├── __init__.py
│   ├── test_full_pipeline.py
│   └── test_offline_mode.py
├── fixtures/
│   ├── sample_notes/
│   │   ├── basic_flashcards.md
│   │   ├── cloze_deletions.md
│   │   └── with_media.md
│   └── test_config.yaml
└── mocks/
    └── anki_connect_responses.yaml
```

---

## Test Execution

### 9. Running Tests

```bash
# All tests
pytest

# Unit tests only (fast)
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v --mock-anki

# E2E tests (slow)
pytest tests/e2e/ -v

# With coverage
pytest --cov=homeschool --cov-report=html

# Single test file
pytest tests/unit/test_note_parser.py -v

# With verbose output
pytest -vv --tb=long
```

### 10. CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/unit/ --cov=homeschool
      - run: pytest tests/integration/
      - run: pytest tests/e2e/
        if: github.event_name == 'push'
```

---

## Coverage Targets

### 11. Coverage Requirements

| Module | Target Coverage | Priority |
|--------|-----------------|----------|
| `note_parser.py` | 95% | Critical |
| `anki_connect.py` | 90% | Critical |
| `ai_generator.py` | 85% | High |
| `sync_engine.py` | 90% | Critical |
| `config.py` | 80% | High |
| `media_handler.py` | 75% | Medium |

### 12. Coverage Enforcement
```bash
# Fail if coverage drops below threshold
pytest --cov=homeschool --cov-fail-under=80
```

---

## Testing Improvements from Plan 02 & 03

### 13. Tests for Improvement Plan 02 Features

#### 13.1 Robustness Tests
- [ ] Test Docker health check endpoints
- [ ] Test retry with exponential backoff
- [ ] Test transaction rollback on sync failure
- [ ] Test config validation with missing fields
- [ ] Test log rotation after size threshold

#### 13.2 Usability Tests
- [ ] Test `homeschool init` command
- [ ] Test `homeschool status` command
- [ ] Test `homeschool logs` command
- [ ] Test progress bar display
- [ ] Test tab completion

#### 13.3 Integration Tests
- [ ] Test AnkiConnect duplicate detection
- [ ] Test bulk export/import
- [ ] Test Obsidian plugin trigger

### 14. Tests for Improvement Plan 03 Features

#### 14.1 ID Tracking Tests
- [ ] Test unique ID added to note frontmatter
- [ ] Test content hash change detection
- [ ] Test `--force-regen` bypasses cache
- [ ] Test update detection after edit

#### 14.2 AI Quality Tests
- [ ] Test confidence scoring
- [ ] Test user feedback loop
- [ ] Test review queue display
- [ ] Test SuperMemo prompt compliance

#### 14.3 Deduplication Tests
- [ ] Test semantic similarity check
- [ ] Test ChromaDB embeddings lookup
- [ ] Test >85% similarity skip
- [ ] Test config option wiring

#### 14.4 Offline Tests
- [ ] Test Ollama provider fallback
- [ ] Test offline queue system
- [ ] Test local embedding cache

---

## Test Data Management

### 15. Mock Data Strategy
- **AnkiConnect**: Use pre-recorded VCR cassettes
- **AI generation**: Mock OpenAI/Ollama responses
- **File system**: Use `tmp_path` fixtures
- **Databases**: Use in-memory SQLite

### 16. Test Isolation
- Each test cleans up its artifacts
- Use unique identifiers per test run
- Mock external services completely

---

## Continuous Improvement

### 17. Test Metrics to Track
- Test pass rate (target: >98%)
- Test execution time (target: <5 min unit tests)
- Flaky test count (target: 0)
- Coverage trend over time

### 18.定期Test Review
- Weekly: Review failed tests
- Monthly: Add tests for new features
- Quarterly: Coverage audit and gap analysis

---

## Recommended Implementation Order

### Phase 1: Foundation (Week 1-2)
- [ ] Set up pytest and conftest.py
- [ ] Create fixture files
- [ ] Write unit tests for note_parser.py
- [ ] Write unit tests for config validation

### Phase 2: Core Integration (Week 3-4)
- [ ] Write AnkiConnect mock adapters
- [ ] Write integration tests for sync workflow
- [ ] Add media handling tests
- [ ] Set up CI/CD pipeline

### Phase 3: Advanced Features (Week 5-6)
- [ ] Add AI quality scoring tests
- [ ] Add deduplication tests
- [ ] Add offline mode tests
- [ ] Write E2E test scenarios

### Phase 4: Polish (Week 7-8)
- [ ] Achieve coverage targets
- [ ] Fix flaky tests
- [ ] Add performance benchmarks
- [ ] Document test patterns

---

## Related Documents
- improvement_plan_02.md - Core functionality to test
- improvement_plan_03.md - Enhanced features to test
- docs/Learning Workflow.md - Workflow under test
- docs/Local AI Workflow.md - AI features under test