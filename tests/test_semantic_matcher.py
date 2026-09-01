"""Unit tests for SemanticMatcher confidence scoring and entity ranking."""
import pytest
from backend.ai.semantic_matcher import MatchConfidenceTier, SemanticMatcher, semantic_matcher


def test_semantic_matcher_exact_phrase():
    query = "expensive gift for laila"
    candidate = {
        "id": "abc12345678",
        "title": "Airport Masti of Aarush & Laila - Expensive Gift For Laila",
        "channel": "Aarush Bhola Fit",
        "duration": "40:00",
        "is_short": False,
    }
    score, matched = semantic_matcher.calculate_similarity_score(
        user_query=query,
        candidate_title=candidate["title"],
        candidate_channel=candidate["channel"],
    )
    assert score >= 0.70
    assert "expensive" in matched
    assert "gift" in matched
    assert "laila" in matched


def test_semantic_matcher_rejects_unrelated():
    query = "expensive gift for laila"
    unrelated_candidate = {
        "id": "xyz98765432",
        "title": "College Mein Hui Ladai || NCR Days || Girliyapa Diaries",
        "channel": "Girliyapa Diaries",
        "duration": "07:56",
        "is_short": False,
    }
    score, matched = semantic_matcher.calculate_similarity_score(
        user_query=query,
        candidate_title=unrelated_candidate["title"],
        candidate_channel=unrelated_candidate["channel"],
    )
    assert score < 0.20


def test_semantic_matcher_penalizes_shorts():
    query = "samay raina standup"
    short_candidate = {
        "id": "short123456",
        "title": "Samay Raina Standup Comedy Funny Moment",
        "channel": "Comedy Clips",
        "duration": "0:15",
        "is_short": True,
    }
    score, matched = semantic_matcher.calculate_similarity_score(
        user_query=query,
        candidate_title=short_candidate["title"],
        candidate_channel=short_candidate["channel"],
        is_short=True,
    )
    assert score < 0.40  # Heavily penalized for shorts


def test_rank_candidates_sorting():
    query = "expensive gift for laila"
    candidates = [
        {"id": "1", "title": "Reacting to Traitors Season 2", "channel": "Fukra Insaan", "is_short": False},
        {"id": "2", "title": "Airport Masti of Aarush & Laila - Expensive Gift For Laila", "channel": "Aarush Bhola", "is_short": False},
        {"id": "3", "title": "Best Gifts Under 500", "channel": "Tech Channel", "is_short": False},
    ]
    ranked = semantic_matcher.rank_candidates(query, candidates)
    assert ranked[0].id == "2"
    assert ranked[0].tier == MatchConfidenceTier.VERY_HIGH
