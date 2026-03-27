# Improvement Plan 03: User-Driven Enhancements Based on Community Research

## Overview
This plan addresses common pain points discovered through Reddit discussions and GitHub issue tracking for Obsidian-Anki-flashcard systems. The focus is on implementing solutions that are easily integrable with the current Homeschool workflow, addressing the most frequently reported frustrations.

## Pain Points & Solutions

### 1. Flashcard ID Tracking & Update Detection
**Reddit/GitHub Issue**: "Nothing to do. Everything is up to date." - Updates not recognized
- **Source**: flashcards-obsidian issue #223, ObsidianToAnki issue #665
- **Problem**: When notes are updated, generated flashcards aren't recognized as changed; no IDs added to notes

**Solution for Homeschool**:
- Implement unique ID tagging in note frontmatter on first card generation
- Store mapping between note content hash and Anki card IDs
- Compare content hashes to detect changes (not just timestamps)
- Add `--force-regen` flag to bypass cache for manual refresh
- Track "last processed hash" per note to detect meaningful changes

### 2. AI Flashcard Quality Improvements
**Reddit Issue**: "AI-generated flashcards are unreliable... 70% wrong info"
- **Source**: r/Anki discussion on AI-generated flashcards
- **Problem**: AI doesn't know what's hard for user; generates irrelevant or incorrect cards

**Solution for Homeschool**:
- Add user feedback loop: mark generated cards as "useful" or "not useful" 
- Use AI with specific prompt following SuperMemo's 20 rules
- Implement confidence scoring for generated cards
- Add manual review queue: show generated cards before adding to Anki
- Track which cards user skips/flags for deletion

### 3. Semantic Deduplication
**Reddit/GitHub Issue**: Duplicate cards being created; no way to detect similarity
- **Source**: obsidianki features, GitHub duplicates issues
- **Problem**: AI generates similar cards; no semantic similarity check

**Solution for Homeschool**:
- Use embeddings (from local Ollama) to compute semantic similarity
- Check new AI-generated cards against existing Anki cards
- Skip cards with >85% similarity to existing cards
- Store embeddings index in ChromaDB for fast lookup
- Add config option: `skip_similar_cards: true`

### 4. Large Deck Sync Performance
**GitHub Issue**: "30,000 cards causes 8-10 second sync delays"
- **Source**: ObsidianToAnki issue #565
- **Problem**: Plugin scans entire Anki collection instead of target deck

**Solution for Homeschool**:
- Add deck-specific sync scope: only check cards in specified deck
- Implement batch processing with progress indicators
- Add caching layer: cache Anki card metadata locally
- Background sync option: run incrementally, not all at once

### 5. Image & Media Handling
**GitHub Issue**: Images not rendering in Anki after sync
- **Source**: Obsidian-Anki-Sync issue #17, Yanki-obsidian docs
- **Problem**: Local image paths break when synced to Anki

**Solution for Homeschool**:
- Detect media references in notes (`![[image.png]]`)
- Copy media files to Anki media folder before sync
- Convert Obsidian Wiki-links to Anki-compatible paths
- Add `--verify-media` flag to check all references exist
- Support relative paths and cross-vault references

### 6. Offline-First Local AI
**Reddit Issue**: "Privacy concerns... data leaves my machine"
- **Source**: r/LocalLLaMA, r/ObsidianMD discussions
- **Problem**: Users want fully offline AI processing

**Solution for Homeschool**:
- Add Ollama integration as alternative to cloud APIs
- Use quantized models (Phi-3-mini, TinyLlama) for CPU-only environments
- Add config: `ai_provider: "ollama"` | `"openai"` | `"anthropic"`
- Implement offline fallback: queue cards when offline, process later
- Cache Ollama embeddings locally for duplicate detection

### 7. AnkiConnect Error Resilience
**Reddit Issue**: "Sync failed. Internet offline" - no recovery mechanism
- **Source**: r/Anki sync discussions, AnkiDroid issues
- **Problem**: Network failures break sync with no retry or recovery

