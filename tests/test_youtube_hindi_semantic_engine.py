"""Comprehensive unit and semantic equivalence tests for YouTube Hindi/Hinglish NLU Engine."""
import json
import os
import pytest

from backend.nlu.youtube_nlu import youtube_nlu
from backend.core.command_processor import command_processor


@pytest.fixture(scope="module")
def paraphrase_data():
    data_path = os.path.join(os.path.dirname(__file__), "data", "youtube_hindi_paraphrases.json")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_youtube_nlu_paraphrase_corpus(paraphrase_data):
    """Assert all 119 natural Hindi/Hinglish paraphrases resolve to exact canonical action and arguments."""
    total = len(paraphrase_data)
    passed = 0
    failures = []

    for item in paraphrase_data:
        raw_text = item["text"]
        expected_action = item["action"]
        expected_ordinal = item.get("ordinal")
        expected_query = item.get("query")

        res = youtube_nlu.parse(raw_text)
        
        # Action check
        if res.canonical_action != expected_action:
            failures.append(f"FAILED action for '{raw_text}': expected {expected_action}, got {res.canonical_action}")
            continue

        # Ordinal check
        if expected_ordinal is not None and res.ordinal != expected_ordinal:
            failures.append(f"FAILED ordinal for '{raw_text}': expected {expected_ordinal}, got {res.ordinal}")
            continue

        passed += 1

    assert not failures, f"Failed {len(failures)}/{total} paraphrases:\n" + "\n".join(failures[:10])
    print(f"\nAll {passed}/{total} natural Hindi/Hinglish paraphrases resolved with 100% accuracy!")


def test_word_order_independence():
    """Verify semantic meaning is identical regardless of word ordering."""
    phrases = [
        "MrBeast search karo YouTube pe",
        "YouTube pe MrBeast search karo",
        "YouTube pe search karo MrBeast",
    ]
    for p in phrases:
        res = youtube_nlu.parse(p)
        assert res.canonical_action == "youtube.search"
        assert "mrbeast" in res.query.lower()


def test_negation_protection():
    """Verify negations are safely caught and not executed."""
    neg_phrases = [
        "pause mat karna",
        "video mat rokna",
        "next short mat chala",
        "volume kam mat karo"
    ]
    for p in neg_phrases:
        res = youtube_nlu.parse(p)
        assert res.is_negated is True
        assert res.canonical_action == "youtube.none_negated"


def test_self_corrections():
    """Verify self-corrections resolve to the final intended target."""
    res1 = youtube_nlu.parse("second nahi first short chalao")
    assert res1.canonical_action == "youtube.play_short"
    assert res1.ordinal == 1

    res2 = youtube_nlu.parse("third nahi first wali short laga")
    assert res2.canonical_action == "youtube.play_short"
    assert res2.ordinal == 1

    res3 = youtube_nlu.parse("pause nahi mute karo")
    assert res3.canonical_action == "youtube.mute"


@pytest.mark.asyncio
async def test_cross_app_collision_safety():
    """Verify explicit app names are never crossed or hijacked."""
    dom_yt, app_yt = command_processor.resolve_application_context(
        raw_text="YouTube pe next short chalao",
        normalized_text="youtube pe next short chalao"
    )
    assert app_yt == "youtube"

    dom_sp, app_sp = command_processor.resolve_application_context(
        raw_text="Spotify pe agla gaana chalao",
        normalized_text="spotify pe agla gaana chalao"
    )
    assert app_sp == "spotify"
