"""JARVIS 3.0 - Universal Deterministic Intent Router.

Routes developer slash commands, multi-step compound flows, and unambiguous
natural language intents (Hindi, Hinglish, English) to canonical tools with zero latency.
"""
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from apps.application_registry import application_registry
from core.logger import get_logger
from nlu.canonical_intents import CanonicalIntent
from nlu.language_normalizer import LanguageNormalizer, NormalizedEntities

logger = get_logger("DeterministicRouter")


class RouteDecision(BaseModel):
    intent: CanonicalIntent
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    immediate_response: str = ""
    is_multi_step: bool = False
    plan_steps: List[Dict[str, Any]] = Field(default_factory=list)


class DeterministicRouter:
    """Fast, deterministic semantic pattern matcher."""

    @classmethod
    def route_command(cls, raw_text: str) -> Optional[RouteDecision]:
        """Route user text to canonical tool and arguments, or return None for Gemini planning."""
        if not raw_text or not raw_text.strip():
            return None

        text_raw = raw_text.strip()
        normalized = LanguageNormalizer.normalize_text(raw_text)
        entities = LanguageNormalizer.extract_entities(normalized)
        text = normalized.lower()

        # ── 0. Developer Slash Commands ───────────────────────────────────────
        if text_raw.startswith("/"):
            slash_cmd = text_raw.lower()
            if slash_cmd in ["/health", "/healthcheck"]:
                return RouteDecision(intent=CanonicalIntent.DIAGNOSTICS_HEALTH_CHECK, tool_name="diagnostics.health_check", confidence=1.0)
            if slash_cmd in ["/apps", "/applications"]:
                return RouteDecision(intent=CanonicalIntent.DESKTOP_LIST_APPS, tool_name="desktop.list_apps", confidence=1.0)
            if slash_cmd in ["/tools", "/capabilities"]:
                return RouteDecision(intent=CanonicalIntent.DIAGNOSTICS_RUN, tool_name="system.status", confidence=1.0)
            if slash_cmd.startswith("/capabilities "):
                target_app = slash_cmd.replace("/capabilities ", "").strip()
                return RouteDecision(intent=CanonicalIntent.DESKTOP_APP_CAPABILITIES, tool_name="desktop.app_capabilities", arguments={"app_name": target_app}, confidence=1.0)
            if slash_cmd in ["/diagnose", "/debug", "/bugs"]:
                return RouteDecision(intent=CanonicalIntent.DIAGNOSTICS_BUGS, tool_name="diagnostics.bugs", confidence=1.0)
            if slash_cmd in ["/stop", "/cancel"]:
                return RouteDecision(intent=CanonicalIntent.SYSTEM_STOP, tool_name="system.stop", confidence=1.0)

        # ── 1. Emergency Stop & Cancel Commands ──────────────────────────────
        if any(re.search(rf"\b{w}\b", text) for w in ["stop", "cancel", "ruk", "ruk jao", "bas", "hatao", "pause all", "cancel current task"]):
            if "video" not in text and "gaana" not in text:
                return RouteDecision(
                    intent=CanonicalIntent.SYSTEM_STOP,
                    tool_name="system.stop",
                    confidence=1.0,
                    immediate_response="Ji Boss, ruk gaya.",
                )

        # ── 2. Multi-Step Compound Commands ("aur", "and", "fir", "then", "ke baad") ──
        for conj in [" aur ", " and ", " fir ", " then ", " ke baad "]:
            if conj in text:
                parts = [p.strip() for p in re.split(re.escape(conj), text) if p.strip()]
                if len(parts) >= 2:
                    sub_plans = []
                    for part in parts:
                        sub_route = cls.route_command(part)
                        if sub_route:
                            sub_plans.append({
                                "tool": sub_route.tool_name,
                                "arguments": sub_route.arguments,
                                "intent": sub_route.intent.value,
                            })
                    if len(sub_plans) >= 2:
                        logger.info(f"Compound command detected ({len(sub_plans)} steps): {[s['tool'] for s in sub_plans]}")
                        return RouteDecision(
                            intent=CanonicalIntent.COMPLEX_PLAN,
                            tool_name="multi_step_planner",
                            confidence=0.95,
                            is_multi_step=True,
                            plan_steps=sub_plans,
                            immediate_response="Ji Boss, multi-step plan execute kar raha hoon.",
                        )

        # ── 3. Health Check & Diagnostics ────────────────────────────────────
        if any(w in text for w in ["health check", "healthcheck", "system health", "diagnose", "system status"]):
            return RouteDecision(
                intent=CanonicalIntent.DIAGNOSTICS_HEALTH_CHECK,
                tool_name="diagnostics.health_check",
                confidence=1.0,
                immediate_response="Running system health check...",
            )

        if any(w in text for w in ["find bugs", "detect bugs", "bugs find karo", "bug finder"]):
            return RouteDecision(
                intent=CanonicalIntent.DIAGNOSTICS_BUGS,
                tool_name="diagnostics.bugs",
                confidence=1.0,
                immediate_response="Scanning system integrity for bugs...",
            )

        # ── 4. Application Discovery / Listing ────────────────────────────────
        if any(w in text for w in ["kaun kaun se apps", "installed apps", "show apps", "list apps", "kaunse apps"]):
            return RouteDecision(
                intent=CanonicalIntent.DESKTOP_LIST_APPS,
                tool_name="desktop.list_apps",
                confidence=0.98,
                immediate_response="Listing discovered installed applications...",
            )

        # ── 5. Hidden Files Management ───────────────────────────────────────
        if "hidden file" in text or "hidden files" in text:
            if any(w in text for w in ["dikhao", "show", "unhide", "open"]):
                return RouteDecision(
                    intent=CanonicalIntent.FILES_SHOW_HIDDEN,
                    tool_name="files.show_hidden",
                    arguments={},
                    confidence=0.99,
                    immediate_response="Ji Boss, Windows Explorer mein hidden files show kar di gayi hain.",
                )
            if any(w in text for w in ["hide", "chhupao", "band karo"]):
                return RouteDecision(
                    intent=CanonicalIntent.FILES_HIDE_HIDDEN,
                    tool_name="files.hide_hidden",
                    arguments={},
                    confidence=0.99,
                    immediate_response="Ji Boss, hidden files hide kar di gayi hain.",
                )

        # ── 6. Downloads Management ──────────────────────────────────────────
        if "download" in text or "downloads" in text:
            if any(w in text for w in ["last", "pichli", "recently", "recent"]) and any(w in text for w in ["file", "kya"]):
                return RouteDecision(
                    intent=CanonicalIntent.DOWNLOADS_LAST,
                    tool_name="downloads.last_downloaded",
                    arguments={},
                    confidence=0.98,
                )
            if any(w in text for w in ["folder kholo", "open folder", "directory kholo"]):
                return RouteDecision(
                    intent=CanonicalIntent.DOWNLOADS_OPEN_FOLDER,
                    tool_name="downloads.open_folder",
                    arguments={},
                    confidence=0.98,
                )
            if any(w in text for w in ["status", "complete hai", "ho rahi hai", "check"]):
                return RouteDecision(
                    intent=CanonicalIntent.DOWNLOADS_STATUS,
                    tool_name="downloads.status",
                    arguments={},
                    confidence=0.98,
                )

        # ── 7. File Extensions Search (PDF, PNG, MP4, DOCX, Large files) ─────
        m_ext = re.search(r"\b(pdf|png|jpg|jpeg|mp4|mp3|docx|xlsx|zip|rar)\s+(?:files?|documents?)\b", text)
        if m_ext and any(w in text for w in ["find", "search", "dhoondo", "dikhao"]):
            ext = m_ext.group(1)
            return RouteDecision(
                intent=CanonicalIntent.FILES_FIND_EXT,
                tool_name="files.find_by_extension",
                arguments={"extension": ext},
                confidence=0.98,
            )

        if any(w in text for w in ["large files", "badi files", "gb se badi", "mb se badi"]):
            return RouteDecision(
                intent=CanonicalIntent.FILES_FIND_LARGE,
                tool_name="files.find_large",
                arguments={"min_size_mb": 100.0},
                confidence=0.98,
            )

        # ── 8. YouTube Shorts Controls (Priority for Shorts) ──────────────────
        if entities.is_short:
            if entities.ordinal_index == 1 or any(w in text for w in ["first", "pehla", "pehli", "1st"]):
                return RouteDecision(
                    intent=CanonicalIntent.YOUTUBE_PLAY_FIRST_SHORT,
                    tool_name="youtube.play_first_short",
                    arguments={},
                    confidence=0.99,
                    immediate_response="Ji Boss, pehla Short chala diya.",
                )
            if any(w in text for w in ["next", "agla", "agli"]):
                return RouteDecision(
                    intent=CanonicalIntent.YOUTUBE_NEXT_SHORT,
                    tool_name="youtube.next_short",
                    arguments={},
                    confidence=0.98,
                    immediate_response="Ji Boss, agla short play kiya.",
                )
            if any(w in text for w in ["prev", "previous", "pichla", "pichli"]):
                return RouteDecision(
                    intent=CanonicalIntent.YOUTUBE_PREV_SHORT,
                    tool_name="youtube.prev_short",
                    arguments={},
                    confidence=0.98,
                    immediate_response="Ji Boss, pichla short play kiya.",
                )
            return RouteDecision(
                intent=CanonicalIntent.YOUTUBE_PLAY_FIRST_SHORT,
                tool_name="youtube.play_first_short",
                arguments={},
                confidence=0.95,
                immediate_response="Ji Boss, YouTube Shorts shuru kar diya.",
            )

        # ── 9. YouTube Media & Video Controls ────────────────────────────────
        if any(w in text for w in ["pause", "rok", "rok do", "video pause"]):
            return RouteDecision(intent=CanonicalIntent.YOUTUBE_PAUSE, tool_name="youtube.pause", confidence=0.98, immediate_response="Ji Boss, video pause kar diya.")
        if any(w in text for w in ["resume", "unpause", "play video", "video chalao", "continue"]):
            return RouteDecision(intent=CanonicalIntent.YOUTUBE_RESUME, tool_name="youtube.resume", confidence=0.95, immediate_response="Ji Boss, video resume kar diya.")
        if any(w in text for w in ["next video", "agla video", "next gaana", "next song", "agla chalao"]):
            return RouteDecision(intent=CanonicalIntent.YOUTUBE_NEXT, tool_name="youtube.next_video", confidence=0.98, immediate_response="Ji Boss, agla video chala diya.")
        if any(w in text for w in ["previous video", "pichla video", "prev video", "pichla gaana"]):
            return RouteDecision(intent=CanonicalIntent.YOUTUBE_PREV, tool_name="youtube.prev_video", confidence=0.98, immediate_response="Ji Boss, pichla video chala diya.")
        if any(w in text for w in ["comments kholo", "open comments", "comments section"]):
            return RouteDecision(intent=CanonicalIntent.YOUTUBE_OPEN_COMMENTS, tool_name="youtube.open_comments", confidence=0.98, immediate_response="Ji Boss, comments section open kar diya.")
        if any(w in text for w in ["fullscreen", "full screen", "bada karo"]):
            return RouteDecision(intent=CanonicalIntent.YOUTUBE_FULLSCREEN, tool_name="youtube.fullscreen", confidence=0.98, immediate_response="Ji Boss, fullscreen toggle kar diya.")
        if any(w in text for w in ["like video", "video like", "like karo"]):
            return RouteDecision(intent=CanonicalIntent.YOUTUBE_LIKE, tool_name="youtube.like", confidence=0.98, immediate_response="Ji Boss, video like kar di!")
        if any(w in text for w in ["subscribe karo", "channel subscribe"]):
            return RouteDecision(intent=CanonicalIntent.YOUTUBE_SUBSCRIBE, tool_name="youtube.subscribe", confidence=0.98, immediate_response="Ji Boss, channel subscribe kar diya!")

        if "youtube" in text:
            if entities.search_query:
                return RouteDecision(
                    intent=CanonicalIntent.YOUTUBE_SEARCH,
                    tool_name="youtube.search",
                    arguments={"query": entities.search_query},
                    confidence=0.95,
                    immediate_response=f"Ji Boss, YouTube par '{entities.search_query}' search kiya.",
                )
            if any(w in text for w in ["open", "kholo", "chalao", "launch"]):
                return RouteDecision(intent=CanonicalIntent.YOUTUBE_OPEN, tool_name="youtube.open", confidence=0.98, immediate_response="Ji Boss, YouTube open kar diya.")

        # ── 10. Chrome Browser Tab Controls ──────────────────────────────────
        if "chrome" in text or "browser" in text or "tab" in text:
            if any(w in text for w in ["new tab", "naya tab"]):
                return RouteDecision(intent=CanonicalIntent.CHROME_NEW_TAB, tool_name="chrome.new_tab", confidence=0.98, immediate_response="Ji Boss, new tab open kar diya.")
            if any(w in text for w in ["close tab", "tab band karo", "tab close"]):
                return RouteDecision(intent=CanonicalIntent.CHROME_CLOSE_TAB, tool_name="chrome.close_tab", confidence=0.98, immediate_response="Ji Boss, active tab close kar diya.")
            if any(w in text for w in ["next tab", "agla tab"]):
                return RouteDecision(intent=CanonicalIntent.CHROME_NEXT_TAB, tool_name="chrome.next_tab", confidence=0.98)
            if any(w in text for w in ["prev tab", "pichla tab", "previous tab"]):
                return RouteDecision(intent=CanonicalIntent.CHROME_PREV_TAB, tool_name="chrome.previous_tab", confidence=0.98)
            if any(w in text for w in ["incognito", "private"]):
                return RouteDecision(intent=CanonicalIntent.CHROME_OPEN_INCOGNITO, tool_name="chrome.open_incognito", confidence=0.98)
            if any(w in text for w in ["history", "browsing history"]):
                return RouteDecision(intent=CanonicalIntent.CHROME_OPEN_HISTORY, tool_name="chrome.open_history", confidence=0.98)
            if any(w in text for w in ["bookmarks", "bookmark"]):
                return RouteDecision(intent=CanonicalIntent.CHROME_OPEN_BOOKMARKS, tool_name="chrome.open_bookmarks", confidence=0.98)
            if "chrome" in text and any(w in text for w in ["open", "kholo", "launch"]):
                return RouteDecision(intent=CanonicalIntent.CHROME_OPEN, tool_name="chrome.open", confidence=0.98, immediate_response="Ji Boss, Chrome open kar diya.")

        # ── 11. System Volume & Audio Controls ───────────────────────────────
        if entities.volume_level is not None:
            return RouteDecision(intent=CanonicalIntent.SYSTEM_SET_VOLUME, tool_name="system.set_volume", arguments={"level": entities.volume_level}, confidence=0.99)
        if any(w in text for w in ["volume up", "volume badhao", "aawaz badhao", "sound up"]):
            return RouteDecision(intent=CanonicalIntent.SYSTEM_VOLUME_UP, tool_name="system.volume_up", arguments={"steps": 3}, confidence=0.98)
        if any(w in text for w in ["volume down", "volume kam", "aawaz kam", "sound down"]):
            return RouteDecision(intent=CanonicalIntent.SYSTEM_VOLUME_DOWN, tool_name="system.volume_down", arguments={"steps": 3}, confidence=0.98)
        if any(w in text for w in ["unmute", "aawaz kholo"]):
            return RouteDecision(intent=CanonicalIntent.SYSTEM_UNMUTE, tool_name="system.unmute", confidence=0.98)
        if any(w in text for w in ["mute", "aawaz band"]):
            return RouteDecision(intent=CanonicalIntent.SYSTEM_MUTE, tool_name="system.mute", confidence=0.98)

        # ── 12. WhatsApp Controls ────────────────────────────────────────────
        if "whatsapp" in text or entities.target_contact:
            if any(w in text for w in ["voice call", "call lagao", "call karo", "phone mila"]) or (entities.target_contact and "call" in text):
                target = entities.target_contact or "active"
                return RouteDecision(intent=CanonicalIntent.WHATSAPP_VOICE_CALL, tool_name="whatsapp.voice_call", arguments={"contact": target}, confidence=0.95)
            if any(w in text for w in ["video call"]):
                target = entities.target_contact or "active"
                return RouteDecision(intent=CanonicalIntent.WHATSAPP_VIDEO_CALL, tool_name="whatsapp.video_call", arguments={"contact": target}, confidence=0.95)
            if any(w in text for w in ["end call", "cut call", "call cut", "hang up"]):
                return RouteDecision(intent=CanonicalIntent.WHATSAPP_END_CALL, tool_name="whatsapp.end_call", confidence=0.98)
            if entities.message_body or any(w in text for w in ["message", "msg", "text"]):
                target = entities.target_contact or "active"
                body = entities.message_body or ""
                return RouteDecision(intent=CanonicalIntent.WHATSAPP_SEND_MESSAGE, tool_name="whatsapp.send_message", arguments={"contact": target, "message": body, "auto_send": bool(body)}, confidence=0.95)
            if "whatsapp" in text and any(w in text for w in ["open", "kholo", "launch"]):
                return RouteDecision(intent=CanonicalIntent.WHATSAPP_OPEN, tool_name="whatsapp.open", confidence=0.98)

        # ── 13. System Status, Time, Battery, Lock ───────────────────────────
        if any(w in text for w in ["time kya hai", "time batao", "current time", "what is the time"]):
            return RouteDecision(intent=CanonicalIntent.SYSTEM_TIME, tool_name="system.time", confidence=0.99)
        if any(w in text for w in ["battery", "battery percentage", "charging status"]):
            return RouteDecision(intent=CanonicalIntent.SYSTEM_BATTERY, tool_name="system.battery", confidence=0.99)
        if any(w in text for w in ["system status", "cpu status", "ram status", "pc performance"]):
            return RouteDecision(intent=CanonicalIntent.SYSTEM_STATUS, tool_name="system.status", confidence=0.99)
        if any(w in text for w in ["lock computer", "computer lock", "screen lock", "lock pc"]):
            return RouteDecision(intent=CanonicalIntent.SYSTEM_LOCK, tool_name="system.open_app", arguments={"app_name": "rundll32.exe user32.dll,LockWorkStation"}, confidence=0.99, immediate_response="Ji Boss, computer lock kar diya.")

        # ── 14. Universal App Launching across 93+ Discovered Apps ───────────
        m_open = re.search(r"\b([a-zA-Z0-9_\s]+?)\s+(?:kholo|open\s+karo|chalao|launch\s+karo|start\s+karo)\b", text)
        if not m_open:
            m_open = re.search(r"\b(?:open|launch|start)\s+([a-zA-Z0-9_\s]+)\b", text)
        if m_open:
            cand = m_open.group(1).strip()
            # Ignore command words
            if cand not in ["tab", "short", "video", "comments", "link", "url", "file", "folder", "hidden files"]:
                app_match = application_registry.find_app_by_name(cand)
                if app_match:
                    return RouteDecision(
                        intent=CanonicalIntent.DESKTOP_OPEN_APP,
                        tool_name="desktop.open_app",
                        arguments={"app_name": app_match.name},
                        confidence=0.95,
                        immediate_response=f"Ji Boss, {app_match.name} open kar diya.",
                    )

        # Ambiguous / Complex request -> delegate to Gemini planner
        return None
