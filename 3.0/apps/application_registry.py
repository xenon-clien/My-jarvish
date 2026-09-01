"""JARVIS 3.0 - Central Application Registry.

Manages all discovered desktop and web applications, their metadata,
adapters, and status across 15 categories.
"""
from typing import Dict, List, Optional
from apps.application_discovery import (
    AppCategory,
    ApplicationDiscoveryEngine,
    DiscoveredApp,
    application_discovery_engine,
)
from core.events import EventType, JarvisEvent, event_bus
from core.logger import get_logger

logger = get_logger("AppRegistry")


class ApplicationRegistry:
    """Central registry of all applications installed on the system."""

    def __init__(self):
        self._apps: Dict[str, DiscoveredApp] = {}
        self._is_scanned = False
        self.rescan()

    def rescan(self) -> None:
        """Run full OS discovery scan and update registry."""
        logger.info("Scanning system for installed applications...")
        apps_list = application_discovery_engine.discover_all_applications()
        self._apps = {app.id: app for app in apps_list}
        self._is_scanned = True
        logger.info(f"ApplicationRegistry loaded {len(self._apps)} applications across {len(AppCategory)} categories.")
        event_bus.publish(JarvisEvent(
            event_type=EventType.APP_OPENED,
            data={"total_apps": len(self._apps)},
        ))

    def get_app(self, app_id: str) -> Optional[DiscoveredApp]:
        """Get application by exact slug ID."""
        return self._apps.get(app_id.lower().strip())

    def find_app_by_name(self, query: str) -> Optional[DiscoveredApp]:
        """Fuzzy search for application by name."""
        clean_q = query.lower().strip()
        # Direct key match
        if clean_q in self._apps:
            return self._apps[clean_q]

        # Exact name match
        for app in self._apps.values():
            if app.name.lower() == clean_q:
                return app

        # Substring search
        for app in self._apps.values():
            if clean_q in app.name.lower() or app.name.lower() in clean_q:
                return app

        return None

    def list_apps(self, category: Optional[AppCategory] = None) -> List[DiscoveredApp]:
        """Return all applications with optional category filter."""
        apps = list(self._apps.values())
        if category:
            apps = [a for a in apps if a.category == category]
        return sorted(apps, key=lambda a: a.name.lower())

    def get_category_breakdown(self) -> Dict[str, int]:
        """Return count of applications per category."""
        counts: Dict[str, int] = {cat.value: 0 for cat in AppCategory}
        for app in self._apps.values():
            cat_val = app.category.value
            counts[cat_val] = counts.get(cat_val, 0) + 1
        return counts

    def get_summary_report(self) -> str:
        """Generate human-readable CLI report of all discovered applications."""
        lines = [f"JARVIS APPLICATION REGISTRY ({len(self._apps)} Applications Discovered)"]
        lines.append("=" * 60)
        breakdown = self.get_category_breakdown()
        for cat, count in breakdown.items():
            if count > 0:
                lines.append(f"• {cat}: {count} apps")
        lines.append("=" * 60)
        return "\n".join(lines)


application_registry = ApplicationRegistry()
