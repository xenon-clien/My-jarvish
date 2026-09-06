"""Universal Intent Router.

Routes canonical SemanticParseResults to registered Application Tools and Skills.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from backend.core.logger import get_logger
from backend.nlu.models import SemanticParseResult, UniversalIntent

logger = get_logger("UniversalIntentRouter")


class RoutedToolCall(BaseModel):
    """Structured tool execution payload produced by the router."""
    tool_name: str
    arguments: Dict[str, Any]
    immediate_response: str
    target_application: Optional[str] = None


class UniversalIntentRouter:
    """Dispatches application-agnostic universal intents to concrete tool implementations."""

    @classmethod
    def route(cls, parse_result: SemanticParseResult) -> Optional[List[RoutedToolCall]]:
        """Map canonical intent and entities into executable ToolCalls."""
        intent = parse_result.primary_intent
        entities = parse_result.entities
        app = parse_result.target_application or "system"

        # Multi-Action Command Chaining (e.g. "scroll karo aur pehla short chalao")
        raw = (parse_result.raw_transcript or "").strip()
        for conj in [" aur ", " and ", " fir ", " then ", " ke baad "]:
            if conj in raw.lower():
                import re
                parts = [p.strip() for p in re.split(re.escape(conj), raw, flags=re.IGNORECASE) if p.strip()]
                if len(parts) >= 2 and all(len(p) > 2 for p in parts):
                    from backend.nlu.semantic_engine import SemanticIntentEngine
                    compound_calls = []
                    for part in parts:
                        sub_parsed = SemanticIntentEngine.parse(part)
                        if sub_parsed.primary_intent not in [UniversalIntent.UNKNOWN, UniversalIntent.CONVERSATIONAL_CHAT]:
                            sub_routes = cls._route_single(sub_parsed.primary_intent, sub_parsed.entities, sub_parsed.target_application or app)
                            if sub_routes:
                                compound_calls.extend(sub_routes)
                    if compound_calls:
                        return compound_calls

        return cls._route_single(intent, entities, app)

    @classmethod
    def _route_single(cls, intent: UniversalIntent, entities: Any, app: str) -> Optional[List[RoutedToolCall]]:
        """Internal single-intent tool dispatcher."""

        # ── 1. Communication & Messaging ─────────────────────────────────────
        if intent == UniversalIntent.CALL_CONTACT:
            target = entities.contact or entities.phone_number or "active"
            return [RoutedToolCall(
                tool_name="call_whatsapp_contact",
                arguments={"contact_or_phone": target, "call_type": "voice"},
                immediate_response=f"Ji Boss, WhatsApp par {target} ko voice call laga di hai.",
                target_application="whatsapp",
            )]

        if intent == UniversalIntent.VIDEO_CALL:
            target = entities.contact or entities.phone_number or "active"
            return [RoutedToolCall(
                tool_name="call_whatsapp_contact",
                arguments={"contact_or_phone": target, "call_type": "video"},
                immediate_response=f"Ji Boss, WhatsApp par {target} ko video call laga di hai.",
                target_application="whatsapp",
            )]

        if intent == UniversalIntent.END_CALL:
            return [RoutedToolCall(
                tool_name="control_whatsapp_call",
                arguments={"action": "end"},
                immediate_response="Ji Boss, WhatsApp call end kar di.",
                target_application="whatsapp",
            )]

        if intent == UniversalIntent.MUTE_CALL:
            return [RoutedToolCall(
                tool_name="control_whatsapp_call",
                arguments={"action": "mute"},
                immediate_response="Ji Boss, call mic mute/unmute toggle kar diya.",
                target_application="whatsapp",
            )]

        if intent == UniversalIntent.SEND_MESSAGE:
            target = entities.contact or entities.phone_number or "active"
            body = entities.message_body or ""
            return [RoutedToolCall(
                tool_name="send_whatsapp_message",
                arguments={"contact_or_phone": target, "message": body, "auto_send": bool(body)},
                immediate_response=f"Ji Boss, WhatsApp par {target} ko message {'bhej diya.' if body else 'chat open kar diya.'}",
                target_application="whatsapp",
            )]

        if intent == UniversalIntent.DELETE_MESSAGE:
            return [RoutedToolCall(
                tool_name="delete_whatsapp_message",
                arguments={"mode": "last_sent"},
                immediate_response="Ji Boss, last sent message unsend kar diya.",
                target_application="whatsapp",
            )]

        if intent == UniversalIntent.STATUS_VIEW:
            return [RoutedToolCall(
                tool_name="control_whatsapp_status",
                arguments={"action": "open"},
                immediate_response="Ji Boss, WhatsApp Status open kar diya.",
                target_application="whatsapp",
            )]

        # ── 2. Application Lifecycle ─────────────────────────────────────────
        if intent == UniversalIntent.OPEN_APP:
            if app == "shorts" or "short" in (entities.query or "").lower():
                return [RoutedToolCall(
                    tool_name="click_screen_video",
                    arguments={"index": 1, "section": "shorts"},
                    immediate_response="Ji Boss, YouTube Shorts chala diya.",
                    target_application="youtube",
                )]
            if app == "youtube":
                query_str = (entities.query or "").strip()
                return [RoutedToolCall(
                    tool_name="play_youtube_video",
                    arguments={"query": query_str},
                    immediate_response=f"Haan Shivam, YouTube par {query_str} chala diya hai." if query_str else "Haan Shivam, YouTube open kar diya hai.",
                    target_application="youtube",
                )]
            if app == "chrome":
                return [RoutedToolCall(
                    tool_name="open_website",
                    arguments={"url": "https://www.google.com"},
                    immediate_response="Ji Boss, Chrome browser open kar diya.",
                    target_application="chrome",
                )]
            if app == "whatsapp":
                return [RoutedToolCall(
                    tool_name="send_whatsapp_message",
                    arguments={"contact_or_phone": "active", "message": "", "auto_send": False},
                    immediate_response="Ji Boss, WhatsApp open kar diya.",
                    target_application="whatsapp",
                )]
            # Generic App Launcher
            return [RoutedToolCall(
                tool_name="launch_app",
                arguments={"app_name": app},
                immediate_response=f"Ji Boss, {app.title()} open kar diya.",
                target_application=app,
            )]

        if intent == UniversalIntent.CLEAN_JUNK:
            return [RoutedToolCall(
                tool_name="clean_unused_apps",
                arguments={"close_browsers": False},
                immediate_response="Ji Boss, faltu apps band kar diye.",
                target_application="system",
            )]

        # ── 3. Media & Playback Controls ─────────────────────────────────────
        if intent in [UniversalIntent.PLAY, UniversalIntent.RESUME]:
            if "short" in (entities.query or "").lower():
                return [RoutedToolCall(
                    tool_name="click_screen_video",
                    arguments={"index": 1, "section": "shorts"},
                    immediate_response="Ji Boss, YouTube Shorts chala diya.",
                    target_application="youtube",
                )]
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "play"},
                immediate_response="Ji Boss, video play kar diya.",
                target_application="youtube",
            )]

        if intent in [UniversalIntent.PAUSE, UniversalIntent.STOP]:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "pause"},
                immediate_response="Ji Boss, video pause kar diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.NEXT_MEDIA:
            return [RoutedToolCall(
                tool_name="click_screen_video",
                arguments={"index": 1, "section": "next"},
                immediate_response="Ji Boss, agla video chala diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.PREVIOUS_MEDIA:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "prev"},
                immediate_response="Ji Boss, pichla video chala diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.SEEK_FORWARD:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "seek_forward"},
                immediate_response=f"Ji Boss, {entities.time_duration_sec or 10} seconds aage kar diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.SEEK_BACKWARD:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "seek_backward"},
                immediate_response=f"Ji Boss, {entities.time_duration_sec or 10} seconds peeche kar diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.SEEK_TIMESTAMP:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "seek_timestamp", "time_str": entities.time_str, "level": entities.time_duration_sec},
                immediate_response=f"Ji Boss, video ko {entities.time_str or 'target time'} par set kar diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.SPEED_UP:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "speed_up"},
                immediate_response="Ji Boss, playback speed badha di.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.SPEED_DOWN:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "speed_down"},
                immediate_response="Ji Boss, playback speed kam kar di.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.FULLSCREEN:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "fullscreen"},
                immediate_response="Ji Boss, fullscreen toggle kar diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.THEATER_MODE:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "theater"},
                immediate_response="Ji Boss, theater mode toggle kar diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.MINIPLAYER:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "miniplayer"},
                immediate_response="Ji Boss, miniplayer toggle kar diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.CAPTIONS:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "captions"},
                immediate_response="Ji Boss, captions/subtitles toggle kar diye.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.REPLAY:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "replay"},
                immediate_response="Ji Boss, video shuru se restart kar diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.NEXT_SHORT:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "next_short"},
                immediate_response="Ji Boss, agla short chala diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.PREV_SHORT:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "prev_short"},
                immediate_response="Ji Boss, pichla short chala diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.VOLUME_UP:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "volume_up"},
                immediate_response="Ji Boss, volume badha diya.",
                target_application="system",
            )]

        if intent == UniversalIntent.VOLUME_DOWN:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "volume_down"},
                immediate_response="Ji Boss, volume kam kar diya.",
                target_application="system",
            )]

        if intent == UniversalIntent.MUTE_AUDIO:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "mute"},
                immediate_response="Ji Boss, mute kar diya.",
                target_application="system",
            )]

        if intent == UniversalIntent.UNMUTE_AUDIO:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "unmute"},
                immediate_response="Ji Boss, unmute kar diya.",
                target_application="system",
            )]

        # ── 4. Social & Video Interaction ────────────────────────────────────
        if intent == UniversalIntent.LIKE:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "like"},
                immediate_response="Ji Boss, video like kar diya!",
                target_application="youtube",
            )]

        if intent == UniversalIntent.DISLIKE:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "dislike"},
                immediate_response="Ji Boss, video dislike kar diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.SUBSCRIBE:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "subscribe"},
                immediate_response="Ji Boss, channel subscribe kar diya!",
                target_application="youtube",
            )]

        if intent == UniversalIntent.SHARE:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "share"},
                immediate_response="Ji Boss, share menu open kar diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.COMMENTS_VIEW:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "comments_down"},
                immediate_response="Ji Boss, comments section par scroll kar diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.COMMENTS_HIDE:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "comments_up"},
                immediate_response="Ji Boss, wapas video par scroll kar diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.DISLIKE:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "dislike"},
                immediate_response="Ji Boss, video dislike kar diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.SUBSCRIBE:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "subscribe"},
                immediate_response="Ji Boss, channel subscribe kar diya!",
                target_application="youtube",
            )]

        if intent == UniversalIntent.SHARE:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "share"},
                immediate_response="Ji Boss, share option open kar diya!",
                target_application="youtube",
            )]

        if intent == UniversalIntent.COMMENTS_VIEW:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "comments_down"},
                immediate_response="Ji Boss, comments section open kar diya.",
                target_application="youtube",
            )]

        if intent == UniversalIntent.COMMENTS_HIDE:
            return [RoutedToolCall(
                tool_name="control_media",
                arguments={"action": "comments_up"},
                immediate_response="Ji Boss, wapas video par scroll kar diya.",
                target_application="youtube",
            )]

        # ── 5. Navigation & Selection ────────────────────────────────────────
        if intent == UniversalIntent.SELECT:
            idx = entities.ordinal_index or 1
            is_short_req = "short" in (entities.query or "").lower() or entities.position_relative == "shorts"
            sec = "shorts" if is_short_req else ("sidebar" if entities.position_relative == "sidebar" or idx > 1 else "main")
            resp = "Ji Boss, YouTube Shorts chala diya." if is_short_req else f"Ji Boss, video number {idx} chala diya."
            return [RoutedToolCall(
                tool_name="click_screen_video",
                arguments={"index": idx, "section": sec},
                immediate_response=resp,
                target_application="youtube",
            )]

        if intent == UniversalIntent.SCROLL_DOWN:
            return [RoutedToolCall(
                tool_name="scroll_page",
                arguments={"direction": "down", "amount": 400},
                immediate_response="Ji Boss, neeche scroll kar diya.",
                target_application=app,
            )]

        if intent == UniversalIntent.SCROLL_UP:
            return [RoutedToolCall(
                tool_name="scroll_page",
                arguments={"direction": "up", "amount": 400},
                immediate_response="Ji Boss, upar scroll kar diya.",
                target_application=app,
            )]

        if intent == UniversalIntent.SEARCH and entities.query:
            if app == "youtube":
                return [RoutedToolCall(
                    tool_name="play_youtube_video",
                    arguments={"query": entities.query},
                    immediate_response=f"Ji Boss, YouTube par '{entities.query}' search kiya.",
                    target_application="youtube",
                )]
            return [RoutedToolCall(
                tool_name="google_search",
                arguments={"query": entities.query},
                immediate_response=f"Ji Boss, '{entities.query}' search kar diya.",
                target_application="chrome",
            )]

        return None
