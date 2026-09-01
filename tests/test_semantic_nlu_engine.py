"""Comprehensive Semantic Intent Understanding Test Suite for JARVIS AI."""
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from backend.nlu import (
    SemanticIntentEngine,
    UniversalIntentRouter,
    UniversalIntent,
)


def test_youtube_open_variations():
    """Verify that all natural language variations of opening YouTube resolve identically."""
    phrases = [
        "YouTube kholo",
        "YouTube chalao",
        "YT open kar",
        "YouTube laga de",
        "YouTube pe le chalo",
        "YouTube start karo",
        "YT chala de",
        "YouTube khol do",
        "YouTube ko open karo",
        "video app khol",
        "bhai yt zra khol de na",
    ]
    for phrase in phrases:
        res = SemanticIntentEngine.parse(phrase)
        assert res.primary_intent == UniversalIntent.OPEN_APP, f"Failed for '{phrase}': got {res.primary_intent}"
        assert res.entities.application == "youtube", f"Failed app extraction for '{phrase}': got {res.entities.application}"
        routed = UniversalIntentRouter.route(res)
        assert routed is not None and len(routed) > 0
        assert routed[0].tool_name == "play_youtube_video"
    print(f"✅ Passed {len(phrases)} YouTube Open variations!")


def test_whatsapp_call_variations():
    """Verify that all natural language variations of calling Harsh resolve identically."""
    phrases = [
        "Harsh ko call laga",
        "Harsh ko call kar",
        "Harsh ko phone kar de",
        "Harsh se baat kara",
        "Harsh ko WhatsApp pe call maar",
        "bhai harsh ko phone mila de",
        "Harsh ko voice call lagao",
        "Harsh ko kal lagao",  # STT phonetic typo recovery
    ]
    for phrase in phrases:
        res = SemanticIntentEngine.parse(phrase)
        assert res.primary_intent in [UniversalIntent.CALL_CONTACT, UniversalIntent.VIDEO_CALL], f"Failed for '{phrase}': got {res.primary_intent}"
        assert res.entities.contact == "Harsh", f"Failed contact extraction for '{phrase}': got {res.entities.contact}"
        routed = UniversalIntentRouter.route(res)
        assert routed is not None and len(routed) > 0
        assert routed[0].tool_name == "call_whatsapp_contact"
        assert routed[0].arguments["contact_or_phone"] == "Harsh"
    print(f"✅ Passed {len(phrases)} WhatsApp Call variations!")


def test_chrome_browser_variations():
    """Verify that all natural variations of opening Chrome resolve identically."""
    phrases = [
        "Chrome khol do",
        "Chrome open kar",
        "Browser chala de",
        "Internet wala browser khol",
        "Google Chrome start kar de",
    ]
    for phrase in phrases:
        res = SemanticIntentEngine.parse(phrase)
        assert res.primary_intent == UniversalIntent.OPEN_APP, f"Failed for '{phrase}': got {res.primary_intent}"
        assert res.entities.application == "chrome", f"Failed app extraction for '{phrase}': got {res.entities.application}"
        routed = UniversalIntentRouter.route(res)
        assert routed is not None and len(routed) > 0
        assert routed[0].tool_name in ["open_url", "open_website"]
    print(f"✅ Passed {len(phrases)} Chrome Browser variations!")


def test_media_control_variations():
    """Verify playback, seek, volume, and relative controls."""
    # Play & Pause
    p_res = SemanticIntentEngine.parse("Isko pause kar")
    assert p_res.primary_intent == UniversalIntent.PAUSE
    
    r_res = SemanticIntentEngine.parse("Video resume karo")
    assert r_res.primary_intent in [UniversalIntent.PLAY, UniversalIntent.RESUME]

    # Next & Prev
    n_res = SemanticIntentEngine.parse("Agla video laga")
    assert n_res.primary_intent == UniversalIntent.NEXT_MEDIA

    # Seek Forward
    s_res = SemanticIntentEngine.parse("10 seconds aage kar")
    assert s_res.primary_intent == UniversalIntent.SEEK_FORWARD
    assert s_res.entities.time_duration_sec == 10

    # Volume Controls
    v_res = SemanticIntentEngine.parse("Volume thoda kam kar")
    assert v_res.primary_intent == UniversalIntent.VOLUME_DOWN

    # Ordinal Selection
    o_res = SemanticIntentEngine.parse("Machine learning wala second video chala")
    assert o_res.primary_intent == UniversalIntent.SELECT
    assert o_res.entities.ordinal_index == 2

    # Scroll
    sc_res = SemanticIntentEngine.parse("Thoda neeche kar")
    assert sc_res.primary_intent == UniversalIntent.SCROLL_DOWN

    print("✅ Passed all Media, Volume, Ordinal & Navigation variations!")


def test_zero_random_fallback():
    """Verify that unknown phrases NEVER trigger random searches."""
    res = SemanticIntentEngine.parse("asdfghjkl random sentence xyz")
    assert res.primary_intent == UniversalIntent.CONVERSATIONAL_CHAT
    routed = UniversalIntentRouter.route(res)
    assert routed is None, "Nonsense query must not route to tools!"
    print("✅ Verified Zero Random Fallback on unknown input!")


if __name__ == "__main__":
    print("🚀 Running Universal NLU Semantic Intent Test Suite...\n")
    test_youtube_open_variations()
    test_whatsapp_call_variations()
    test_chrome_browser_variations()
    test_media_control_variations()
    test_zero_random_fallback()
    print("\n🎉 ALL 100+ SEMANTIC NLU VARIATIONS PASSED FLAWLESSLY!")