**Solution for Homeschool**:
- Implement retry with exponential backoff (3 attempts default)
- Add `--offline-mode` to queue operations for later sync
- Log detailed error messages for debugging
- Add connection health check before sync: `anki-connect --health`
- Create manual recovery mode: list failed cards for user review

### 8. FSRS Algorithm Integration
**Reddit Issue**: Using Anki's built-in scheduling, want better algorithms
- **Source**: TrueRecall app, SRAI plugin discussions
- **Problem**: Default Anki scheduling less efficient than FSRS

**Solution for Homeschool**:
- Add FSRS v6 algorithm support for scheduling decisions
- Export FSRS parameters to Anki for cards created via Homeschool
- Track user performance metrics (recall rate per card)
- Add configurable presets: "aggressive", "balanced", "conservative"

### 9. Note Coverage Tracking
**Reddit/PK GitHub Issue**: Don't know what content has been tested
- **Source**: AB1908/obsidian-spaced-repetition plugin
- **Problem**: No metric for "how much of this note have I turned into flashcards"

**Solution for Homeschool**:
- Track percentage of note converted to flashcards
- Generate coverage report: which notes have full cards, partial, none
- Add "coverage score" to each note in the dashboard
- Suggest underexplored sections for flashcard generation

### 10. Multiple Deck & Tag Management
**GitHub Issue**: Want deck assignment based on file/folder structure
- **Source**: jannusgoe/obsidian-ankisync, Yanki-obsidian
- **Problem**: Want automatic deck assignment without manual config

**Solution for Homeschool**:
- Parse note hierarchy for deck assignment: `folder/subfolder/note`
- Add frontmatter support: `deck: "MyDeck::SubDeck"`
- Auto-create missing decks in Anki on sync
- Support tag inheritance from parent folders

## Implementation Priority

### Phase 1: Critical Sync Fixes (Week 1)
- [ ] Implement ID tracking in note frontmatter
- [ ] Add content hash comparison for change detection
- [ ] Add retry mechanism for AnkiConnect failures
- [ ] Basic duplicate detection (exact match)

### Phase 2: Quality & Performance (Week 2)
- [ ] Add semantic deduplication with embeddings
- [ ] Implement deck-specific sync scope
- [ ] Add media file handling and copy
- [ ] Add user review queue before Anki sync

### Phase 3: Local AI & Advanced Features (Week 3)
- [ ] Add Ollama provider integration
- [ ] Add offline mode / queue system
- [ ] Implement FSRS export parameters
- [ ] Add note coverage tracking

### Phase 4: Polish (Week 4)
- [ ] Add progress indicators for large syncs
- [ ] Comprehensive error messages
- [ ] Configuration validation at startup
- [ ] Documentation updates

## Integration Points with Current Workflow

The solutions above align with current project structure:
- Uses ChromaDB (already integrated) for embeddings storage
- Uses existing AnkiConnect wrapper for sync
- Complements existing note processing pipeline
- Adds minimal new dependencies: `numpy` (embeddings), `ollama` (optional)

## Acceptance Criteria

1. Flashcard updates detected within 5 seconds for notes <1000 cards
2. Semantic deduplication rejects >80% of similar cards
3. Media files render correctly in Anki from Obsidian notes
4. Offline mode works without internet for full pipeline
5. Error recovery requires no manual intervention for network failures

## Dependencies Added

- `numpy` - For embeddings computation (if using local)
- `ollama` (optional) - For local AI processing
- `faiss-cpu` - For fast similarity search (optional)

## Related Projects Studied

- flashcards-obsidian (reuseman) - ID tracking fix #197
- Yanki-obsidian - Pure markdown sync approach
- Obsidianki - CLI tool with semantic deduplication
- TrueRecall - FSRS-integrated Obsidian plugin
- SRAI - Spaced Repetition AI plugin for Obsidian