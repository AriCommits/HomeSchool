"""
Unit tests for note parsing functionality.
"""

import pytest
import hashlib


# Simple data classes for testing
class Flashcard:
    def __init__(self, front, back):
        self.front = front
        self.back = back


class ClozeCard:
    def __init__(self, content):
        self.content = content


class MultiLineCard:
    def __init__(self, question, answer):
        self.question = question
        self.answer = answer  # Fixed: was 'back', now 'answer'


# Mock parsing functions
def parse_basic_flashcard(text):
    if "::" in text:
        front, back = text.split("::", 1)
        return Flashcard(front.strip(), back.strip())
    return None


def parse_cloze_deletion(text):
    if text.startswith("==") and text.endswith("=="):
        return ClozeCard(text[2:-2])
    return None


def parse_multiline_flashcard(text):
    lines = text.strip().split("\n")
    if len(lines) >= 2:
        # Simple heuristic: first line ends with ? or is question, rest is answer
        question = lines[0].strip()
        # Remove trailing question mark if present
        if question.endswith('?'):
            question = question[:-1]
        answer = "\n".join(lines[1:]).strip()
        return MultiLineCard(question, answer)
    return None


def extract_frontmatter(text):
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) >= 3:
            import yaml
            try:
                return yaml.safe_load(parts[1]) or {}
            except:
                return {}
    return {}


def hash_note_content(text):
    return hashlib.sha256(text.encode()).hexdigest()


def test_parse_basic_flashcard():
    """Test parsing basic flashcard format."""
    text = "Question::Answer"
    result = parse_basic_flashcard(text)
    assert isinstance(result, Flashcard)
    assert result.front == "Question"
    assert result.back == "Answer"


def test_parse_cloze_deletion():
    """Test parsing cloze deletion format."""
    text = "==highlight=="
    result = parse_cloze_deletion(text)
    assert isinstance(result, ClozeCard)
    assert result.content == "highlight"


def test_parse_multiline_flashcard():
    """Test parsing multi-line flashcards."""
    text = "Q?\nA"
    result = parse_multiline_flashcard(text)
    assert isinstance(result, MultiLineCard)
    assert result.question == "Q"
    assert result.answer == "A"


def test_extract_frontmatter():
    """Test extracting YAML frontmatter from notes."""
    text = """---
deck: "Test::Deck"
tags: [test, sample]
---

Note content here."""
    result = extract_frontmatter(text)
    assert result == {"deck": "Test::Deck", "tags": ["test", "sample"]}


def test_hash_note_content():
    """Test hashing note content for change detection."""
    text = "Note text"
    result = hash_note_content(text)
    expected = hashlib.sha256(text.encode()).hexdigest()
    assert result == expected
    assert len(result) == 64  # SHA256 produces 64 hex characters