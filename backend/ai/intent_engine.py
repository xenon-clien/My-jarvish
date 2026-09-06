"""Fast Local Intent Matcher for JARVIS AI.

Provides instant (<1ms) deterministic rule-based intent parsing for common voice
and text commands in Hindi, Hinglish, and English without requiring cloud LLM latency.
All responses are ultra-concise, human-like, and main-point focused.
"""
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.ai.providers import ToolCall


class FastIntentMatch(BaseModel):
    """Represents a successfully resolved intent from fast local matching."""
    intent_name: str
    tool_calls: List[ToolCall] = Field(default_factory=list)
    immediate_response: Optional[str] = None
    is_direct_chat: bool = False
    direct_chat_response: Optional[str] = None


class FastIntentEngine:
    """Ultra-fast regex and keyword matcher for immediate JARVIS command execution."""

    def __init__(self, user_name: str = "Shivam"):
        self.user_name = user_name

    def match(self, user_text: str) -> Optional[FastIntentMatch]:
        """Analyze user text and return a FastIntentMatch if an exact or high-confidence intent matches."""
        if not user_text:
            return None

        raw = user_text.strip()
        text = raw.lower()
        # Normalize Hindi negation variants: nahin, nhi, nai, ni, नहीं, नही -> nahi
        text = re.sub(r"\b(nahin|nhi|nai|ni|नहीं|नही)\b", "nahi", text, flags=re.IGNORECASE)
        # Remove trailing punctuation
        text = re.sub(r"[?!.,]+$", "", text).strip()

        # -------------------------------------------------------------
        # 0. Instant Stop / Silence / Quiet Command (Highest Priority)
        # -------------------------------------------------------------
        if any(text == w or text.startswith(w) for w in [
            "shant ho jao", "chup ho jao", "chup raho", "chup", "stop", "shant", "quiet",
            "stop speaking", "bas", "ruk jao", "bolna band karo", "awaz band karo",
            "awaaz band karo", "shut up", "khamosh", "shant raho"
        ]):
            try:
                from backend.voice.text_to_speech import tts_manager
                tts_manager.stop()
            except Exception:
                pass
            return FastIntentMatch(
                intent_name="silence",
                is_direct_chat=True,
                direct_chat_response="Haan bhai, shant ho gaya.",
            )

        # -------------------------------------------------------------
        # 0.5 Universal App Analysis & Feature Health Testing Commands (With Hindi/Hinglish Slangs)
        # -------------------------------------------------------------
        if any(w in text for w in [
            "analyze this app", "analyze app", "app analyze karo", "analyze this", "is app ke features batao",
            "app capabilities", "check capabilities", "scan app", "analyze youtube", "analyze chrome",
            "is app ko scan maar", "bata is app mein kya kya hai", "is app ka scene kya hai", "is app ke features dikha",
            "app scan kar", "features bata iske", "ye app kya kya kar sakta hai", "is app ka intro de"
        ]):
            target_app = "youtube" if "youtube" in text else ("chrome" if "chrome" in text else None)
            return FastIntentMatch(
                intent_name="analyze_active_app",
                tool_calls=[ToolCall(name="analyze_app", arguments={"app_name": target_app})],
                immediate_response="Ji Boss, active application ko analyze karke saare features discover kar rahi hoon.",
            )

        if any(w in text for w in [
            "test all features of this app", "test this app", "test all features", "app health test",
            "app test karo", "test app health", "check app health", "saare features test karo",
            "app ko check maar", "test kar sab theek hai na", "features check kar daal", "app test maar"
        ]):
            target_app = "youtube" if "youtube" in text else ("chrome" if "chrome" in text else None)
            return FastIntentMatch(
                intent_name="test_app_health",
                tool_calls=[ToolCall(name="test_app_health", arguments={"app_name": target_app})],
                immediate_response="Ji Boss, is application ke saare features ka safe non-destructive health test run kar rahi hoon.",
            )

        # -------------------------------------------------------------
        # 0.6 Context-Aware Relative Commands & Hindi/Hinglish Slangs
        # -------------------------------------------------------------
        from backend.skills.context import relative_resolver
        rel_info = relative_resolver.resolve(text)
        if rel_info.get("action") == "like":
            return FastIntentMatch(
                intent_name="relative_like",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "like"})],
                immediate_response="Ji Boss, video like kar di!",
            )
        elif rel_info.get("action") == "share":
            return FastIntentMatch(
                intent_name="relative_share",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "share"})],
                immediate_response="Ji Boss, share option open kar diya!",
            )
        elif rel_info.get("action") == "subscribe":
            return FastIntentMatch(
                intent_name="relative_subscribe",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "subscribe"})],
                immediate_response="Ji Boss, channel subscribe kar diya!",
            )
        elif rel_info.get("action") == "comments_down":
            return FastIntentMatch(
                intent_name="relative_comments",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "comments_down"})],
                immediate_response="Ji Boss, comments section par scroll kar diya.",
            )
        elif rel_info.get("ordinal_index") is not None and any(w in text for w in ["play the", "open the", "click the", "the one", "wala", "wali", "chala na", "laga de"]):
            idx = rel_info["ordinal_index"]
            pos = rel_info.get("position") or "auto"
            return FastIntentMatch(
                intent_name=f"relative_click_{idx}",
                tool_calls=[ToolCall(name="click_screen_video", arguments={"index": idx, "section": pos})],
                immediate_response=f"Ji Boss, {idx} number item chala diya.",
            )


        # -------------------------------------------------------------
        # 1.5 High Priority WhatsApp Calling, Messaging & Communication Suite
        # -------------------------------------------------------------
        # Save Contact Voice Intent (e.g. "80548 40494 harsh save karo", "harsh ka number 8054840494 save karo")
        save_contact_match = re.search(r"(?:save\s+)?([a-zA-Z\s]+?)\s+(?:ka\s+number\s+|number\s+)?([0-9\s\+]{10,15})\s*(?:save\s+karo|save)?", text) or \
                             re.search(r"([0-9\s\+]{10,15})\s+([a-zA-Z\s]+?)\s*(?:save\s+karo|save)", text)
        if save_contact_match and any(w in text for w in ["save", "save karo"]):
            g1 = save_contact_match.group(1).strip()
            g2 = save_contact_match.group(2).strip()
            if re.match(r"^[0-9\s\+]{10,15}$", g1):
                phone_raw = g1.replace(" ", "").replace("+", "")
                name_raw = g2
            else:
                name_raw = g1
                phone_raw = g2.replace(" ", "").replace("+", "")

            name_clean = re.sub(r"\b(save|karo|ka|ki|ke|number|contact)\b", "", name_raw, flags=re.IGNORECASE).strip()
            if name_clean and phone_raw:
                return FastIntentMatch(
                    intent_name="save_contact_intent",
                    tool_calls=[ToolCall(name="save_contact", arguments={"name": name_clean.title(), "phone": phone_raw})],
                    immediate_response=f"Ji Boss, {name_clean.title()} ka number {phone_raw} address book mein save kar diya hai!",
                )

        # WhatsApp Voice Call & Video Call (e.g. "harsh ko voice call lagao", "voice call lagao", "call harsh")
        if any(w in text for w in [
            "voice call", "voice call lagao", "voice call karo", "whatsapp voice call", "call lagao",
            "whatsapp call", "call karo", "call this contact", "voice call kar do", "call lagao whatsapp pe",
            "whatsapp pe call lagao", "whatsapp call lagao", "voice call laga na", "call laga de", "call"
        ]) and not any(k in text for k in ["cut", "end", "disconnect", "hangup", "mute"]):
            contact_match = re.search(r"^(?:whatsapp\s+(?:pe|par)\s+)?([a-zA-Z0-9_\s]+?)\s+(?:ko\s+)?(?:voice\s+call|call)\s*(?:lagao|karo|kar\s+do|laga\s+de)?$", text)
            target_name = "active"
            if contact_match and contact_match.group(1).strip() not in ["whatsapp", "voice", ""]:
                clean_target = re.sub(r"\b(whatsapp|voice|call|lagao|karo|ko|pe|par|isko|usko)\b", "", contact_match.group(1)).strip()
                if clean_target:
                    target_name = clean_target

            if "harsh" in text.lower():
                target_name = "Harsh"

            return FastIntentMatch(
                intent_name="whatsapp_voice_call",
                tool_calls=[ToolCall(name="call_whatsapp_contact", arguments={"contact_or_phone": target_name, "call_type": "voice"})],
                immediate_response=f"Ji Boss, WhatsApp par {target_name if target_name != 'active' else 'active contact'} ko voice call laga di hai.",
            )

        if any(w in text for w in ["video call", "video call lagao", "video call karo", "whatsapp video call", "video call kar do"]):
            contact_match = re.search(r"^(?:whatsapp\s+(?:pe|par)\s+)?([a-zA-Z0-9_\s]+?)\s+(?:ko\s+)?video\s+call\s*(?:lagao|karo|kar\s+do)?$", text)
            target_name = "active"
            if contact_match and contact_match.group(1).strip() not in ["whatsapp", "video", ""]:
                clean_target = re.sub(r"\b(whatsapp|video|call|lagao|karo|ko|pe|par)\b", "", contact_match.group(1)).strip()
                if clean_target:
                    target_name = clean_target

            return FastIntentMatch(
                intent_name="whatsapp_video_call",
                tool_calls=[ToolCall(name="call_whatsapp_contact", arguments={"contact_or_phone": target_name, "call_type": "video"})],
                immediate_response=f"Ji Boss, WhatsApp par {target_name if target_name != 'active' else 'active contact'} ko video call laga di hai.",
            )

        # WhatsApp Send Message (e.g. "harsh ko message karo hello", "harsh ko message bhejo")
        msg_patterns = [
            r"^(?:whatsapp\s+(?:pe|par)\s+)?([a-zA-Z\s]+?)\s+(?:ko\s+)?(?:message|msg)\s*(?:karo|bhejo|kar\s+do|laga\s+de|bhej)?(?:\s*[:,\-]?\s*(.+))?$",
            r"^(?:send\s+message\s+to\s+|message\s+)([a-zA-Z\s]+?)(?:\s*[:,\-]?\s*(.+))?$",
            r"^([a-zA-Z\s]+?)\s+ko\s+(?:bolo|likho)\s+(.+)$",
        ]
        for m_pat in msg_patterns:
            m_res = re.match(m_pat, text)
            if m_res and any(w in text for w in ["message", "msg", "bhejo", "bhej", "bolo", "likho"]):
                target_raw = m_res.group(1).strip()
                body_msg = m_res.group(2).strip() if len(m_res.groups()) > 1 and m_res.group(2) else ""
                clean_target = re.sub(r"\b(whatsapp|message|msg|ko|pe|par|karo|bhejo)\b", "", target_raw, flags=re.IGNORECASE).strip()
                if "harsh" in text.lower():
                    clean_target = "Harsh"

                if clean_target:
                    return FastIntentMatch(
                        intent_name="whatsapp_send_message",
                        tool_calls=[ToolCall(name="send_whatsapp_message", arguments={"contact_or_phone": clean_target, "message": body_msg, "auto_send": bool(body_msg)})],
                        immediate_response=f"Ji Boss, WhatsApp par {clean_target} ko message {'bhej diya.' if body_msg else 'chat open kar diya.'}",
                    )

        # -------------------------------------------------------------
        # 2. YouTube & Video Actions (Prioritized & Short)
        # -------------------------------------------------------------
        # Guard: Ignore YouTube section if user requested communication/calls/messages
        if any(k in text for k in ["call", "voice call", "video call", "whatsapp", "message", "msg"]):
            pass
        else:
            # Generic YouTube Open: "play youtube karo", "youtube open karo", "chrome mein youtube kholo", "open youtube"
            generic_yt_patterns = [
                r"^(play\s+)?youtube(\s+open\s+karo|\s+kholo|\s+chalao|\s+play\s+karo|\s+start\s+karo)?(\s+chrome(\s+ke\s+andar|\s+mein)?)?$",
                r"^(chrome\s+(ke\s+andar|mein)\s+)?youtube(\s+open\s+karo|\s+kholo|\s+chalao)?$",
                r"^open\s+youtube(\s+in\s+chrome)?$",
                r"^play\s+youtube$",
                r"^youtube$",
            ]
            for pattern in generic_yt_patterns:
                if re.match(pattern, text):
                    return FastIntentMatch(
                        intent_name="open_youtube",
                        tool_calls=[ToolCall(name="play_youtube_video", arguments={"query": ""})],
                        immediate_response="Ji Boss, YouTube open kar diya.",
                    )

        # Expanded Ordinal Map (1 to 10)
        ordinal_map = {
            "first": 1, "1st": 1, "pehla": 1, "pehli": 1, "1": 1,
            "second": 2, "2nd": 2, "dusra": 2, "doosra": 2, "dusri": 2, "2": 2,
            "third": 3, "3rd": 3, "teesra": 3, "tisra": 3, "teesri": 3, "3": 3,
            "fourth": 4, "4th": 4, "chautha": 4, "chauthi": 4, "4": 4,
            "fifth": 5, "5th": 5, "panchwa": 5, "panchvi": 5, "5": 5,
            "sixth": 6, "6th": 6, "chhatha": 6, "chhatthi": 6, "6": 6,
            "seventh": 7, "7th": 7, "saatwa": 7, "saatwi": 7, "7": 7,
            "eighth": 8, "8th": 8, "aathwa": 8, "aathwi": 8, "8": 8,
            "ninth": 9, "9th": 9, "nauwa": 9, "9": 9,
            "tenth": 10, "10th": 10, "daswa": 10, "10": 10,
        }

        # 1. Direct Next / Previous Video (With Hindi/Hinglish Slangs)
        if not any(k in text for k in ["call", "whatsapp", "message", "msg"]) and any(w in text for w in [
            "next video", "agla video", "agli video", "next song", "next gaana", "play next",
            "agla laga", "next fek", "agla chala", "change kar de", "aage badha", "next gaana laga"
        ]):
            return FastIntentMatch(
                intent_name="youtube_next_video",
                tool_calls=[ToolCall(name="click_screen_video", arguments={"index": 1, "section": "next"})],
                immediate_response="Ji Boss, agla video chala diya.",
            )

        if any(w in text for w in [
            "previous video", "pichla video", "pichli video", "previous song", "back video",
            "pichla la", "wapas chala", "pichle pe chal", "peeche kar", "wapas laga"
        ]):
            return FastIntentMatch(
                intent_name="youtube_previous_video",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "previous"})],
                immediate_response="Ji Boss, pichla video chala diya.",
            )

        # 1.5 YouTube Shorts Automation (With Hindi/Hinglish Slangs)
        if any(w in text for w in [
            "next short", "agla short", "agli short", "short change karo", "scroll short",
            "next short phek", "short badal de", "agla short daal", "short change kar"
        ]):
            return FastIntentMatch(
                intent_name="youtube_next_short",
                tool_calls=[ToolCall(name="click_screen_video", arguments={"index": 1, "section": "shorts"})],
                immediate_response="Ji Boss, agla short chala diya.",
            )

        if any(w in text for w in [
            "shorts play", "shorts chalao", "short chalao", "shorts lagao", "youtube shorts", "open shorts", "play shorts", "short video",
            "shorts chala de", "shorts khol", "shorts laga na"
        ]):
            return FastIntentMatch(
                intent_name="open_youtube_shorts",
                tool_calls=[ToolCall(name="play_youtube_video", arguments={"query": "", "wants_short": True})],
                immediate_response="Ji Boss, YouTube Shorts chala diye.",
            )

        # 2. Right-Side Recommended Video Matching (e.g. "play second video in my right side", "right side 4th video", "right side 3rd video")
        if "right side" in text or "right-side" in text or "sidebar" in text or "side" in text:
            idx = 1
            for word, val in ordinal_map.items():
                if re.search(rf"\b{word}\b", text):
                    idx = val
                    break
            return FastIntentMatch(
                intent_name=f"click_right_side_video_{idx}",
                tool_calls=[ToolCall(name="click_screen_video", arguments={"index": idx, "section": "right"})],
                immediate_response=f"Ji Boss, right side wali {idx} number video chala di.",
            )

        # 3. Screen / Grid Video Click Matching (e.g., "play second video", "dusra video chalao", "click 4th video", "3rd video play karo")
        ord_pattern = r"^(?:play|paly|click|chalao|lagao|open|chala|laga)?\s*(first|1st|pehla|pehli|second|2nd|dusra|doosra|dusri|third|3rd|teesra|tisra|teesri|fourth|4th|chautha|fifth|5th|sixth|6th|seventh|7th|eighth|8th|ninth|9th|tenth|10th|[1-9]|10)\s+(?:video|short|shorts|gaana|song|video\s+pe|pe)?\s*(?:click\s+karo|play\s+karo|play|chalao|lagao|kholo|chala\s+de|laga\s+de)?$"
        m_ord = re.match(ord_pattern, text)
        if m_ord:
            ord_word = m_ord.group(1).lower()
            idx = ordinal_map.get(ord_word, 1)
            return FastIntentMatch(
                intent_name=f"click_video_{idx}",
                tool_calls=[ToolCall(name="click_screen_video", arguments={"index": idx})],
                immediate_response=f"Ji Boss, {idx} number video chala diya.",
            )

        # 4. Advanced YouTube Controls (Speed, Theater, Fullscreen, Subtitles, Seek, Like, Subscribe, Share, Comments)
        if any(w in text for w in [
            "like video", "video like", "like karo", "like this video", "like this short", "short like",
            "iss video ko like", "is video ko like", "video ko like", "short ko like", "like kar do", "like",
            "like thok de", "like maar", "like daba de", "like thoko", "like kar na", "like maar de"
        ]):
            return FastIntentMatch(
                intent_name="youtube_like",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "like"})],
                immediate_response="Ji Boss, video like kar di!",
            )

        if any(w in text for w in [
            "subscribe karo", "channel subscribe karo", "subscribe to channel", "subscribe",
            "subscribe maar", "subscribe thok", "ghanti daba de", "subscribe kar daal", "subscribe kar na"
        ]):
            return FastIntentMatch(
                intent_name="youtube_subscribe",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "subscribe"})],
                immediate_response="Ji Boss, channel subscribe kar diya!",
            )

        # 4.5 WhatsApp Voice Call & Video Call Automation
        # Save Contact Voice Intent (e.g. "80548 40494 harsh save karo", "harsh ka number 8054840494 save karo")
        save_contact_match = re.search(r"(?:save\s+)?([a-zA-Z\s]+?)\s+(?:ka\s+number\s+|number\s+)?([0-9\s\+]{10,15})\s*(?:save\s+karo|save)?", text) or \
                             re.search(r"([0-9\s\+]{10,15})\s+([a-zA-Z\s]+?)\s*(?:save\s+karo|save)", text)
        if save_contact_match and any(w in text for w in ["save", "save karo"]):
            g1 = save_contact_match.group(1).strip()
            g2 = save_contact_match.group(2).strip()
            # Determine which group is phone and which is name
            if re.match(r"^[0-9\s\+]{10,15}$", g1):
                phone_raw = g1.replace(" ", "").replace("+", "")
                name_raw = g2
            else:
                name_raw = g1
                phone_raw = g2.replace(" ", "").replace("+", "")

            name_clean = re.sub(r"\b(save|karo|ka|ki|ke|number|contact)\b", "", name_raw, flags=re.IGNORECASE).strip()
            if name_clean and phone_raw:
                return FastIntentMatch(
                    intent_name="save_contact_intent",
                    tool_calls=[ToolCall(name="save_contact", arguments={"name": name_clean.title(), "phone": phone_raw})],
                    immediate_response=f"Ji Boss, {name_clean.title()} ka number {phone_raw} address book mein save kar diya hai!",
                )

        if any(w in text for w in [
            "voice call", "voice call lagao", "voice call karo", "whatsapp voice call", "call lagao",
            "whatsapp call", "call karo", "call this contact", "voice call kar do", "call lagao whatsapp pe",
            "whatsapp pe call lagao", "whatsapp call lagao", "voice call laga na", "call laga de"
        ]):
            # Check if a contact name is mentioned (e.g. "harsh ko call lagao", "shivam ko call lagao")
            contact_match = re.search(r"^(?:whatsapp\s+(?:pe|par)\s+)?([a-zA-Z0-9_\s]+?)\s+(?:ko\s+)?(?:voice\s+call|call)\s*(?:lagao|karo|kar\s+do|laga\s+de)?$", text)
            target_name = "active"
            if contact_match and contact_match.group(1).strip() not in ["whatsapp", "voice", ""]:
                clean_target = re.sub(r"\b(whatsapp|voice|call|lagao|karo|ko|pe|par|isko|usko)\b", "", contact_match.group(1)).strip()
                if clean_target:
                    target_name = clean_target

            if "harsh" in text.lower():
                target_name = "Harsh"

            return FastIntentMatch(
                intent_name="whatsapp_voice_call",
                tool_calls=[ToolCall(name="call_whatsapp_contact", arguments={"contact_or_phone": target_name, "call_type": "voice"})],
                immediate_response=f"Ji Boss, WhatsApp par {target_name if target_name != 'active' else 'active contact'} ko voice call laga di hai.",
            )

        if any(w in text for w in ["video call", "video call lagao", "video call karo", "whatsapp video call", "video call kar do"]):
            contact_match = re.search(r"^(?:whatsapp\s+(?:pe|par)\s+)?([a-zA-Z0-9_\s]+?)\s+(?:ko\s+)?video\s+call\s*(?:lagao|karo|kar\s+do)?$", text)
            target_name = "active"
            if contact_match and contact_match.group(1).strip() not in ["whatsapp", "video", ""]:
                clean_target = re.sub(r"\b(whatsapp|video|call|lagao|karo|ko|pe|par)\b", "", contact_match.group(1)).strip()
                if clean_target:
                    target_name = clean_target

            return FastIntentMatch(
                intent_name="whatsapp_video_call",
                tool_calls=[ToolCall(name="call_whatsapp_contact", arguments={"contact_or_phone": target_name, "call_type": "video"})],
                immediate_response=f"Ji Boss, WhatsApp par {target_name if target_name != 'active' else 'active contact'} ko video call laga di hai.",
            )

        # WhatsApp Send Message Automation (e.g. "harsh ko message karo hello bhai", "harsh ko message bhejo", "send message to harsh: hello")
        msg_patterns = [
            r"^(?:whatsapp\s+(?:pe|par)\s+)?([a-zA-Z\s]+?)\s+(?:ko\s+)?(?:message|msg)\s*(?:karo|bhejo|kar\s+do|laga\s+de|bhej)?(?:\s*[:,\-]?\s*(.+))?$",
            r"^(?:send\s+message\s+to\s+|message\s+)([a-zA-Z\s]+?)(?:\s*[:,\-]?\s*(.+))?$",
            r"^([a-zA-Z\s]+?)\s+ko\s+(?:bolo|likho)\s+(.+)$",
        ]
        for m_pat in msg_patterns:
            m_res = re.match(m_pat, text)
            if m_res and any(w in text for w in ["message", "msg", "bhejo", "bhej", "bolo", "likho"]):
                target_raw = m_res.group(1).strip()
                body_msg = m_res.group(2).strip() if len(m_res.groups()) > 1 and m_res.group(2) else ""
                clean_target = re.sub(r"\b(whatsapp|message|msg|ko|pe|par|karo|bhejo)\b", "", target_raw, flags=re.IGNORECASE).strip()
                if "harsh" in text.lower():
                    clean_target = "Harsh"

                if clean_target:
                    return FastIntentMatch(
                        intent_name="whatsapp_send_message",
                        tool_calls=[ToolCall(name="send_whatsapp_message", arguments={"contact_or_phone": clean_target, "message": body_msg, "auto_send": bool(body_msg)})],
                        immediate_response=f"Ji Boss, WhatsApp par {clean_target} ko message {'bhej diya.' if body_msg else 'chat open kar diya.'}",
                    )

        # -------------------------------------------------------------
        # 4.6 Complete WhatsApp Automation Suite (Calls, Chats, Status, Media)
        # -------------------------------------------------------------
        # A. WhatsApp Call Controls (Hang up, End Call, Mute Call)
        if any(w in text for w in ["call cut karo", "call end karo", "call cut", "end call", "hang up", "call disconnect", "call band karo", "call disconnect karo"]):
            return FastIntentMatch(
                intent_name="whatsapp_end_call",
                tool_calls=[ToolCall(name="control_whatsapp_call", arguments={"action": "end"})],
                immediate_response="Ji Boss, WhatsApp call end kar di.",
            )

        if any(w in text for w in ["call mute karo", "call unmute karo", "mute call", "unmute call", "call mic band karo"]):
            return FastIntentMatch(
                intent_name="whatsapp_mute_call",
                tool_calls=[ToolCall(name="control_whatsapp_call", arguments={"action": "mute"})],
                immediate_response="Ji Boss, WhatsApp call mute/unmute toggle kar diya.",
            )

        # B. WhatsApp Status / Stories Suite
        if any(w in text for w in ["status dekho", "whatsapp status", "status kholo", "status dikhao", "view status", "status open karo"]):
            return FastIntentMatch(
                intent_name="whatsapp_status_open",
                tool_calls=[ToolCall(name="control_whatsapp_status", arguments={"action": "open"})],
                immediate_response="Ji Boss, WhatsApp Status open kar diya.",
            )

        if any(w in text for w in ["next status", "agla status", "status change karo", "next story"]):
            return FastIntentMatch(
                intent_name="whatsapp_status_next",
                tool_calls=[ToolCall(name="control_whatsapp_status", arguments={"action": "next"})],
                immediate_response="Ji Boss, agla status laga diya.",
            )

        if any(w in text for w in ["previous status", "pichla status", "back status", "prev status"]):
            return FastIntentMatch(
                intent_name="whatsapp_status_prev",
                tool_calls=[ToolCall(name="control_whatsapp_status", arguments={"action": "prev"})],
                immediate_response="Ji Boss, pichla status laga diya.",
            )

        if any(w in text for w in ["pause status", "status roko", "status pause", "resume status"]):
            return FastIntentMatch(
                intent_name="whatsapp_status_pause",
                tool_calls=[ToolCall(name="control_whatsapp_status", arguments={"action": "pause"})],
                immediate_response="Ji Boss, status pause/resume toggle kar diya.",
            )

        # C. WhatsApp Chat Navigation & Management
        if any(w in text for w in ["next chat", "agla chat", "chat change karo", "next conversation", "agla message"]):
            return FastIntentMatch(
                intent_name="whatsapp_next_chat",
                tool_calls=[ToolCall(name="manage_whatsapp_chat", arguments={"action": "next_chat"})],
                immediate_response="Ji Boss, agla chat select kiya.",
            )

        if any(w in text for w in ["previous chat", "pichla chat", "back chat", "prev chat"]):
            return FastIntentMatch(
                intent_name="whatsapp_prev_chat",
                tool_calls=[ToolCall(name="manage_whatsapp_chat", arguments={"action": "prev_chat"})],
                immediate_response="Ji Boss, pichla chat select kiya.",
            )

        if any(w in text for w in ["mute this chat", "mute chat", "chat mute karo", "chat silent karo"]):
            return FastIntentMatch(
                intent_name="whatsapp_mute_chat",
                tool_calls=[ToolCall(name="manage_whatsapp_chat", arguments={"action": "mute"})],
                immediate_response="Ji Boss, chat mute toggle kar diya.",
            )

        if any(w in text for w in ["archive chat", "chat archive karo", "archive this chat"]):
            return FastIntentMatch(
                intent_name="whatsapp_archive_chat",
                tool_calls=[ToolCall(name="manage_whatsapp_chat", arguments={"action": "archive"})],
                immediate_response="Ji Boss, chat archive kar diya.",
            )

        if any(w in text for w in ["pin chat", "chat pin karo", "unpin chat", "pin this chat"]):
            return FastIntentMatch(
                intent_name="whatsapp_pin_chat",
                tool_calls=[ToolCall(name="manage_whatsapp_chat", arguments={"action": "pin"})],
                immediate_response="Ji Boss, chat pin/unpin toggle kar diya.",
            )

        if any(w in text for w in ["unread mark karo", "mark as unread", "chat unread karo"]):
            return FastIntentMatch(
                intent_name="whatsapp_mark_unread",
                tool_calls=[ToolCall(name="manage_whatsapp_chat", arguments={"action": "unread"})],
                immediate_response="Ji Boss, chat ko unread mark kar diya.",
            )

        if any(w in text for w in ["new chat kholo", "new chat open karo", "new chat", "start new chat"]):
            return FastIntentMatch(
                intent_name="whatsapp_new_chat",
                tool_calls=[ToolCall(name="manage_whatsapp_chat", arguments={"action": "new_chat"})],
                immediate_response="Ji Boss, new chat window open kar di.",
            )

        if any(w in text for w in ["new group banao", "create new group", "new group"]):
            return FastIntentMatch(
                intent_name="whatsapp_new_group",
                tool_calls=[ToolCall(name="manage_whatsapp_chat", arguments={"action": "new_group"})],
                immediate_response="Ji Boss, new group dialog open kar diya.",
            )

        # D. Message Recall / Clear Draft Box
        if any(w in text for w in ["message delete karo", "msg delete karo", "unsend message", "delete message", "unsend karo"]):
            return FastIntentMatch(
                intent_name="whatsapp_delete_message",
                tool_calls=[ToolCall(name="delete_whatsapp_message", arguments={"mode": "last_sent"})],
                immediate_response="Ji Boss, last sent message unsend kar diya.",
            )

        if any(w in text for w in ["draft clear karo", "draft hatao", "box clear karo", "input clear karo"]):
            return FastIntentMatch(
                intent_name="whatsapp_clear_draft",
                tool_calls=[ToolCall(name="delete_whatsapp_message", arguments={"mode": "draft"})],
                immediate_response="Ji Boss, drafted text clear kar diya.",
            )

        if any(w in text for w in [
            "share video", "share karo", "video share karo", "share this video",
            "share thok do", "share maar", "bhej de", "forward maar", "share kar na"
        ]):
            return FastIntentMatch(
                intent_name="youtube_share",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "share"})],
                immediate_response="Ji Boss, share option open kar diya!",
            )

        if any(w in text for w in [
            "comments dikhao", "comments padho", "comments mein jao", "scroll comments", "comments dekhne", "comments scroll",
            "comments khol", "niche scroll maar", "comments dikha na", "comments pe le chal"
        ]):
            return FastIntentMatch(
                intent_name="youtube_comments_down",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "comments_down"})],
                immediate_response="Ji Boss, comments section par scroll kar diya.",
            )

        if any(w in text for w in [
            "comments band karo", "video par jao", "video dikhao", "upar scroll karo", "scroll up",
            "wapas video pe chal", "comments hata", "upar le chal", "video dikha"
        ]):
            return FastIntentMatch(
                intent_name="youtube_comments_up",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "comments_up"})],
                immediate_response="Ji Boss, wapas video par scroll kar diya.",
            )

        if any(w in text for w in ["theater mode", "theatre mode", "cinema mode"]):
            return FastIntentMatch(
                intent_name="youtube_theater_mode",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "theater"})],
                immediate_response="Ji Boss, theater mode toggle kar diya.",
            )

        if any(w in text for w in ["subtitles on", "subtitles off", "caption on", "caption off", "subtitles", "captions"]):
            return FastIntentMatch(
                intent_name="youtube_subtitles",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "subtitles"})],
                immediate_response="Ji Boss, subtitles toggle kar diye.",
            )

        if any(w in text for w in ["2x speed", "double speed", "speed 2x", "2x karo"]):
            return FastIntentMatch(
                intent_name="youtube_2x_speed",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "speed_up"})],
                immediate_response="Ji Boss, 2x speed kar di.",
            )

        if any(w in text for w in ["10 seconds aage", "10 second aage", "skip 10 seconds", "thoda aage karo"]):
            return FastIntentMatch(
                intent_name="youtube_seek_forward",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "seek_forward"})],
                immediate_response="Ji Boss, 10 seconds aage kar diya.",
            )

        if any(w in text for w in ["10 seconds peeche", "10 second peeche", "rewind 10 seconds", "thoda peeche karo"]):
            return FastIntentMatch(
                intent_name="youtube_seek_backward",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "seek_backward"})],
                immediate_response="Ji Boss, 10 seconds peeche kar diya.",
            )

        # -------------------------------------------------------------
        # 2.5 Specific YouTube Video / Search / Play
        # -------------------------------------------------------------
        # Guard: If user said pause, like, subscribe, seek, comments, fullscreen, mute - DO NOT search!
        if not any(k in text for k in [
            "pause", "rok", "roko", "like", "subscribe", "share", "aage", "forward", "peeche",
            "rewind", "fullscreen", "theater", "comments", "mute", "unmute", "volume", "speed"
        ]):
            click_yt_patterns = [
                r"^(?:youtube\s+(?:mein|pe|par)\s+)?(.+?)\s+(?:video|song|gaana|standup|comedy|podcast)\s+(?:chalao|lagao|play\s+karo|bajao|kholo|search\s+karo|play)(?:\s+(?:youtube\s+(?:mein|pe|par)|in\s+youtube|on\s+youtube|in\s+chrome))?$",
                r"^(?:youtube\s+(?:mein|pe|par)\s+)(.+?)\s+(?:chalao|lagao|play\s+karo|bajao|kholo|search\s+karo|play)$",
                r"^(?:youtube\s+(?:mein|pe|par)\s+)?(.+?)\s+(?:pe|par)\s+click\s+karo$",
                r"^click\s+(?:on\s+)?(.+?)\s+(?:on|in)\s+youtube$",
                r"^(?:play|search)\s+(.+?)\s+(?:on|in)\s+youtube$",
                r"^play\s+(video|song|gaana|music|track|movie|podcast|vlog|short|shorts|reel|reels)\s+(.+)$",
            ]
            for pattern in click_yt_patterns:
                m = re.match(pattern, text)
                if m:
                    query_candidate = m.group(1).strip()
                    clean_q = re.sub(
                        r"\b(video|song|gaana|standup|comedy|podcast|youtube|chrome|on|in|mein|pe|par|search|play|karo|lagao|chalao|right\s+side|left\s+side|side|upar|niche|pehli|dusri|teesri|1st|2nd|3rd|first|second|third|hai|woh|yeh|ye|wo|wali|wala|vale|wale|ko|ki|ke|ka|batao|dikhao|sunao)\b",
                        "",
                        query_candidate,
                        flags=re.IGNORECASE
                    ).strip()
                    # Clean extra whitespace
                    clean_q = re.sub(r"\s+", " ", clean_q).strip()
                    if not clean_q:
                        clean_q = ""

                    if clean_q:
                        return FastIntentMatch(
                            intent_name="play_youtube_video",
                            tool_calls=[ToolCall(name="play_youtube_video", arguments={"query": clean_q})],
                            immediate_response=f"Ji Boss, {clean_q.title()} play kar diya.",
                        )
                    else:
                        return FastIntentMatch(
                            intent_name="open_youtube",
                            tool_calls=[ToolCall(name="play_youtube_video", arguments={"query": ""})],
                            immediate_response="Ji Boss, YouTube open kar diya.",
                        )

        # -------------------------------------------------------------
        # 3. Tab & Browser Window Controls
        # -------------------------------------------------------------
        if any(w in text for w in [
            "faltu tabs band karo", "faltu tab band karo", "faltu apps band karo",
            "clean tabs", "close unused apps", "close idle apps", "cleanup taskbar", "taskbar clean karo"
        ]):
            return FastIntentMatch(
                intent_name="clean_unused_apps",
                tool_calls=[ToolCall(name="clean_unused_apps", arguments={"close_browsers": False})],
                immediate_response="Ji Boss, faltu apps band kar diye.",
            )

        if any(w in text for w in [
            "youtube band karo", "close youtube", "youtube close karo", "youtube tab band karo"
        ]):
            return FastIntentMatch(
                intent_name="close_browser_tab_youtube",
                tool_calls=[ToolCall(name="close_browser_tab", arguments={"target": "youtube"})],
                immediate_response="Ji Boss, YouTube band kar diya.",
            )

        if any(w in text for w in [
            "tab band karo", "tab close karo", "close tab", "active tab band karo", "current tab close karo"
        ]):
            return FastIntentMatch(
                intent_name="close_browser_tab",
                tool_calls=[ToolCall(name="close_browser_tab", arguments={"target": "browser"})],
                immediate_response="Ji Boss, tab band kar diya.",
            )

        # Timestamp Seek Matching (e.g. "forward this video 10 min 30 sec", "10 minute aage karo", "5m30s par jao")
        time_seek_match = re.search(r"(\d+)\s*(?:min|minute|minutes|m)\s*(?:(\d+)\s*(?:sec|second|seconds|s))?", text)
        if time_seek_match and any(w in text for w in ["forward", "aage", "seek", "skip", "jao", "lagao", "chalao"]):
            mins = int(time_seek_match.group(1))
            secs = int(time_seek_match.group(2)) if time_seek_match.group(2) else 0
            t_param = f"{mins}m{secs}s" if secs else f"{mins}m"
            sec_disp = f" {secs} second" if secs else ""
            return FastIntentMatch(
                intent_name="youtube_seek_timestamp",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "seek_timestamp", "time_str": t_param})],
                immediate_response=f"Ji Boss, video ko {mins} minute{sec_disp} aage seek kar diya.",
            )

        # -------------------------------------------------------------
        # 4. Universal Application Launch & Close Controls
        # -------------------------------------------------------------
        open_app_match = re.match(r"^(?:open|launch|kholo|start)\s+(.+?)(?:\s+(?:karo|app|application|software))?$", text) or \
                         re.match(r"^(.+?)\s+(?:open\s+karo|kholo|start\s+karo|launch\s+karo|khol\s+do)$", text)
        if open_app_match:
            app_query = open_app_match.group(1).strip()
            # Guard against video/media phrases misfiring as apps
            if not any(k in app_query for k in ["video", "youtube", "short", "channel", "song", "third", "second", "1st", "2nd", "3rd", "first"]):
                clean_app_q = re.sub(r"\b(app|application|software|ko|ka|ki|ke|pe|par)\b", "", app_query).strip()
                from backend.tools.app_tools import app_registry
                resolved_app = app_registry.resolve_app(clean_app_q) or app_registry.resolve_app(app_query)
                if resolved_app:
                    target_name = resolved_app["name"]
                    return FastIntentMatch(
                        intent_name=f"open_{target_name.lower().replace(' ', '_')}",
                        tool_calls=[ToolCall(name="open_application", arguments={"app_name": target_name.lower()})],
                        immediate_response=f"Ji Boss, {target_name} khol diya.",
                    )

        close_app_match = re.match(r"^(?:close|band\s+karo|hata\s+do|stop|kill)\s+(.+?)(?:\s+(?:karo|app|application|software))?$", text) or \
                          re.match(r"^(.+?)\s+(?:close\s+karo|band\s+karo|hata\s+do|band\s+kar\s+do|close)$", text)
        if close_app_match:
            app_query = close_app_match.group(1).strip()
            clean_app_q = re.sub(r"\b(app|application|software|ko|ka|ki|ke|pe|par)\b", "", app_query).strip()
            from backend.tools.app_tools import app_registry
            resolved_app = app_registry.resolve_app(clean_app_q) or app_registry.resolve_app(app_query)
            if resolved_app:
                target_name = resolved_app["name"]
                return FastIntentMatch(
                    intent_name=f"close_{target_name.lower().replace(' ', '_')}",
                    tool_calls=[ToolCall(name="close_application", arguments={"app_name": target_name.lower()})],
                    immediate_response=f"Ji Boss, {target_name} band kar diya.",
                )

        # Check for minimize / maximize / restore window
        min_match = re.match(r"^(?:minimize|chhota\s+karo)\s+(.+?)(?:\s+(?:ko|app|window|karo))?$", text) or \
                    re.match(r"^(.+?)\s+(?:ko\s+)?(?:minimize\s+karo|chhota\s+karo|minimize)$", text)
        if min_match or any(w in text for w in ["minimize", "chhota karo"]):
            target_raw = min_match.group(1).strip() if min_match else text.replace("minimize", "").replace("karo", "").replace("ko", "").strip()
            clean_target = re.sub(r"\b(taskbar|mein|me|ko|window|app|application|screen)\b", "", target_raw).strip() or "window"
            return FastIntentMatch(
                intent_name="minimize_window",
                tool_calls=[ToolCall(name="manage_window", arguments={"action": "minimize", "target_app": clean_target})],
                immediate_response=f"Ji Boss, {clean_target.title()} window minimize kar rahi hu.",
            )

        max_match = re.match(r"^(?:maximize|bada\s+karo|fullscreen)\s+(.+?)(?:\s+(?:ko|app|window|karo))?$", text) or \
                    re.match(r"^(.+?)\s+(?:ko\s+)?(?:maximize\s+karo|bada\s+karo|maximize|fullscreen)$", text)
        if max_match:
            target_raw = max_match.group(1).strip()
            clean_target = re.sub(r"\b(taskbar|mein|me|ko|window|app|application|screen)\b", "", target_raw).strip() or "window"
            return FastIntentMatch(
                intent_name="maximize_window",
                tool_calls=[ToolCall(name="manage_window", arguments={"action": "maximize", "target_app": clean_target})],
                immediate_response=f"Ji Boss, {clean_target.title()} window maximize kar rahi hu.",
            )


        # -------------------------------------------------------------
        # 4.5 Real-Time Weather & Temperature Intent
        # -------------------------------------------------------------
        if any(w in text for w in ["mausam", "weather", "temperature", "taapman", "taapmaan"]) or (
            any(w in text for w in ["kaisa hai", "kaisi hai", "ka batao"]) and any(c in text for c in ["delhi", "mumbai", "punjab", "chandigarh", "jaipur", "bangalore", "kolkata", "chennai", "hyderabad", "pune", "lucknow", "bhopal", "patna", "noida", "gurgaon"])
        ):
            clean_loc = re.sub(
                r"\b(aaj|kal|ka|ki|ke|mein|me|par|pe|kaisa|kaisi|hai|kya|batao|dikhao|sunao|mausam|weather|temperature|taapman|taapmaan|today|current|now)\b",
                "",
                text,
                flags=re.IGNORECASE
            ).strip() or "Punjab"
            return FastIntentMatch(
                intent_name="get_weather_info",
                tool_calls=[ToolCall(name="get_weather_info", arguments={"location": clean_loc})],
            )

        # -------------------------------------------------------------
        # 5. Power & System Controls
        # -------------------------------------------------------------
        if any(w in text for w in [
            "laptop shutdown karo", "shutdown laptop", "shutdown pc", "power off computer",
            "laptop band karo", "pc band karo", "computer band karo", "turn off pc", "shutdown"
        ]):
            return FastIntentMatch(
                intent_name="shutdown_pc",
                tool_calls=[ToolCall(name="shutdown_pc", arguments={"close_all_apps": True})],
                immediate_response="Ji Boss, laptop shutdown kar rahi hu.",
            )

        if any(w in text for w in [
            "restart", "reboot", "restart laptop", "restart pc", "laptop restart karo", "pc restart karo"
        ]):
            return FastIntentMatch(
                intent_name="restart_pc",
                tool_calls=[ToolCall(name="restart_pc", arguments={"close_all_apps": True})],
                immediate_response="Ji Boss, restart shuru ho gaya.",
            )

        if any(w in text for w in [
            "lock pc", "lock screen", "laptop lock karo", "screen lock karo", "lock karo", "lock computer"
        ]):
            return FastIntentMatch(
                intent_name="lock_pc",
                tool_calls=[ToolCall(name="lock_pc", arguments={})],
                immediate_response="Ji Boss, screen lock kar di.",
            )

        if any(w in text for w in [
            "sleep mode", "sleep pc", "sleep laptop", "sleep mode mein daalo", "laptop sleep karo"
        ]):
            return FastIntentMatch(
                intent_name="sleep_pc",
                tool_calls=[ToolCall(name="sleep_pc", arguments={})],
                immediate_response="Ji Boss, sleep mode on kar diya.",
            )

        if any(w in text for w in ["cancel shutdown", "shutdown cancel karo", "shutdown roko"]):
            return FastIntentMatch(
                intent_name="cancel_shutdown",
                tool_calls=[ToolCall(name="cancel_shutdown", arguments={})],
                immediate_response="Ji Boss, shutdown cancel kar diya.",
            )

        # -------------------------------------------------------------
        # 6. System Cleaner & Diagnostics
        # -------------------------------------------------------------
        if any(w in text for w in [
            "junk files clean karo", "clean junk", "clean cache", "temp files clean karo",
            "free up space", "cache delete karo", "clear temp", "cleanup pc", "laptop clean karo"
        ]):
            return FastIntentMatch(
                intent_name="clean_junk_files",
                tool_calls=[ToolCall(name="clean_junk_files", arguments={})],
                immediate_response="Ji Boss, junk files clean ho gayi.",
            )

        if any(w in text for w in ["recycle bin empty karo", "empty recycle bin", "recycle bin khali karo"]):
            return FastIntentMatch(
                intent_name="empty_recycle_bin",
                tool_calls=[ToolCall(name="empty_recycle_bin", arguments={})],
                immediate_response="Ji Boss, recycle bin khali ho gaya.",
            )

        if any(w in text for w in ["battery status", "battery kitni hai", "charge kitna hai", "battery percent", "battery"]):
            return FastIntentMatch(
                intent_name="get_battery_status",
                tool_calls=[ToolCall(name="get_battery_status", arguments={})],
                immediate_response="Boss, battery check kar rahi hu.",
            )

        if any(w in text for w in ["time kya hai", "kitne baje hain", "what is the time", "current time", "time batao", "samay kya hai"]):
            return FastIntentMatch(
                intent_name="get_current_time",
                tool_calls=[ToolCall(name="get_current_time", arguments={})],
                immediate_response="Boss, samay check kar rahi hu.",
            )

        # 6.5 PC Problem Solver & Diagnostics
        if any(w in text for w in [
            "check my laptop", "check laptop", "diagnose my laptop", "diagnose laptop",
            "laptop health", "system health", "laptop check karo", "pc check karo",
            "check system", "pc diagnose", "pc check", "laptop check", "pc ki health"
        ]):
            return FastIntentMatch(
                intent_name="get_comprehensive_system_health",
                tool_calls=[ToolCall(name="get_comprehensive_system_health", arguments={})],
                immediate_response="Ji Boss, complete system health check kar rahi hu.",
            )

        if any(w in text for w in [
            "bluetooth nahi chal raha", "bluetooth problem", "why is bluetooth not working",
            "bluetooth fix karo", "bluetooth chalu nahi ho raha", "bluetooth band hai",
            "bluetooth kharab hai", "bluetooth connect nahi ho raha", "bluetooth kaam nahi kar raha",
            "mera bluetooth", "bluetooth check karo", "bluetooth dekho", "bluetooth thik karo"
        ]) or ("bluetooth" in text and any(w in text for w in ["nahi", "not", "problem", "issue", "error", "kharab", "band", "chalu nahi", "mera", "check", "fix", "solve", "thik"])):
            return FastIntentMatch(
                intent_name="diagnose_bluetooth",
                tool_calls=[ToolCall(name="diagnose_system_problem", arguments={"problem_description": "bluetooth", "auto_repair": True})],
                immediate_response="Ji Boss, Bluetooth diagnose aur repair kar rahi hu.",
            )

        if any(w in text for w in [
            "wifi nahi chal raha", "internet nahi chal raha", "wifi problem", "net nahi chal raha",
            "why is wifi not working", "wifi fix karo", "net problem", "internet problem"
        ]) or (any(net_w in text for net_w in ["wifi", "wi-fi", "internet"]) and any(w in text for w in ["nahi", "not", "problem", "issue", "error", "kharab", "band"])):
            return FastIntentMatch(
                intent_name="diagnose_network",
                tool_calls=[ToolCall(name="diagnose_system_problem", arguments={"problem_description": "wifi_network", "auto_repair": True})],
                immediate_response="Ji Boss, Network aur Internet diagnose aur repair kar rahi hu.",
            )

        if any(w in text for w in ["no sound", "awaaz nahi aa rahi", "aawaz nahi aa rahi", "mic nahi chal raha", "speaker problem", "audio problem"]):
            return FastIntentMatch(
                intent_name="diagnose_audio",
                tool_calls=[ToolCall(name="diagnose_system_problem", arguments={"problem_description": "audio", "auto_repair": True})],
                immediate_response="Ji Boss, Audio aur Microphone diagnose aur repair kar rahi hu.",
            )

        if any(w in text for w in ["laptop slow hai", "laptop hang ho raha hai", "laptop freeze ho raha hai", "pc slow hai", "why is my laptop slow"]):
            return FastIntentMatch(
                intent_name="diagnose_performance",
                tool_calls=[ToolCall(name="diagnose_system_problem", arguments={"problem_description": "performance_hang", "auto_repair": True})],
                immediate_response="Ji Boss, System performance aur CPU/RAM load diagnose kar rahi hu.",
            )

        if any(w in text for w in ["system status", "health scan", "cpu usage", "ram usage"]):
            return FastIntentMatch(
                intent_name="get_system_health",
                tool_calls=[ToolCall(name="get_system_status", arguments={})],
                immediate_response="Ji Boss, health scan shuru kar diya.",
            )

        # -------------------------------------------------------------
        # 7. Media Volume & Playback Controls
        # -------------------------------------------------------------
        if any(w in text for w in ["volume up", "volume badhao", "aawaz badhao", "sound badhao"]):
            return FastIntentMatch(
                intent_name="media_volume_up",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "volume_up", "steps": 3})],
                immediate_response="Ji Boss, volume badha diya.",
            )

        if any(w in text for w in ["volume down", "volume kam karo", "aawaz kam karo", "sound kam karo"]):
            return FastIntentMatch(
                intent_name="media_volume_down",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "volume_down", "steps": 3})],
                immediate_response="Ji Boss, volume kam kar diya.",
            )

        if any(w in text for w in ["mute", "mute karo", "aawaz band karo", "unmute"]):
            return FastIntentMatch(
                intent_name="media_mute",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "mute"})],
                immediate_response="Ji Boss, mute kar diya.",
            )

        if any(w in text for w in ["pause", "pause karo", "video pause karo", "song pause karo", "rok do", "stop song"]):
            return FastIntentMatch(
                intent_name="media_pause",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "pause"})],
                immediate_response="Ji Boss, pause kar diya.",
            )

        if any(w in text for w in ["play media", "resume", "chalao media", "unpause"]):
            return FastIntentMatch(
                intent_name="media_play",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "play"})],
                immediate_response="Ji Boss, play kar diya.",
            )

        if any(w in text for w in ["next song", "agla gaana", "next video"]):
            return FastIntentMatch(
                intent_name="media_next",
                tool_calls=[ToolCall(name="control_media", arguments={"action": "next"})],
                immediate_response="Ji Boss, agla gaana laga diya.",
            )

        # -------------------------------------------------------------
        # 8. WhatsApp Quick Actions
        # -------------------------------------------------------------
        if any(w in text for w in ["send karo", "bhejo", "send message", "press enter"]):
            return FastIntentMatch(
                intent_name="send_active_message",
                tool_calls=[ToolCall(name="send_active_message", arguments={})],
                immediate_response="Ji Boss, message send ho gaya.",
            )

        if any(w in text for w in ["msg delete karo", "message delete karo", "unsend karo", "delete message"]):
            return FastIntentMatch(
                intent_name="delete_whatsapp_message",
                tool_calls=[ToolCall(name="delete_whatsapp_message", arguments={})],
                immediate_response="Ji Boss, message delete ho gaya.",
            )

        # No fast rule matched -> Fall back to LLM
        return None


# Global fast intent engine
fast_intent_engine = FastIntentEngine()
