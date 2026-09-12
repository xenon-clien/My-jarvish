"""Authoritative Single YouTube Browser Session Bridge.

Re-exports YouTubeBrowserSession from backend.youtube.session to ensure a single
authoritative CDP connection, dedicated worker event loop, and state tracking.
"""

from backend.youtube.session import (
    YouTubeBrowserSession,
    youtube_session as browser_session,
    DEFAULT_CDP_URL,
)

__all__ = ["YouTubeBrowserSession", "browser_session", "DEFAULT_CDP_URL"]
