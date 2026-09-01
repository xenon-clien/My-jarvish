"""Unit tests for ContextMemory follow-up resolution."""
import pytest
from backend.ai.context_memory import ContextMemory
from backend.ai.semantic_matcher import ScoredCandidate


def test_context_memory_ordinal_resolution():
    memory = ContextMemory()
    candidates = [
        ScoredCandidate(id="vid1", title="Aarush & Laila Episode 1", confidence_score=0.9),
        ScoredCandidate(id="vid2", title="Expensive Gift for Laila", confidence_score=0.85),
        ScoredCandidate(id="vid3", title="Samay Raina Standup Comedy", confidence_score=0.7),
    ]
    memory.record_search("youtube", "laila video", candidates)

    # Test "dusra wala"
    match = memory.resolve_followup("dusra wala lagao")
    assert match is not None
    assert match.id == "vid2"
    assert match.title == "Expensive Gift for Laila"

    # Test "teesra wala"
    match3 = memory.resolve_followup("nahi teesra wala chalao")
    assert match3 is not None
    assert match3.id == "vid3"


def test_context_memory_descriptive_filter():
    memory = ContextMemory()
    candidates = [
        ScoredCandidate(id="vid1", title="Reacting to Funny Memes", confidence_score=0.9),
        ScoredCandidate(id="vid2", title="Expensive Gift For Laila Airport Masti", confidence_score=0.85),
    ]
    memory.record_search("youtube", "laila video", candidates)

    match = memory.resolve_followup("isme se expensive gift wala chalao")
    assert match is not None
    assert match.id == "vid2"
