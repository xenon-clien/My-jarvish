"""Automated Reliability Test Suite for JARVIS NLU, Language Normalizer & Action Router.

Tests 50+ real-world Hindi, Hinglish, and English phrasing variations across all 34 capabilities:
- YouTube Play, Pause, Resume, Seek, Speed, Fullscreen, Shorts, Replay
- Ordinal selection for 3-Column Home Grid & Watch Sidebar
- Exact compound timestamp parsing (5m30s, 12m, 45s, 5:30)
- System volume, app launcher, scrolling, and cleanup
"""
import pytest
from backend.nlu import SemanticIntentEngine, UniversalIntentRouter, LanguageNormalizer, UniversalIntent
from backend.nlu.entities import EntityResolver


class TestLanguageNormalizer:
    """Test phonetic and verb normalizations for Hindi, Hinglish, and English."""

    def test_stt_phonetic_repairs(self):
        assert LanguageNormalizer.normalize("video ko pouse kar")[0] == "video ko pause karo"
        assert LanguageNormalizer.normalize("isko rijum karo")[0] == "isko resume karo"
        assert LanguageNormalizer.normalize("screen fulskrin karo")[0] == "screen fullscreen karo"
        assert LanguageNormalizer.normalize("channel sabscraib karo")[0] == "channel subscribe karo"

    def test_verb_normalizations(self):
        assert "pause karo" in LanguageNormalizer.normalize("video rok do")[0]
        assert "pause karo" in LanguageNormalizer.normalize("isko roko")[0]
        assert "chalao" in LanguageNormalizer.normalize("video chla de")[0]
        assert "kholo" in LanguageNormalizer.normalize("chrome khol de")[0]

    def test_number_word_normalization(self):
        norm, _ = LanguageNormalizer.normalize("dusri video chalao")
        assert "2nd" in norm or "2" in norm

        norm2, _ = LanguageNormalizer.normalize("panch minute tees second")
        assert "5" in norm2 and "30" in norm2


class TestEntityExtraction:
    """Test exact compound timestamps, ordinals, and parameters."""

    def test_compound_timestamp_extraction(self):
        entities = EntityResolver.resolve_entities("video ko 5 minute 30 second par lagao")
        assert entities.time_str == "5m30s"
        assert entities.time_duration_sec == 330

    def test_colon_timestamp_extraction(self):
        entities = EntityResolver.resolve_entities("video ko 5:30 par le jao")
        assert entities.time_str == "5m30s"
        assert entities.time_duration_sec == 330

    def test_minute_only_extraction(self):
        entities = EntityResolver.resolve_entities("12 minute par karo")
        assert entities.time_str == "12m"
        assert entities.time_duration_sec == 720

    def test_seconds_only_extraction(self):
        entities = EntityResolver.resolve_entities("45 second par karo")
        assert entities.time_str == "45s"
        assert entities.time_duration_sec == 45

    def test_ordinal_resolution(self):
        assert EntityResolver.resolve_entities("pehli video chalao").ordinal_index == 1
        assert EntityResolver.resolve_entities("dusri video chalao").ordinal_index == 2
        assert EntityResolver.resolve_entities("3rd video chalao").ordinal_index == 3
        assert EntityResolver.resolve_entities("chauthi video chalao").ordinal_index == 4

    def test_self_correction_ordinal(self):
        # Pick latest spoken ordinal when user corrects themselves
        entities = EntityResolver.resolve_entities("play 1st second video")
        assert entities.ordinal_index == 2


