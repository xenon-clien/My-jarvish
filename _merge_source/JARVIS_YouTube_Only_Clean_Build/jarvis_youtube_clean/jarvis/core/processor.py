from __future__ import annotations

from jarvis.ai.planner import SemanticPlanner
from jarvis.ai.providers import AIProviderRouter
from jarvis.config import settings
from jarvis.core.logging import EventLogger
from jarvis.core.models import ActionResult
from jarvis.core.parser import FastParser
from jarvis.youtube.adapter import YouTubeAdapter
from jarvis.youtube.catalog import canonical_names


class CommandProcessor:
    def __init__(self):
        self.providers = AIProviderRouter()
        self.planner = SemanticPlanner(self.providers)
        self.parser = FastParser()
        self.youtube = YouTubeAdapter()
        self.log = EventLogger(settings.logs_dir / "events.jsonl")

    async def close(self):
        await self.youtube.close()

    async def handle(self, raw_text: str) -> ActionResult:
        text = (raw_text or "").strip()
        if not text:
            return ActionResult(False, "FAILED", "core.empty", "Maine command nahi suni.")

        # Developer commands are local and never sent to AI.
        low = text.lower()
        if low == "/health":
            ctx = await self.youtube.context()
            return ActionResult(True, "LIVE_VERIFIED", "core.health", f"YouTube page: {ctx.get('page_type')}. Provider: {self.providers.status().get('last_provider') or 'not used yet'}.", actual=ctx)
        if low == "/tools":
            names = canonical_names()
            return ActionResult(True, "LIVE_VERIFIED", "core.tools", f"YouTube-only profile: {len(names)} canonical tools.", details={"tools": names})
        if low == "/provider":
            return ActionResult(True, "LIVE_VERIFIED", "core.provider", "Provider status", actual=self.providers.status())
        if low == "/provider reset astra":
            self.providers.reset_astra()
            return ActionResult(True, "LIVE_VERIFIED", "core.provider_reset", "Astra provider state reset. Next semantic AI request may test Astra again.")
        if low in {"/stop", "stop jarvis", "jarvis stop"}:
            return ActionResult(True, "LIVE_VERIFIED", "core.stop", "STOP_REQUESTED")

        ctx = await self.youtube.context()
        intent = self.parser.parse(text, ctx)
        if intent is None:
            # Explicitly reject known other-app requests instead of confusing the AI.
            if any(app in low for app in ["whatsapp", "spotify", "telegram", "vscode", "vs code", "file explorer"]):
                return ActionResult(False, "UNSUPPORTED", "core.disabled_app", "Abhi production profile mein sirf YouTube enabled hai.")
            intent = self.planner.plan(text)

        if intent is None:
            return ActionResult(False, "UNSUPPORTED", "core.unresolved", "Main is command ko YouTube ke approved actions mein safely map nahi kar paaya.")
        if intent.application not in settings.enabled_apps:
            return ActionResult(False, "UNSUPPORTED", intent.canonical, f"{intent.application} current production profile mein enabled nahi hai.")

        self.log.write("COMMAND_RESOLVED", raw_text=text, canonical=intent.canonical, arguments=intent.arguments, source=intent.source, confidence=intent.confidence)
        result = await self.youtube.execute(intent)
        self.log.write("COMMAND_RESULT", canonical=intent.canonical, success=result.success, status=result.status, message=result.message, expected=result.expected, actual=result.actual)
        return result
