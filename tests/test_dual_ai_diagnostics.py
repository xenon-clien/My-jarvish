"""Automated Unit Tests for JARVIS Dual-AI Diagnostics & Cost-Safety Architecture."""
import pytest
import time
import os
import json
from pathlib import Path

from backend.diagnostics.nemotron_guard import NemotronUsageGuard, NemotronState, NVIDIA_ALLOWED_MODELS
from backend.diagnostics.fingerprint_manager import ErrorFingerprintManager
from backend.diagnostics.issue_tracker import IssueTracker
from backend.diagnostics.nemotron_debugger import NemotronDiagnosticReport


class TestNemotronUsageGuardCostSafety:
    """Validate safety quota, warning threshold, hard cap, and zero paid fallback."""

    def test_model_allowlist_enforcement(self, tmp_path):
        guard = NemotronUsageGuard(persistence_dir=str(tmp_path))
        guard.model_name = "nvidia/nemotron-3.5-lightning:free"
        can_run, reason = guard.canUseNemotron()
        assert can_run is True
        assert reason == "AVAILABLE"

        # Unauthorized paid models must be strictly blocked
        for paid_model in ["openai/gpt-4o", "nvidia/nemotron-3.5-lightning", "anthropic/claude-3.5-sonnet"]:
            guard.model_name = paid_model
            can_run, reason = guard.canUseNemotron()
            assert can_run is False
            assert "UNAUTHORIZED_MODEL" in reason

    def test_warning_threshold_stops_automatic_usage(self, tmp_path):
        guard = NemotronUsageGuard(persistence_dir=str(tmp_path))
        guard.model_name = "nvidia/nemotron-3.5-lightning:free"
        guard.state.requests_today = 40
        guard.state.warning_threshold = 40
        guard.state.max_daily_requests = 45

        # Automatic usage is stopped at warning threshold
        can_run, reason = guard.canUseNemotron(is_automatic=True)
        assert can_run is False
        assert reason == "NEAR_FREE_LIMIT"
        assert guard.get_current_state() == NemotronState.NEAR_FREE_LIMIT

    def test_hard_limit_at_45_requests(self, tmp_path):
        guard = NemotronUsageGuard(persistence_dir=str(tmp_path))
        guard.model_name = "nvidia/nemotron-3.5-lightning:free"
        guard.state.requests_today = 45
        guard.state.max_daily_requests = 45

        # Hard limit reached: absolutely 0 further requests allowed
        can_run, reason = guard.canUseNemotron(is_automatic=False)
        assert can_run is False
        assert reason == "LOCAL_FREE_LIMIT_REACHED"
        assert guard.get_current_state() == NemotronState.LOCAL_FREE_LIMIT_REACHED

    def test_provider_quota_exhausted_override(self, tmp_path):
        guard = NemotronUsageGuard(persistence_dir=str(tmp_path))
        guard.model_name = "nvidia/nemotron-3.5-lightning:free"
        guard.record_rate_limit(is_quota_exhausted=True)

        can_run, reason = guard.canUseNemotron()
        assert can_run is False
        assert reason == "PROVIDER_FREE_LIMIT_REACHED"
        assert guard.get_current_state() == NemotronState.PROVIDER_FREE_LIMIT_REACHED

    def test_restart_persistence_preserves_counter(self, tmp_path):
        # 1. Create guard, record requests
        guard1 = NemotronUsageGuard(persistence_dir=str(tmp_path))
        guard1.model_name = "nvidia/nemotron-3.5-lightning:free"
        guard1.record_request(success=True)
        guard1.record_request(success=True)
        guard1.record_request(success=False)
        assert guard1.state.requests_today == 3

        # 2. Simulate complete application restart (new instance loading from disk)
        guard2 = NemotronUsageGuard(persistence_dir=str(tmp_path))
        guard2.model_name = "nvidia/nemotron-3.5-lightning:free"
        assert guard2.state.requests_today == 3
        assert guard2.state.successful_requests_today == 2
        assert guard2.state.failed_requests_today == 1

    def test_manual_kill_switch(self, tmp_path):
        guard = NemotronUsageGuard(persistence_dir=str(tmp_path))
        guard.model_name = "nvidia/nemotron-3.5-lightning:free"
        guard.set_enabled(False)

        can_run, reason = guard.canUseNemotron()
        assert can_run is False
        assert reason == "DISABLED"
        assert guard.get_current_state() == NemotronState.DISABLED


class TestErrorFingerprintManager:
    """Validate error fingerprint computation and diagnosis caching."""

    def test_deterministic_fingerprint(self, tmp_path):
        mgr = ErrorFingerprintManager(cache_dir=str(tmp_path))
        fp1 = mgr.compute_fingerprint(domain="youtube", intent="play_first_short", error_type="WRONG_TARGET")
        fp2 = mgr.compute_fingerprint(domain="youtube", intent="play_first_short", error_type="WRONG_TARGET")
        assert fp1 == fp2
        assert fp1.startswith("YOUTUBE-WRONG_TARGET-")

    def test_diagnosis_caching(self, tmp_path):
        mgr = ErrorFingerprintManager(cache_dir=str(tmp_path))
        fp = mgr.compute_fingerprint(domain="youtube", intent="play_first_short", error_type="WRONG_TARGET")
        
        entry = mgr.store_diagnosis(
            fingerprint=fp,
            issue_type="WRONG_TARGET",
            affected_layer="YouTubeTargetResolver",
            root_cause="Duplicate short elements",
            confidence=0.92,
            reproduction_test="python scripts/reproduce_debug.py youtube-first-short",
            recommended_fix="Deduplicate short links",
        )
        assert entry.fingerprint == fp

        cached = mgr.get_cached_diagnosis(fp)
        assert cached is not None
        assert cached.root_cause == "Duplicate short elements"
        assert cached.occurrence_count == 2


class TestIssueTracker:
    """Validate issue creation, severity tracking, and resolution."""

    def test_issue_lifecycle(self, tmp_path):
        tracker = IssueTracker(persistence_dir=str(tmp_path))
        issue = tracker.create_issue(
            domain="youtube",
            title="Wrong first Short opened",
            command="play first short",
            expected="Short #1",
            actual="Short #2",
            severity="ERROR",
            root_cause="Ordinal mismatch",
            affected_layer="YouTubeTargetResolver",
            confidence=0.88,
        )
        assert issue.issue_id.startswith("YT-")
        assert issue.status == "DIAGNOSED"

        open_list = tracker.get_open_issues()
        assert len(open_list) == 1

        resolved = tracker.resolve_issue(issue.issue_id)
        assert resolved is True
        assert len(tracker.get_open_issues()) == 0
