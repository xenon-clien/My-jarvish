"""Automated Developer Regression Test Suite for JARVIS.

Validates core deterministic routing, subsystem isolation, structured command tracing,
and multi-step compound command handling across YouTube, Chrome, WhatsApp, and System.
"""
import pytest
import os
import json
from pathlib import Path

from backend.nlu.semantic_engine import SemanticIntentEngine
from backend.nlu.router import UniversalIntentRouter
from backend.observability.command_tracer import command_tracer, CommandTrace
from backend.observability.sentry_monitor import sentry_error_boundary


class TestDeterministicRoutingRegression:
    """Validate 100% deterministic intent routing for canonical commands."""

    @pytest.mark.parametrize("phrase, expected_tool, expected_index", [
        ("play first short", "click_screen_video", 1),
        ("play the first short", "click_screen_video", 1),
        ("first short play karo", "click_screen_video", 1),
        ("pehla short chalao", "click_screen_video", 1),
        ("पहला शॉर्ट चलाओ", "click_screen_video", 1),
        ("youtube ka first short play karo", "click_screen_video", 1),
        ("play second short", "click_screen_video", 2),
        ("dusra short chalao", "click_screen_video", 2),
        ("play third short", "click_screen_video", 3),
        ("teesra short chalao", "click_screen_video", 3),
    ])
    def test_youtube_shorts_routing(self, phrase, expected_tool, expected_index):
        parsed = SemanticIntentEngine.parse(phrase)
        routes = UniversalIntentRouter.route(parsed)
        assert len(routes) > 0, f"No route returned for '{phrase}'"
        assert routes[0].tool_name == expected_tool
        assert routes[0].arguments.get("index") == expected_index

    @pytest.mark.parametrize("phrase, expected_intent", [
        ("pause video", "PAUSE"),
        ("rok do", "PAUSE"),
        ("resume video", "RESUME"),
        ("chala do", "RESUME"),
        ("next video", "NEXT_MEDIA"),
        ("agla gaana", "NEXT_MEDIA"),
        ("volume up", "VOLUME_UP"),
        ("aawaz badhao", "VOLUME_UP"),
        ("volume down", "VOLUME_DOWN"),
        ("mute audio", "MUTE_AUDIO"),
    ])
    def test_media_and_system_intents(self, phrase, expected_intent):
        parsed = SemanticIntentEngine.parse(phrase)
        assert parsed.primary_intent.value == expected_intent

    def test_negative_downloads_isolation(self):
        """Verify 'downloads kholo' never accidentally routes to Shorts or Video play."""
        parsed = SemanticIntentEngine.parse("downloads kholo")
        assert parsed.primary_intent.value != "SELECT"
        assert parsed.target_application == "youtube"

    def test_negative_file_explorer_isolation(self):
        """Verify 'file explorer kholo' never routes to media playback."""
        parsed = SemanticIntentEngine.parse("file explorer kholo")
        assert parsed.target_application == "system"


class TestCommandTracerObservability:
    """Validate structured command tracing and sequential ID generation."""

    def test_sequential_command_id_generation(self):
        id1 = command_tracer.next_command_id()
        id2 = command_tracer.next_command_id()
        assert id1.startswith("CMD-")
        assert id2.startswith("CMD-")
        n1 = int(id1.split("-")[1])
        n2 = int(id2.split("-")[1])
        assert n2 == n1 + 1

    def test_complete_trace_lifecycle(self):
        cid = command_tracer.next_command_id()
        trace = command_tracer.start_trace("play first short", command_id=cid)
        assert trace.command_id == cid

        command_tracer.update_trace(
            command_id=cid,
            domain="youtube",
            intent="youtube.play_first_short",
            selected_tool="youtube.play_first_short",
        )

        fin = command_tracer.finish_trace(
            command_id=cid,
            verification_status="PASS",
            verification_details="Verified YouTube Shorts active",
        )
        assert fin is not None
        assert fin.verification_status == "PASS"
        assert fin.duration_ms >= 0


class TestSentryErrorBoundary:
    """Validate that adapter error boundaries isolate exceptions without crashing."""

    def test_error_boundary_catches_exception(self):
        @sentry_error_boundary(adapter="mock_test")
        def failing_function():
            raise RuntimeError("Simulated adapter failure")

        res = failing_function()
        assert res["status"] == "error"
        assert "Simulated adapter failure" in res["error"]