class TestSemanticIntentClassification:
    """Test 100% precision intent classification across natural Hindi/Hinglish variations."""

    @pytest.mark.parametrize("command,expected_intent", [
        ("video pause karo", UniversalIntent.PAUSE),
        ("video rok do", UniversalIntent.PAUSE),
        ("isko rok", UniversalIntent.PAUSE),
        ("stop the video", UniversalIntent.PAUSE),
        ("pause video", UniversalIntent.PAUSE),
        ("resume video", UniversalIntent.RESUME),
        ("unpause karo", UniversalIntent.RESUME),
        ("video chalao", UniversalIntent.RESUME),
        ("10 second aage karo", UniversalIntent.SEEK_FORWARD),
        ("fast forward 10 sec", UniversalIntent.SEEK_FORWARD),
        ("10 second peeche karo", UniversalIntent.SEEK_BACKWARD),
        ("10s rewind", UniversalIntent.SEEK_BACKWARD),
        ("video ko 5 minute 30 second par lagao", UniversalIntent.SEEK_TIMESTAMP),
        ("12 minute par karo", UniversalIntent.SEEK_TIMESTAMP),
        ("5:30 par chalao", UniversalIntent.SEEK_TIMESTAMP),
        ("speed badhao", UniversalIntent.SPEED_UP),
        ("speed kam karo", UniversalIntent.SPEED_DOWN),
        ("fullscreen karo", UniversalIntent.FULLSCREEN),
        ("theater mode lagao", UniversalIntent.THEATER_MODE),
        ("miniplayer chalao", UniversalIntent.MINIPLAYER),
        ("subtitles on karo", UniversalIntent.CAPTIONS),
        ("video replay karo", UniversalIntent.REPLAY),
        ("agla short dikhao", UniversalIntent.NEXT_SHORT),
        ("pichla short dikhao", UniversalIntent.PREV_SHORT),
        ("pehli video chalao", UniversalIntent.SELECT),
        ("dusri video chalao", UniversalIntent.SELECT),
        ("3rd video chalao", UniversalIntent.SELECT),
        ("chauthi video chalao", UniversalIntent.SELECT),
        ("scroll karo", UniversalIntent.SCROLL_DOWN),
        ("upar scroll karo", UniversalIntent.SCROLL_UP),
        ("video like karo", UniversalIntent.LIKE),
        ("video dislike karo", UniversalIntent.DISLIKE),
        ("channel subscribe karo", UniversalIntent.SUBSCRIBE),
        ("video share karo", UniversalIntent.SHARE),
        ("comments dikhao", UniversalIntent.COMMENTS_VIEW),
        ("volume badhao", UniversalIntent.VOLUME_UP),
        ("volume kam karo", UniversalIntent.VOLUME_DOWN),
        ("mute karo", UniversalIntent.MUTE_AUDIO),
        ("unmute karo", UniversalIntent.UNMUTE_AUDIO),
        ("chrome kholo", UniversalIntent.OPEN_APP),
        ("notepad kholo", UniversalIntent.OPEN_APP),
        ("calculator kholo", UniversalIntent.OPEN_APP),
        ("faltu tabs band karo", UniversalIntent.CLEAN_JUNK),
    ])
    def test_intent_mapping(self, command: str, expected_intent: UniversalIntent):
        nlu_res = SemanticIntentEngine.parse(command)
        assert nlu_res.primary_intent == expected_intent, f"Failed for '{command}': expected {expected_intent}, got {nlu_res.primary_intent}"


class TestRouterToolMapping:
    """Test that all intents route to concrete, registered executable tools."""

    def test_pause_routing(self):
        nlu_res = SemanticIntentEngine.parse("video pause karo")
        routed = UniversalIntentRouter.route(nlu_res)
        assert routed is not None and len(routed) > 0
        assert routed[0].tool_name == "control_media"
        assert routed[0].arguments.get("action") == "pause"

    def test_timestamp_seek_routing(self):
        nlu_res = SemanticIntentEngine.parse("video ko 5 minute 30 second par lagao")
        routed = UniversalIntentRouter.route(nlu_res)
        assert routed is not None and len(routed) > 0
        assert routed[0].tool_name == "control_media"
        assert routed[0].arguments.get("action") == "seek_timestamp"
        assert routed[0].arguments.get("time_str") == "5m30s"

    def test_home_grid_selection_routing(self):
        nlu_res = SemanticIntentEngine.parse("dusri video chalao")
        routed = UniversalIntentRouter.route(nlu_res)
        assert routed is not None and len(routed) > 0
        assert routed[0].tool_name == "click_screen_video"
        assert routed[0].arguments.get("index") == 2

    def test_app_launch_routing(self):
        nlu_res = SemanticIntentEngine.parse("notepad kholo")
        routed = UniversalIntentRouter.route(nlu_res)
        assert routed is not None and len(routed) > 0
        assert routed[0].tool_name == "open_application" or routed[0].tool_name == "launch_app"
        assert routed[0].arguments.get("app_name") == "notepad"
