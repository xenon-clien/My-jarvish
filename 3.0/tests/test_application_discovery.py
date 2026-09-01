"""Unit tests for Application Discovery Engine and Application Registry."""
import pytest
from apps.application_discovery import AppCategory, ApplicationDiscoveryEngine, application_discovery_engine
from apps.application_registry import ApplicationRegistry, application_registry
from apps.capability_discovery import CapabilityDiscoveryEngine, capability_discovery_engine


def test_application_discovery_scan():
    apps = application_discovery_engine.discover_all_applications()
    assert isinstance(apps, list)
    assert len(apps) > 0, "Expected at least core system apps to be discovered."

    # Verify essential system apps are present
    app_ids = [a.id for a in apps]
    assert "file_explorer" in app_ids or "notepad" in app_ids or "calculator" in app_ids


def test_application_registry_query_and_breakdown():
    reg = ApplicationRegistry()
    apps = reg.list_apps()
    assert len(apps) > 0

    breakdown = reg.get_category_breakdown()
    assert isinstance(breakdown, dict)
    assert AppCategory.SYSTEM_UTILITIES.value in breakdown

    # Search for notepad or explorer
    app = reg.find_app_by_name("notepad")
    if app:
        assert "notepad" in app.name.lower() or app.id == "notepad"


def test_capability_manifest_generation():
    manifest = capability_discovery_engine.get_manifest_by_id_or_name("youtube")
    assert manifest is not None
    assert manifest.app_name == "YouTube"
    assert manifest.adapter == "YouTubeAdapter"
    assert len(manifest.capabilities) > 0

    cap_names = [c.name for c in manifest.capabilities]
    assert "open" in cap_names
