"""Cognitive Action Planner for JARVIS AI.

Transforms raw voice/text commands into structured multi-step execution plans
with entity identification, context resolution, tool dependency mapping,
and verification rules.
"""
from enum import Enum
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.ai.context_memory import context_memory
from backend.ai.providers import ToolCall
from backend.ai.semantic_matcher import semantic_matcher
from backend.core.logger import get_logger

logger = get_logger("ActionPlanner")


class PlanIntent(str, Enum):
    PLAY_VIDEO = "PLAY_VIDEO"
    SEARCH_WEB = "SEARCH_WEB"
    OPEN_APPLICATION = "OPEN_APPLICATION"
    CLOSE_APPLICATION = "CLOSE_APPLICATION"
    CLEAN_APPS = "CLEAN_APPS"
    WHATSAPP_MESSAGE = "WHATSAPP_MESSAGE"
    POWER_CONTROL = "POWER_CONTROL"
    SYSTEM_CLEANER = "SYSTEM_CLEANER"
    DIAGNOSTICS = "DIAGNOSTICS"
    MEDIA_CONTROL = "MEDIA_CONTROL"
    FOLLOWUP_ACTION = "FOLLOWUP_ACTION"
    SILENCE = "SILENCE"
    DIRECT_CHAT = "DIRECT_CHAT"


class PlannedStep(BaseModel):
    """A discrete verifiable step in an action plan."""
    step_id: int
    action_type: str
    tool_call: ToolCall
    description: str
    requires_verification: bool = True
    verification_target: Optional[str] = None


class ActionPlan(BaseModel):
    """Structured end-to-end execution plan."""
    intent: PlanIntent
    target_platform: Optional[str] = None
    target_entity: Optional[str] = None
    steps: List[PlannedStep] = Field(default_factory=list)
    immediate_response: Optional[str] = None
    requires_clarification: bool = False
    clarification_question: Optional[str] = None
    is_direct_chat: bool = False
    direct_chat_response: Optional[str] = None


class ActionPlanner:
    """Cognitive intent parser and action planner."""

    def __init__(self, user_name: str = "Shivam"):
        self.user_name = user_name

    def create_plan(self, user_text: str) -> Optional[ActionPlan]:
        """Analyze user text and generate an execution plan."""
        if not user_text:
            return None

        raw = user_text.strip()
        text = raw.lower()
        # Normalize Hindi negation variants: nahin, nhi, nai, ni, नहीं, नही -> nahi
        text = re.sub(r"\b(nahin|nhi|nai|ni|नहीं|नही)\b", "nahi", text, flags=re.IGNORECASE)
        text = re.sub(r"[?!.,]+$", "", text).strip()

        # 0. Instant Stop / Silence
        if any(text == w or text.startswith(w) for w in [
            "shant ho jao", "chup ho jao", "chup raho", "chup", "stop", "shant", "quiet",
            "stop speaking", "bas", "ruk jao", "bolna band karo", "awaz band karo", "awaaz band karo", "shut up"
        ]):
            return ActionPlan(
                intent=PlanIntent.SILENCE,
                is_direct_chat=True,
                direct_chat_response="Ji Boss, shant ho gayi.",
            )

        # 0.1 Close Tab / Close Video / Stop Playback Intent
        if any(w in text for w in [
            "tab band karo", "tab close karo", "close tab", "video band karo", "video close karo",
            "yeh band karo", "woh band karo", "vah band karo", "band kar do", "band karo", "hata do",
            "browser band karo", "chrome band karo", "youtube band karo"
        ]):
            return ActionPlan(
                intent=PlanIntent.FOLLOWUP_ACTION,
                target_platform="browser",
                target_entity="close_tab",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="close_tab",
                        tool_call=ToolCall(name="close_browser_tab", arguments={"target": "youtube"}),
                        description="Close active YouTube/browser tab",
                    )
                ],
                immediate_response="Ji Boss, tab band kar diya.",
            )

        # Strip leading wake words ("Shivam AI, ...", "Hey Shivam, ...", "Jarvis, ...")
        cmd_text = re.sub(r"^(shivam\s+ai|hey\s+shivam|jarvis|hey\s+jarvis|on\s+jarvis|on\s+shivam)[,\s]+", "", text, flags=re.IGNORECASE).strip()
        cmd_text = re.sub(r"^shivam[,\s]+(?!ko\b|ka\b|ki\b|ke\b|par\b|pe\b|\d|\+)", "", cmd_text, flags=re.IGNORECASE).strip()

        # 0.1 Devanagari Hindi Script Conversion (Unicode safe without ASCII word boundaries)
        cmd_text = re.sub(r"(शिवम|सिवम|शिवम्)", "Shivam", cmd_text)
        cmd_text = re.sub(r"(हर्ष)", "Harsh", cmd_text)
        cmd_text = re.sub(r"(मम्मी|माताजी|मॉम)", "Mom", cmd_text)
        cmd_text = re.sub(r"(पापा|पिताजी|डैड)", "Dad", cmd_text)
        cmd_text = re.sub(r"(आरुष\s+पॉल|आरुष\s+गोला|आरुष\s+भोला|आरुष\s+बोला|आरुश\s+भोला|आरुश\s+बोला|आरुष\s+होना|आरुष\s+होल|आरुष\s+पौल|आरुष|अरुष|आरुश)", "Aarush Bhola", cmd_text)
        cmd_text = re.sub(r"(इंग्लिश\s+बोला|इंग्लिश\s+यादव|एलविश\s+यादव|एल्विश\s+यादव|एल्विस\s+यादव|एलविस\s+यादव|एल्विश|एलविश|एलविस|एल्विस)", "Elvish Yadav", cmd_text)
        cmd_text = re.sub(r"(तारक\s+मेहता|ताराक\s+मेहता)", "Tarak Mehta", cmd_text)
        cmd_text = re.sub(r"(सौरव\s+जोशी|सौरभ\s+जोशी|सौरव|सौरभ)", "Sourav Joshi", cmd_text)
        cmd_text = re.sub(r"(फुकरा\s+इंसान|अभिषेक\s+मल्हान)", "Fukra Insaan", cmd_text)
        cmd_text = re.sub(r"(ट्रिगर्ड\s+इंसान|निश्चय\s+मल्हान)", "Triggered Insaan", cmd_text)
        cmd_text = re.sub(r"(टेक्नो\s+गेमर्स|उज्ज्वल)", "Techno Gamerz", cmd_text)
        cmd_text = re.sub(r"(टोटल\s+गेमिंग|अज्जू\s+भाई)", "Total Gaming", cmd_text)
        cmd_text = re.sub(r"(कैरी\s+मिनाटी|कैरीमिनाटी|कैरी)", "CarryMinati", cmd_text)
        cmd_text = re.sub(r"(समय\s+रैना|समय)", "Samay Raina", cmd_text)
        cmd_text = re.sub(r"(हर्ष\s+बेनीवाल)", "Harsh Beniwal", cmd_text)
        cmd_text = re.sub(r"(आशीष\s+चंचलानी)", "Ashish Chanchlani", cmd_text)
        cmd_text = re.sub(r"(भुवन\s+बाम|बीबी\s+की\s+वाइन्स)", "BB Ki Vines", cmd_text)
        cmd_text = re.sub(r"(ध्रुव\s+राठी)", "Dhruv Rathee", cmd_text)
        cmd_text = re.sub(r"(संदीप\s+माहेश्वरी)", "Sandeep Maheshwari", cmd_text)
        cmd_text = re.sub(r"(रणवीर\s+अल्लाहबादिया|बीर\s+बाईसेप्स)", "Ranveer Allahbadia", cmd_text)
        cmd_text = re.sub(r"(राज\s+शामानी)", "Raj Shamani", cmd_text)
        cmd_text = re.sub(r"(तन्मय\s+भट्ट)", "Tanmay Bhat", cmd_text)
        cmd_text = re.sub(r"(जाकिर\s+खान)", "Zakir Khan", cmd_text)
        cmd_text = re.sub(r"(मुनव्वर\s+फारूकी)", "Munawar Faruqui", cmd_text)
        cmd_text = re.sub(r"(खान\s+सर)", "Khan Sir", cmd_text)
        cmd_text = re.sub(r"(लल्लनटॉप)", "The Lallantop", cmd_text)
        # Apps and Technical Utilities in Devanagari
        cmd_text = re.sub(r"(टास्क\s+मैनेजर|टास्क\s+मेनेजर|टास्क)", "task manager", cmd_text)
        cmd_text = re.sub(r"(कंट्रोल\s+पैनल)", "control panel", cmd_text)
        cmd_text = re.sub(r"(डिवाइस\s+मैनेजर)", "device manager", cmd_text)
        cmd_text = re.sub(r"(रिसोर्स\s+मॉनिटर)", "resource monitor", cmd_text)
        cmd_text = re.sub(r"(इवेंट\s+व्यूअर)", "event viewer", cmd_text)
        cmd_text = re.sub(r"(रजिस्ट्री\s+एडिटर|रजिस्ट्री)", "regedit", cmd_text)
        cmd_text = re.sub(r"(सिस्टम\s+इनफार्मेशन|सिस्टम\s+इन्फो)", "system info", cmd_text)
        cmd_text = re.sub(r"(व्हाट्सएप|व्हाट्सऐप|वाट्सएप|वाटसप)", "whatsapp", cmd_text)
        cmd_text = re.sub(r"(गूगल\s+क्रोम|क्रोम)", "chrome", cmd_text)
        cmd_text = re.sub(r"(नोटपैड)", "notepad", cmd_text)
        cmd_text = re.sub(r"(कैलकुलेटर|कैल्क)", "calculator", cmd_text)
        cmd_text = re.sub(r"(स्पॉटिफाई|स्पॉटिफ़ाई|स्पॉटीफाई)", "spotify", cmd_text)
        cmd_text = re.sub(r"(टेलीग्राम)", "telegram", cmd_text)
        cmd_text = re.sub(r"(डिस्कॉर्ड)", "discord", cmd_text)
        cmd_text = re.sub(r"(पेंट)", "paint", cmd_text)
        cmd_text = re.sub(r"(फाइल\s+एक्सप्लोरर|एक्सप्लोरर|माय\s+कंप्यूटर)", "explorer", cmd_text)
        cmd_text = re.sub(r"(वीएस\s+कोड|कोड\s+एडिटर)", "vscode", cmd_text)
        cmd_text = re.sub(r"(सेटिंग्स|सेटिंग)", "settings", cmd_text)
        cmd_text = re.sub(r"(कैमरा)", "camera", cmd_text)

        # System Power & Maintenance in Devanagari
        cmd_text = re.sub(r"(शटडाउन|शट\s+डाउन|टर्न\s+ऑफ)", "shutdown", cmd_text)
        cmd_text = re.sub(r"(रिस्टार्ट|रीस्टार्ट|रीबूट)", "restart", cmd_text)
        cmd_text = re.sub(r"(स्लीप)", "sleep", cmd_text)
        cmd_text = re.sub(r"(लॉक)", "lock", cmd_text)
        cmd_text = re.sub(r"(पीसी|कंप्यूटर|लैपटॉप)", "pc", cmd_text)
        cmd_text = re.sub(r"(द|दी)", "the", cmd_text)
        cmd_text = re.sub(r"(फालतू|अनावश्यक)", "unnecessary", cmd_text)
        cmd_text = re.sub(r"(टास्कबार|टास्क\s+बार)", "taskbar", cmd_text)
        cmd_text = re.sub(r"(टैब्स|टैब|ऐप्स|एप्स)", "tabs", cmd_text)
        cmd_text = re.sub(r"(जंक\s+फाइल्स|जंक|कचरा)", "junk files", cmd_text)
        cmd_text = re.sub(r"(रीसायकल\s+बिन|कचरा\s+डिब्बा)", "recycle bin", cmd_text)
        cmd_text = re.sub(r"(वॉल्यूम|आवाज)", "volume", cmd_text)
        cmd_text = re.sub(r"(म्यूट|शांत)", "mute", cmd_text)
        cmd_text = re.sub(r"(अनम्यूट)", "unmute", cmd_text)
        cmd_text = re.sub(r"(बैटरी)", "battery", cmd_text)
        cmd_text = re.sub(r"(समय|टाइम)", "time", cmd_text)
        cmd_text = re.sub(r"(हटाओ|हटा\s+दो|क्लीन\s+करो|साफ\s+करो)", "clean", cmd_text)
        cmd_text = re.sub(r"(बंद\s+करो|बंद\s+कर\s+दो|काटो)", "close", cmd_text)

        # Ordinals in Devanagari
        cmd_text = re.sub(r"(फर्स्ट\s+नंबर|फर्स्ट|पहले\s+नंबर|पहली|पहला|पहले|1\s+नंबर)", "1st", cmd_text)
        cmd_text = re.sub(r"(सेकंड\s+नंबर|सेकेंड\s+नंबर|सेकंड|सेकेंड|दूसरे\s+नंबर|दूसरी|दूसरा|दूसरे|2\s+नंबर)", "2nd", cmd_text)
        cmd_text = re.sub(r"(थर्ड\s+नंबर|थर्ड|तीसरे\s+नंबर|तीसरी|तीसरा|तीसरे|3\s+नंबर)", "3rd", cmd_text)
        cmd_text = re.sub(r"(फोर्थ\s+नंबर|फोर्थ|चौथे\s+नंबर|चौथी|चौथा|चौथे|4\s+नंबर)", "4th", cmd_text)
        cmd_text = re.sub(r"(फिफ्थ\s+नंबर|फिफ्थ|पांचवे\s+नंबर|पांचवी|पांचवा|पांचवे|5\s+नंबर)", "5th", cmd_text)
        cmd_text = re.sub(r"(सिक्स्थ\s+नंबर|सिक्स्थ|छठे\s+नंबर|छठी|छठा|छठे|6\s+नंबर)", "6th", cmd_text)
        cmd_text = re.sub(r"(रिएक्शन)", "reaction", cmd_text)

        # Devanagari Verbs & Request Forms
        cmd_text = re.sub(r"(लगाओ|लगाना|लगा\s+देना|लगा\s+दे|लगा\s+दो|लगाएं|लगा\s+दीजिए|लगा\s+के\s+दे|लगा\s+के\s+दो|लगाना\s+है)", "play", cmd_text)
        cmd_text = re.sub(r"(चलाओ|चलाना|चला\s+देना|चला\s+दे|चला\s+दो|चलाएं|चला\s+दीजिए|चला\s+के\s+दे|चला\s+के\s+दो|चलाना\s+है)", "play", cmd_text)
        cmd_text = re.sub(r"(बजाओ|बजाना|बजा\s+देना|बजा\s+दे|बजा\s+दो|बजाएं|बजा\s+दीजिए|बजाना\s+है)", "play", cmd_text)
        cmd_text = re.sub(r"(दिखाओ|दिखाना|दिखा\s+देना|दिखा\s+दे|दिखा\s+दो|दिखाएं|दिखा\s+दीजिए|दिखाना\s+है|दिखा)", "play", cmd_text)
        cmd_text = re.sub(r"(सुनाओ|सुनाना|सुना\s+देना|सुना\s+दे|सुना\s+दो|सुनाएं|सुना\s+दीजिए|सुनाना\s+है|सुना)", "play", cmd_text)
        cmd_text = re.sub(r"(देखना\s+है|देखना\s+चाहता\s+हूं|देखना\s+चाहती\s+हूं|सुनना\s+है|सुनना\s+चाहता\s+हूं)", "play", cmd_text)
        cmd_text = re.sub(r"(इसे|इसको|इसे\s+भी|उसको|उसे|इस|उस)", "isse", cmd_text)

        cmd_text = re.sub(r"(लेट\s+नाइट\s+यारी|लेट\s+नाइट\s+यार|लेट\s+नाइट)", "Late Night Yaari", cmd_text)
        cmd_text = re.sub(r"(स्पोर्ट्स\s+यारी)", "Sports Yaari", cmd_text)
        cmd_text = re.sub(r"(जो\s+अभी\s+लाइव\s+है|जो\s+लाइव\s+है|लाइव\s+चल\s+रहा\s+है|लाइव\s+स्ट्रीम)", "live", cmd_text)
        cmd_text = re.sub(r"(लाइव|लाईव)", "live", cmd_text)

        cmd_text = re.sub(r"(युटुब|यूट्यूब|युट्यूब|यूट्युब)", "youtube", cmd_text)
        cmd_text = re.sub(r"(व्लॉग|ब्लॉग|ब्लॉक)", "vlog", cmd_text)
        cmd_text = re.sub(r"(लेटेस्ट|नया|न्यू|ताज़ा|आज\s+का|आज\s+आया|आज)", "latest", cmd_text)
        cmd_text = re.sub(r"(वीडियो|विडियो)", "video", cmd_text)
        cmd_text = re.sub(r"(?<!ल)(गाना|गीत|सॉन्ग)", "song", cmd_text)
        cmd_text = re.sub(r"(एपिसोड|भाग)", "episode", cmd_text)
        cmd_text = re.sub(r"(कॉल|फोन|वॉइस\s+कॉल|वीडियो\s+कॉल)", "call", cmd_text)
        cmd_text = re.sub(r"(मैसेज|संदेश|मेसेज|मैसेज)", "message", cmd_text)
        cmd_text = re.sub(r"(भेजो|सेंड|सेंड\s+करो)", "send", cmd_text)
        cmd_text = re.sub(r"(ओपन|खोलें|खोलो|खोलना|खोल\s+दो|खोल\s+देना|शुरू\s+करो|स्टार्ट|चालू\s+करो|चालू\s+कर\s+दो|ऑन\s+करो)", "open", cmd_text)
        cmd_text = re.sub(r"(प्ले|बजाओ|चलाओ|चला\s+दो|दिखाओ|सर्च)", "play", cmd_text)
        cmd_text = re.sub(r"(का|की|के|में|पे|पर|वाला|वाली|वाले|जो|है|ना|वो|वह|ये|यह|करो|कर\s+दो)", " ", cmd_text)
        cmd_text = re.sub(r"(गोला|पॉल|होना|होल|पौल|बोला)", "", cmd_text)

        # Comprehensive Speech Transcription Normalization (Hinglish & Devanagari)
        cmd_text = re.sub(r"\b(late\s+night\s+yaari|late\s+night\s+yaar|लेट\s+नाइट\s+यारी|लेट\s+नाइट\s+यार|लेट\s+नाइट)\b", "Late Night Yaari", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(sports\s+yaari|स्पोर्ट्स\s+यारी)\b", "Sports Yaari", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(indian\s+backpacker|इंडियन\s+बैकपैकर|इंडियन\s+बैकपेकर|बैकपैकर)\b", "Indian Backpacker", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(aarush\s+bhola|arush\s+bhola|आरुष\s+भोला|आरुश\s+भोला)\b", "Aarush Bhola", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(?:aarush|arush|harish|harris|barish|paras|who\s+is|whose|warish)\s+(?:bhola|pura|pola|gola|hona|ola|gulabo|bola|bhole)\b", "Aarush Bhola", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(barish\s+kab\s+vlog|barish\s+ka\s+vlog|barish\s+kab|barish\s+pura)\b", "Aarush Bhola", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(elvish\s+yadav|elvish|elvis|elwish|alvish|english\s+bola|एल्विश\s+यादव|एल्विश)\b", "Elvish Yadav", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(tarak\s+mehta|taarak\s+mehta|तारक\s+मेहता)\b", "Taarak Mehta", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(sourav\s+joshi|saurav\s+joshi|सौरव\s+जोशी)\b", "Sourav Joshi", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(fukra\s+insaan|abhishek\s+malhan|फुकरा\s+इंसान)\b", "Fukra Insaan", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(triggered\s+insaan|nischay\s+malhan|ट्रिगर्ड\s+इंसान)\b", "Triggered Insaan", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(techno\s+gamerz|ujjwal\s+gamer|टेक्नो\s+गेमर्स)\b", "Techno Gamerz", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(total\s+gaming|ajju\s+bhai|टोटल\s+गेमिंग)\b", "Total Gaming", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(flying\s+beast|gaurav\s+taneja|फ्लाइंग\s+बीस्ट)\b", "Flying Beast", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(samay\s+raina|samay|समय\s+रैना|सुमिरन)\b", "Samay Raina", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(munawar\s+faruqui|munawar|मुनव्वर\s+फारूक|मुनव्वर\s+फ़ारूक़ी|मुनव्वर)\b", "Munawar Faruqui", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(salman\s+khan|salman|सलमान\s+खान|सलमान)\b", "Salman Khan", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(sushant\s+mehta|sushant|सुशांत\s+मेहता|सुशांत)\b", "Sushant Mehta", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(indias\s+got\s+latent|india's\s+got\s+latent|got\s+latent|latent|ऑटो\s+वाला|ऑटो\s+फीचर)\b", "Indias Got Latent", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(carry\s+minati|carryminati|कैरी\s+मिनाटी)\b", "CarryMinati", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(dhruv\s+rathee|ध्रुव\s+राठी)\b", "Dhruv Rathee", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(sandeep\s+maheshwari|संदीप\s+माहेश्वरी)\b", "Sandeep Maheshwari", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(tanmay\s+bhat|तन्मय\s+भट्ट)\b", "Tanmay Bhat", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(beerbiceps|ranveer\s+allahbadia)\b", "Ranveer Allahbadia", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(raj\s+shamani)\b", "Raj Shamani", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(live\s+speedy|live\s+speed|speedy|ishowspeed|showspeed|लाइव\s+स्पीडी|लाइव\s+स्पीड)\b", "iShowSpeed", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(harsh\s+beniwal|harsh\s+benival|हर्ष\s+बेनीवाल)\b", "Harsh Beniwal", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(round2hell|round\s+2\s+hell|राउंड\s+टू\s+हेल)\b", "Round2hell", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(bb\s+ki\s+vines|bhuvan\s+bam|बीबी\s+की\s+वाइन्स)\b", "BB Ki Vines", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(ashish\s+chanchlani|आशीष\s+चंचलानी)\b", "Ashish Chanchlani", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(kullu\s+and\s+sahil|kullu\s+and\s+sahi|kullu\s+sahil|kullu|aaditya\s+kulshreshtha|कुल्लू)\b", "Kullu Sahil", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(coffee\s+with\s+carryminati|koffee\s+with\s+carryminati|coffee\s+with\s+carry)\b", "Coffee with CarryMinati", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(paradox|hustle\s+paradox|पैराडॉक्स)\b", "Paradox", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(death\s+nut|death\s+nut\s+challenge)\b", "Death Nut Challenge", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(blog|block|blod|blouse|vlogs|blogs)\b", "vlog", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(real|rail|riyal|reels)\b", "reel", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(shot|shots|shotgun|chhot|chot|shorts)\b", "short", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(fight\s+mis|flight\s+mis)\b", "flight miss", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(jowar|jo\s+war)\b", "jo", cmd_text, flags=re.IGNORECASE)

        # Clean spatial prefixes & screen markers ("right side mein", "right side", "sidebar", etc.)
        cmd_text = re.sub(r"\b(right\s+side\s+mein|right\s+side\s+pe|right\s+side\s+wala|right\s+side\s+wali|right\s+side|left\s+side\s+mein|left\s+side\s+pe|left\s+side\s+wala|left\s+side\s+wali|left\s+side|sidebar\s+mein|sidebar\s+pe|sidebar|screen\s+par|screen\s+pe)\b", "", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(dikh\s+rahi\s+hai|dikh\s+raha\s+hai|dikh\s+rhi\s+hai|dikh\s+rahe\s+hain|gobhi\s+dikh\s+rahi\s+hai|gobhi)\b", "", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(was\s+written|is\s+written|written\s+hai|written|text\s+padh\s+ke|text\s+pad\s+ke|text\s+padke|text\s+padhke|likha\s+hai|likha\s+hua\s+hai|likha\s+hua|likha|jo\s+likha\s+hai|read\s+karke|padh\s+ke|pad\s+ke|padke|padhke)\b", "", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(coronavirus|corona|karona)\b", "kar do voice", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(big\s+eye\s+drop|eye\s+drop|drop|bada\s+drop)\b", "", cmd_text, flags=re.IGNORECASE)

        # Clean Hindi / Hinglish Slang Words
        cmd_text = re.sub(r"\b(blockbuster|bawaal|dhamaal|kalesh|bhasad|faad|solid|tagda|mast|jabardast|superhit|dhinchak|crazy|op|wavy|faadu|topper|viral|top|hit|best)\b", "", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(yrr|yaar|bhai|bhaiya|bro|dude|dost|boss|kisi\s+bhi|kisi\s+ka\s+bhi|koi\s+bhi|apne\s+aap|fatfat|jaldi\s+se|jaldi|zara|thoda|ek\s+dum)\b", "", cmd_text, flags=re.IGNORECASE)

        # Clean conversational timestamps & relative clauses ("jo a jaaye", "jo aaj aaya hai", "ka jo aaj latest wala blog hai")
        cmd_text = re.sub(r"\b(jo\s+a\s*jaaye|jo\s+aaj\s+aaye|jo\s+aaj\s+new\s+aa\s*ya\s+hai|jo\s+aaj\s+aaya\s+hai|jo\s+aaj\s+aaya|jo\s+naya\s+aaya\s+hai|jo\s+abhi\s+aaya\s+hai|jo\s+abhi\s+release\s+hua\s+hai|jo\s+\d+\s+ghante\s+pahle\s+hai|jo\s+\d+\s+ghante\s+pehle\s+hai|aaj\s+aaya\s+hai|new\s+aaj\s+aaya|aaj\s+ka|naya\s+wala|new\s+wala|latest\s+wala)\b", "latest", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(ka\s+jo\s+latest|jo\s+latest|ka\s+jo\s+new|ka\s+new|jo\s+new)\b", "latest", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(hai\s+vah\s+lagao|hai\s+woh\s+lagao|vah\s+lagao|woh\s+lagao|ye\s+lagao|yah\s+lagao|lagana|chalao|chalana)\b", "lagao", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(yah\s+wala\s+lagana|woh\s+wala\s+lagana|ye\s+wala\s+lagana|woh\s+wali\s+lagana|aur\s+usko\s+love\s+love|love\s+love|search\s+karna)\b", "", cmd_text, flags=re.IGNORECASE)

        # Clean redundant double vlog/latest words
        cmd_text = re.sub(r"\b(latest\s+latest|latest\s+new|new\s+latest)\b", "latest", cmd_text, flags=re.IGNORECASE)
        cmd_text = re.sub(r"\b(vlog\s+vlog)\b", "vlog", cmd_text, flags=re.IGNORECASE)

        # Strip leading conversational fillers ("chalana", "arre", "suno", "oye", "play")
        cmd_text = re.sub(r"^(chalana|chalao|lagao|lagana|bajao|dikhao|sunao|arre|suno|oye|play|kholo)[,\s]+", "", cmd_text, flags=re.IGNORECASE).strip()

        # 0.15 Power Management: Shutdown, Restart, Sleep, Lock, Cancel
        # e.g., "shutdown the pc", "remove all unnecessary tabs in task bar before shutdown", "pc band karo", "restart pc", "sleep pc", "lock pc"
        if any(w in cmd_text.lower() for w in ["shutdown", "shut down", "turn off pc", "turn off computer", "pc band", "computer band", "laptop band"]):
            return ActionPlan(
                intent=PlanIntent.POWER_CONTROL,
                target_platform="system",
                target_entity="shutdown",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="shutdown_pc",
                        tool_call=ToolCall(name="shutdown_pc", arguments={"close_all_apps": True, "delay_seconds": 5}),
                        description="Close open tabs/apps and shut down PC",
                        requires_verification=True,
                    )
                ],
                immediate_response="Ji Boss, sabhi apps band karke computer shutdown kar rahi hu. Goodbye!",
            )
        elif any(w in cmd_text.lower() for w in ["restart", "reboot", "pc restart", "computer restart", "laptop restart"]):
            return ActionPlan(
                intent=PlanIntent.POWER_CONTROL,
                target_platform="system",
                target_entity="restart",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="restart_pc",
                        tool_call=ToolCall(name="restart_pc", arguments={"close_all_apps": True, "delay_seconds": 5}),
                        description="Close open tabs/apps and restart PC",
                        requires_verification=True,
                    )
                ],
                immediate_response="Ji Boss, sabhi apps band karke computer restart kar rahi hu.",
            )
        elif any(w in cmd_text.lower() for w in ["cancel shutdown", "abort shutdown", "shutdown cancel"]):
            return ActionPlan(
                intent=PlanIntent.POWER_CONTROL,
                target_platform="system",
                target_entity="cancel_shutdown",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="cancel_shutdown",
                        tool_call=ToolCall(name="cancel_shutdown", arguments={}),
                        description="Cancel pending shutdown",
                        requires_verification=True,
                    )
                ],
                immediate_response="Ji Boss, scheduled shutdown cancel kar diya.",
            )
        # 0.19 Exact Volume Percentage Setting (e.g. "voice 57 kar do", "volume 57 kar do", "57 kar do", "sound 80%", "57 coronavirus")
        vol_pct_match = re.search(r"\b(?:voice|volume|sound|aawaz|awaz)?\s*(\d{1,3})\s*(?:%|percent|pratishat)?\s*(?:pe\s+set\s+karo|set\s+karo|karo\s+voice|karo\s+volume|kar\s+do|kardo|karo|coronavirus)?\b", cmd_text, flags=re.IGNORECASE)
        if vol_pct_match and (
            any(w in cmd_text.lower() for w in ["voice", "volume", "sound", "aawaz", "awaz", "percent", "%", "set", "kar do", "kardo", "coronavirus"])
            or re.match(r"^\d{1,3}\s*(karo|kar\s+do|kardo)?$", cmd_text.strip())
        ):
            try:
                target_vol = int(vol_pct_match.group(1))
                if 0 <= target_vol <= 100:
                    return ActionPlan(
                        intent=PlanIntent.MEDIA_CONTROL,
                        target_platform="system",
                        target_entity=f"volume_{target_vol}",
                        steps=[
                            PlannedStep(
                                step_id=1,
                                action_type="control_media",
                                tool_call=ToolCall(name="control_media", arguments={"action": "set_volume", "level": target_vol}),
                                description=f"Set system volume to {target_vol}%",
                            )
                        ],
                        immediate_response=f"Ji Boss, volume {target_vol}% kar diya.",
                    )
            except Exception:
                pass
        elif any(w in cmd_text.lower() for w in ["sleep mode", "sleep pc", "put pc to sleep", "sleep computer"]):
            return ActionPlan(
                intent=PlanIntent.POWER_CONTROL,
                target_platform="system",
                target_entity="sleep",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="sleep_pc",
                        tool_call=ToolCall(name="sleep_pc", arguments={}),
                        description="Put computer to sleep",
                        requires_verification=True,
                    )
                ],
                immediate_response="Ji Boss, computer ko sleep mode me daal diya.",
            )
        elif any(w in cmd_text.lower() for w in ["lock pc", "lock screen", "lock workstation", "screen lock"]):
            return ActionPlan(
                intent=PlanIntent.POWER_CONTROL,
                target_platform="system",
                target_entity="lock",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="lock_pc",
                        tool_call=ToolCall(name="lock_pc", arguments={}),
                        description="Lock Windows workstation",
                        requires_verification=True,
                    )
                ],
                immediate_response="Ji Boss, screen lock kar di.",
            )

        # 0.16 Clean Background Apps & Taskbar Tabs
        # e.g., "remove all unnecessary tabs in task bar", "close unnecessary apps", "clean background apps", "faltu tabs band karo", "faltu apps band karo"
        # Block: "taskbar mein antigravity minimize karo" should NOT match here
        _has_win_action = any(w in cmd_text.lower() for w in ["minimize", "maximize", "restore", "chhota karo", "bada karo"])
        if not _has_win_action and any(w in cmd_text.lower() for w in [
            "unnecessary tab", "unnecessary app", "background app", "unnecessary tabs", "unnecessary apps",
            "taskbar tabs", "task bar tabs", "taskbar", "task bar", "faltu tab", "faltu app", "faltu apps", "clean apps",
            "clean unused", "close all tabs", "close open tabs", "clean background", "close unused", "free ram", "free memory"
        ]):
            return ActionPlan(
                intent=PlanIntent.CLEAN_APPS,
                target_platform="system",
                target_entity="clean_apps",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="clean_unused_apps",
                        tool_call=ToolCall(name="clean_unused_apps", arguments={"close_browsers": True}),
                        description="Close unused taskbar apps and background tabs",
                        requires_verification=True,
                    )
                ],
                immediate_response="Ji Boss, sabhi unnecessary tabs aur background apps band kar diye.",
            )

        # 0.17 System Junk & Cache Cleaner
        # e.g., "clean junk files", "clean cache", "delete temp files", "empty recycle bin"
        if any(w in cmd_text.lower() for w in ["junk files", "clean junk", "temp files", "temporary files", "clean cache", "free storage", "free disk"]):
            return ActionPlan(
                intent=PlanIntent.SYSTEM_CLEANER,
                target_platform="system",
                target_entity="clean_junk",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="clean_junk_files",
                        tool_call=ToolCall(name="clean_junk_files", arguments={}),
                        description="Clean temporary junk and cache files",
                        requires_verification=True,
                    )
                ],
                immediate_response="Ji Boss, temporary junk files clean kar di.",
            )
        elif any(w in cmd_text.lower() for w in ["empty recycle bin", "clean recycle bin", "recycle bin empty", "trash clean"]):
            return ActionPlan(
                intent=PlanIntent.SYSTEM_CLEANER,
                target_platform="system",
                target_entity="empty_recycle_bin",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="empty_recycle_bin",
                        tool_call=ToolCall(name="empty_recycle_bin", arguments={}),
                        description="Empty Windows Recycle Bin",
                        requires_verification=True,
                    )
                ],
                immediate_response="Ji Boss, Recycle Bin empty kar diya.",
            )

        # 0.18 Media & Volume Control
        # e.g., "volume up", "volume badhao", "volume down", "volume kam karo", "mute karo", "unmute"
        if any(w in cmd_text.lower() for w in ["volume up", "volume badhao", "volume badha", "volume high", "volume tej", "sound badhao"]):
            return ActionPlan(
                intent=PlanIntent.MEDIA_CONTROL,
                target_platform="system",
                target_entity="volume_up",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="control_media",
                        tool_call=ToolCall(name="control_media", arguments={"action": "volume_up"}),
                        description="Increase system volume",
                    )
                ],
                immediate_response="Ji Boss, volume badha diya.",
            )
        elif any(w in cmd_text.lower() for w in ["volume down", "volume kam", "volume low", "volume dheema", "volume dhima", "sound kam"]):
            return ActionPlan(
                intent=PlanIntent.MEDIA_CONTROL,
                target_platform="system",
                target_entity="volume_down",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="control_media",
                        tool_call=ToolCall(name="control_media", arguments={"action": "volume_down"}),
                        description="Decrease system volume",
                    )
                ],
                immediate_response="Ji Boss, volume kam kar diya.",
            )
        elif any(w in cmd_text.lower() for w in ["mute", "unmute", "silent karo"]):
            return ActionPlan(
                intent=PlanIntent.MEDIA_CONTROL,
                target_platform="system",
                target_entity="mute",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="control_media",
                        tool_call=ToolCall(name="control_media", arguments={"action": "mute"}),
                        description="Toggle system mute",
                    )
                ],
                immediate_response="Ji Boss, volume mute/unmute kar diya.",
            )
        # 0.18.4 Exact Video Timestamp Seek ("53 minute pe karo", "iss video ko bhaga ke 53 minutes pe karo", "12 minute 30 second par karo")
        ts_seek_match = re.search(r"\b(?:video|iss\s+video)?\s*(?:ko\s+)?(?:bhaga\s+ke\s+|bhaga\s+k|karke\s+)?(\d{1,3})\s*(?:minute|min|m)s?\s*(?:(\d{1,2})\s*(?:second|sec|s)?)?\s*(?:par|pe|pe\s+karo|par\s+karo|par\s+le\s+jao|le\s+jao|par\s+set\s+karo|set\s+karo)?\b", cmd_text, flags=re.IGNORECASE)
        if ts_seek_match and any(w in cmd_text.lower() for w in ["minute", "min", "bhaga", "seek", "karo", "le jao", "set"]):
            m_val = int(ts_seek_match.group(1))
            s_val = int(ts_seek_match.group(2)) if ts_seek_match.group(2) else 0
            total_sec = m_val * 60 + s_val
            t_param = f"{m_val}m{s_val}s" if s_val else f"{m_val}m"
            disp_str = f"{m_val} minute {s_val} second" if s_val else f"{m_val} minute"
            return ActionPlan(
                intent=PlanIntent.MEDIA_CONTROL,
                target_platform="system",
                target_entity=f"seek_{t_param}",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="control_media",
                        tool_call=ToolCall(
                            name="control_media",
                            arguments={"action": "seek_timestamp", "level": total_sec, "time_str": t_param}
                        ),
                        description=f"Seek YouTube video to {disp_str}",
                    )
                ],
                immediate_response=f"Ji Boss, video ko {disp_str} par seek kar diya.",
            )
        elif any(w in cmd_text.lower() for w in [
            "video aage", "aage karo", "aage badhao", "bhagao", "fast forward", "forward video",
            "10 sec aage", "10 second aage", "video bhagao", "aage le jao", "seek forward"
        ]):
            return ActionPlan(
                intent=PlanIntent.MEDIA_CONTROL,
                target_platform="system",
                target_entity="seek_forward",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="control_media",
                        tool_call=ToolCall(name="control_media", arguments={"action": "seek_forward"}),
                        description="Seek video forward",
                    )
                ],
                immediate_response="Ji Boss, video aage kar diya.",
            )
        elif any(w in cmd_text.lower() for w in [
            "video peeche", "video piche", "peeche karo", "piche karo", "rewind", "10 sec peeche",
            "10 sec piche", "10 second peeche", "10 second piche", "seek backward", "back karo video"
        ]):
            return ActionPlan(
                intent=PlanIntent.MEDIA_CONTROL,
                target_platform="system",
                target_entity="seek_backward",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="control_media",
                        tool_call=ToolCall(name="control_media", arguments={"action": "seek_backward"}),
                        description="Seek video backward",
                    )
                ],
                immediate_response="Ji Boss, video peeche kar diya.",
            )
        elif any(w in cmd_text.lower() for w in ["speed badhao", "speed fast", "video fast karo", "speed up", "playback speed badhao"]):
            return ActionPlan(
                intent=PlanIntent.MEDIA_CONTROL,
                target_platform="system",
                target_entity="speed_up",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="control_media",
                        tool_call=ToolCall(name="control_media", arguments={"action": "speed_up"}),
                        description="Increase video playback speed",
                    )
                ],
                immediate_response="Ji Boss, video speed badha di.",
            )
        elif any(w in cmd_text.lower() for w in ["speed kam", "speed slow", "video slow karo", "speed down", "playback speed kam"]):
            return ActionPlan(
                intent=PlanIntent.MEDIA_CONTROL,
                target_platform="system",
                target_entity="speed_down",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="control_media",
                        tool_call=ToolCall(name="control_media", arguments={"action": "speed_down"}),
                        description="Decrease video playback speed",
                    )
                ],
                immediate_response="Ji Boss, video speed kam kar di.",
            )
        elif any(w in cmd_text.lower() for w in ["fullscreen", "full screen", "bada karo", "video bada karo", "large screen"]):
            return ActionPlan(
                intent=PlanIntent.MEDIA_CONTROL,
                target_platform="system",
                target_entity="fullscreen",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="control_media",
                        tool_call=ToolCall(name="control_media", arguments={"action": "fullscreen"}),
                        description="Toggle fullscreen video",
                    )
                ],
                immediate_response="Ji Boss, fullscreen kar diya.",
            )
        elif any(w in cmd_text.lower() for w in ["subtitle", "subtitles", "caption", "captions"]):
            return ActionPlan(
                intent=PlanIntent.MEDIA_CONTROL,
                target_platform="system",
                target_entity="captions",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="control_media",
                        tool_call=ToolCall(name="control_media", arguments={"action": "captions"}),
                        description="Toggle video captions/subtitles",
                    )
                ],
                immediate_response="Ji Boss, subtitles toggle kar diye.",
            )
        elif any(w in cmd_text.lower() for w in ["agla short", "next short", "niche wala short"]):
            return ActionPlan(
                intent=PlanIntent.MEDIA_CONTROL,
                target_platform="system",
                target_entity="next_short",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="control_media",
                        tool_call=ToolCall(name="control_media", arguments={"action": "next_short"}),
                        description="Swipe to next short",
                    )
                ],
                immediate_response="Ji Boss, agla short chala diya.",
            )
        elif any(w in cmd_text.lower() for w in ["piche wala short", "peeche wala short", "previous short", "upar wala short"]):
            return ActionPlan(
                intent=PlanIntent.MEDIA_CONTROL,
                target_platform="system",
                target_entity="prev_short",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="control_media",
                        tool_call=ToolCall(name="control_media", arguments={"action": "prev_short"}),
                        description="Swipe to previous short",
                    )
                ],
                immediate_response="Ji Boss, pichla short chala diya.",
            )
        elif any(w in cmd_text.lower() for w in ["video pause", "pause video", "video stop", "stop video", "video resume", "resume video", "pause music", "resume music"]):
            return ActionPlan(
                intent=PlanIntent.MEDIA_CONTROL,
                target_platform="system",
                target_entity="play_pause",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="control_media",
                        tool_call=ToolCall(name="control_media", arguments={"action": "play_pause"}),
                        description="Pause/Resume video playback",
                    )
                ],
                immediate_response="Ji Boss, video pause/play kar diya.",
            )

        # 0.2 Universal History Navigation ("back jao", "peeche jao", "forward jao")
        if any(cmd_text.startswith(w) or cmd_text == w for w in ["back jao", "peeche jao", "piche jao", "go back", "back"]):
            return ActionPlan(
                intent=PlanIntent.FOLLOWUP_ACTION,
                target_platform="browser",
                target_entity="back",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="navigate_back_forward",
                        tool_call=ToolCall(name="navigate_back_forward", arguments={"direction": "back"}),
                        description="Navigate back in active window",
                    )
                ],
                immediate_response="Ji Boss, back chali gayi.",
            )
        elif any(cmd_text.startswith(w) or cmd_text == w for w in ["forward jao", "aage jao", "go forward"]):
            return ActionPlan(
                intent=PlanIntent.FOLLOWUP_ACTION,
                target_platform="browser",
                target_entity="forward",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="navigate_back_forward",
                        tool_call=ToolCall(name="navigate_back_forward", arguments={"direction": "forward"}),
                        description="Navigate forward in active window",
                    )
                ],
                immediate_response="Ji Boss, aage navigate kar diya.",
            )

        # 0.3 Universal Screen Scrolling ("scroll karo", "scroll kar do", "neeche scroll karo", "upar scroll karo", "scroll down", "scroll up", "thoda neeche karo")
        if any(w in cmd_text.lower() for w in [
            "scroll up", "upar scroll", "scroll upar", "upar karo", "thoda upar karo", "page up"
        ]):
            return ActionPlan(
                intent=PlanIntent.FOLLOWUP_ACTION,
                target_platform="system",
                target_entity="scroll_up",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="scroll_screen",
                        tool_call=ToolCall(name="scroll_screen", arguments={"direction": "up", "amount": 4}),
                        description="Scroll up active screen",
                    )
                ],
                immediate_response="Ji Boss, upar scroll kar diya.",
            )
        elif any(w in cmd_text.lower() for w in [
            "scroll down", "neeche scroll", "niche scroll", "scroll neeche", "scroll niche",
            "scroll karo", "scroll kar do", "scroll kardo", "scroll", "thoda scroll", "aur scroll",
            "neeche karo", "niche karo", "thoda neeche karo", "thoda niche karo", "page down"
        ]):
            return ActionPlan(
                intent=PlanIntent.FOLLOWUP_ACTION,
                target_platform="system",
                target_entity="scroll_down",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="scroll_screen",
                        tool_call=ToolCall(name="scroll_screen", arguments={"direction": "down", "amount": 4}),
                        description="Scroll down active screen",
                    )
                ],
                immediate_response="Ji Boss, neeche scroll kar diya.",
            )

        # 0.4 Universal Window Switching ("Chrome par switch karo", "VS Code par switch karo", "Notepad aage lao")
        switch_match = re.match(r"^(?:switch\s+to\s+|switch\s+karo\s+|switch\s+window\s+to\s+)?(chrome|vscode|vs\s+code|code|notepad|explorer|file\s+explorer|settings|calculator|spotify|terminal)\s+(?:par\s+switch\s+karo|switch\s+karo|aage\s+lao|focus\s+karo|par\s+jao)$", cmd_text, flags=re.IGNORECASE)
        if switch_match:
            app_target = switch_match.group(1).lower().strip()
            return ActionPlan(
                intent=PlanIntent.OPEN_APPLICATION,
                target_platform="system",
                target_entity=app_target,
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="switch_window",
                        tool_call=ToolCall(name="switch_window", arguments={"target_app": app_target}),
                        description=f"Switch foreground to {app_target}",
                    )
                ],
                immediate_response=f"Ji Boss, {app_target.title()} par switch kar diya.",
            )

        # 0.4.5 Universal Window Management ("minimize antigravity", "antigravity minimize karo", "maximize chrome", "close window")
        win_mgmt_match = re.search(r"^(?:please\s+|zara\s+)?(minimize|maximize|restore|close|band)\s+(?:karo|kar\s+do|do)?\s*(?:the\s+)?([a-zA-Z0-9\s]+?)?\s*(?:window|app|application)?$", cmd_text, flags=re.IGNORECASE)
        win_mgmt_match2 = re.search(r"^(?:the\s+|iss\s+)?([a-zA-Z0-9\s]+?)\s+(?:ko\s+)?(minimize|maximize|restore|close|band)\s*(?:karo|kar\s+do|do)?$", cmd_text, flags=re.IGNORECASE)

        act_word = None
        target_word = None

        if win_mgmt_match:
            act_word = win_mgmt_match.group(1).lower()
            target_word = (win_mgmt_match.group(2) or "").lower().strip()
        elif win_mgmt_match2:
            target_word = (win_mgmt_match2.group(1) or "").lower().strip()
            act_word = win_mgmt_match2.group(2).lower()

        if act_word and act_word in ["minimize", "maximize", "restore", "close", "band"]:
            std_act = "close" if act_word == "band" else act_word
            clean_tgt = re.sub(r"\b(window|app|application|this|active|screen|yeh|woh|karo|kar\s+do|do|ko|please|zara)\b", "", target_word or "", flags=re.IGNORECASE).strip()
            target_word = clean_tgt if clean_tgt else None
            return ActionPlan(
                intent=PlanIntent.FOLLOWUP_ACTION,
                target_platform="system",
                target_entity=f"{std_act}_{target_word or 'active_window'}",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="manage_window",
                        tool_call=ToolCall(
                            name="manage_window",
                            arguments={"action": std_act, "target_app": target_word}
                        ),
                        description=f"{std_act.title()} window {target_word or 'active'}",
                    )
                ],
                immediate_response=f"Ji Boss, {target_word.title() if target_word else 'window'} {std_act} kar di.",
            )

        # 0.34 Contact Saving ("Shivam 9501445740", "save Shivam number 9501445740", "Shivam ka number 9501445740 save karo")
        contact_num_match = re.search(r"(\+?\d[\d\s\-]{8,14}\d)", cmd_text)
        if contact_num_match and not any(w in cmd_text.lower() for w in ["ep", "episode", "bhag", "part"]):
            c_phone = contact_num_match.group(1).strip().replace(" ", "").replace("-", "")
            # Extract contact name by removing phone, save, number keywords
            name_part = cmd_text.replace(contact_num_match.group(0), " ")
            name_part = re.sub(r"\b(save|add|contact|number|no|ka|ki|ke|as|hai|is|karo|kar|do|rakho|phone|wala|wali|का|की|के|नंबर)\b", " ", name_part, flags=re.IGNORECASE)
            name_part = re.sub(r"\s+", " ", name_part).strip()
            if name_part and len(c_phone) >= 10 and not any(w in cmd_text.lower() for w in ["call", "message", "msg", "bhejo"]):
                return ActionPlan(
                    intent=PlanIntent.WHATSAPP_MESSAGE,
                    target_platform="contacts",
                    target_entity=name_part,
                    steps=[
                        PlannedStep(
                            step_id=1,
                            action_type="save_contact",
                            tool_call=ToolCall(
                                name="save_contact",
                                arguments={"name": name_part.title(), "phone": c_phone}
                            ),
                            description=f"Save contact '{name_part.title()}' with phone '{c_phone}'",
                            requires_verification=True,
                        )
                    ],
                    immediate_response=f"Ji Boss, {name_part.title()} ka number {c_phone} save kar diya hai.",
                )

        # 0.36 WhatsApp Messaging & Calling
        # 1. WhatsApp Call (Voice / Video)
        wa_call_match = re.match(
            r"^(?:whatsapp\s+(?:par|pe)\s+|whatsapp\s+)?(.+?)\s*(?:ko)?\s*(?:whatsapp\s+)?(?:pe\s+|par\s+)?(voice\s+call|video\s+call|call)\s*(?:karo|lagao|milao|kar\s+do)?$",
            cmd_text,
            flags=re.IGNORECASE
        )
        if wa_call_match and "call" in cmd_text.lower():
            target_name = wa_call_match.group(1).strip()
            call_kind = wa_call_match.group(2).lower()
            # Clean filler words (both Latin and Devanagari)
            target_name = re.sub(r"\b(whatsapp|on|in|pe|par|ko|call|voice|video|karo|lagao|milao)\b", "", target_name, flags=re.IGNORECASE).strip()
            target_name = re.sub(r"(\s+को|को|\s+ko|ko)$", "", target_name, flags=re.IGNORECASE).strip()
            if target_name:
                is_video = "video" in call_kind or "video" in cmd_text.lower()
                return ActionPlan(
                    intent=PlanIntent.WHATSAPP_MESSAGE,
                    target_platform="whatsapp",
                    target_entity=target_name,
                    steps=[
                        PlannedStep(
                            step_id=1,
                            action_type="whatsapp_call",
                            tool_call=ToolCall(
                                name="call_whatsapp_contact",
                                arguments={"contact_or_phone": target_name, "call_type": "video" if is_video else "voice"}
                            ),
                            description=f"Initiate WhatsApp {'video' if is_video else 'voice'} call to {target_name}",
                            requires_verification=True,
                        )
                    ],
                    immediate_response=f"Ji Boss, {target_name.title()} ko WhatsApp call laga rahi hu.",
                )

        # 2. WhatsApp Message
        wa_msg_match = re.match(
            r"^(?:whatsapp\s+(?:par|pe)\s+|send\s+)?(.+?)\s*(?:ko)?\s*(?:whatsapp\s+)?(?:pe\s+|par\s+)?(?:message|msg)\s*(?:bhejo|karo|send\s+karo|send)?(?:\s*[:\-–]\s*|\s+(?:ki|that|text|saying|message|msg)\s+|\s+)?(.*)$",
            cmd_text,
            flags=re.IGNORECASE
        )
        if wa_msg_match and any(w in cmd_text.lower() for w in ["message", "msg"]):
            target_name = wa_msg_match.group(1).strip()
            msg_text = (wa_msg_match.group(2) or "Hello").strip()
            target_name = re.sub(r"\b(whatsapp|on|in|pe|par|ko|message|msg|send|karo|bhejo)\b", "", target_name, flags=re.IGNORECASE).strip()
            target_name = re.sub(r"(\s+को|को|\s+ko|ko)$", "", target_name, flags=re.IGNORECASE).strip()
            if target_name:
                return ActionPlan(
                    intent=PlanIntent.WHATSAPP_MESSAGE,
                    target_platform="whatsapp",
                    target_entity=target_name,
                    steps=[
                        PlannedStep(
                            step_id=1,
                            action_type="whatsapp_message",
                            tool_call=ToolCall(
                                name="send_whatsapp_message",
                                arguments={"contact_or_phone": target_name, "message": msg_text if msg_text else "Hello", "auto_send": False}
                            ),
                            description=f"Send WhatsApp message to {target_name}",
                            requires_verification=True,
                        )
                    ],
                    immediate_response=f"Ji Boss, {target_name.title()} ko WhatsApp message bhej rahi hu.",
                )

        # 0.37 Universal PC Problem Solver & Diagnostics ("check my laptop", "bluetooth nahi chal raha", "wifi problem", "no sound", "laptop slow")
        c_diag = cmd_text.lower().strip()
        is_health_check = any(w in c_diag for w in [
            "check my laptop", "check laptop", "diagnose my laptop", "diagnose laptop",
            "laptop health", "system health", "laptop check karo", "pc check karo",
            "find what's wrong", "what's wrong with my laptop", "kya problem hai",
            "check system", "laptop check", "pc diagnose"
        ])
        if is_health_check:
            return ActionPlan(
                intent=PlanIntent.DIAGNOSTICS,
                target_platform="system",
                target_entity="system_health",
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="system_health_scan",
                        tool_call=ToolCall(name="get_comprehensive_system_health", arguments={}),
                        description="Run universal hardware, OS, and software diagnostic health scan",
                        requires_verification=False,
                    )
                ],
                immediate_response="Ji Boss, main aapke laptop ka complete health scan kar rahi hu.",
            )

        problem_keywords = [
            "nahi chal raha", "kaam nahi kar raha", "not working", "problem", "issue", "error",
            "slow", "hang", "freeze", "no sound", "awaaz nahi", "disconnected", "stuck", "troubleshoot",
            "fix", "repair", "kharab", "band hai", "nahi khul raha", "crash", "why is", "storage full",
            "disk full", "space full", "full hai", "storage", "disk", "chalu nahi", "connect nahi"
        ]
        is_hardware_problem = (
            any(w in c_diag for w in ["bluetooth", "wifi", "internet", "sound", "audio", "mic", "display", "usb", "keyboard", "touchpad"])
            and any(n in c_diag for n in ["nahi", "not", "problem", "issue", "error", "kharab", "band", "fail", "slow", "hang", "chalu nahi"])
        )
        if (any(w in c_diag for w in problem_keywords) or is_hardware_problem) and not any(w in c_diag for w in ["whatsapp", "youtube", "video", "song", "gaana", "call"]):
            return ActionPlan(
                intent=PlanIntent.DIAGNOSTICS,
                target_platform="system",
                target_entity=cmd_text,
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="diagnose_problem",
                        tool_call=ToolCall(name="diagnose_system_problem", arguments={"problem_description": cmd_text, "auto_repair": True}),
                        description=f"Diagnose and safely solve problem '{cmd_text}'",
                        requires_verification=True,
                    )
                ],
                immediate_response="Ji Boss, main issue ko deeply diagnose karke repair kar rahi hu.",
            )

        # 0.34 Window Management Controls ("minimize antigravity", "antigravity minimize karo", "antigravity ko taskbar mein minimize karo", "maximize chrome", "close window")
        win_min_match = re.search(r"\b(minimize|chhota\s+karo|taskbar\s+mein\s+minimize)\b", cmd_text, flags=re.IGNORECASE)
        win_max_match = re.search(r"\b(maximize|bada\s+karo|fullscreen)\b", cmd_text, flags=re.IGNORECASE)
        win_restore_match = re.search(r"\b(restore|wapas\s+lao)\b", cmd_text, flags=re.IGNORECASE)

        if win_min_match:
            target_raw = re.sub(r"\b(taskbar|mein|me|ko|window|app|application|screen|minimize|chhota\s+karo|karo|kar\s+do|do|yeh|ye|woh|is|isse)\b", "", cmd_text, flags=re.IGNORECASE).strip() or "window"
            return ActionPlan(
                intent=PlanIntent.FOLLOWUP_ACTION,
                target_platform="system",
                target_entity=target_raw,
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="manage_window",
                        tool_call=ToolCall(name="manage_window", arguments={"action": "minimize", "target_app": target_raw}),
                        description=f"Minimize window for '{target_raw}'",
                        requires_verification=False,
                    )
                ],
                immediate_response=f"Ji Boss, {target_raw.title()} window minimize kar rahi hu.",
            )

        if win_max_match:
            target_raw = re.sub(r"\b(taskbar|mein|me|ko|window|app|application|screen|maximize|bada\s+karo|fullscreen|karo|kar\s+do|do|yeh|ye|woh|is|isse)\b", "", cmd_text, flags=re.IGNORECASE).strip() or "window"
            return ActionPlan(
                intent=PlanIntent.FOLLOWUP_ACTION,
                target_platform="system",
                target_entity=target_raw,
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="manage_window",
                        tool_call=ToolCall(name="manage_window", arguments={"action": "maximize", "target_app": target_raw}),
                        description=f"Maximize window for '{target_raw}'",
                        requires_verification=False,
                    )
                ],
                immediate_response=f"Ji Boss, {target_raw.title()} window maximize kar rahi hu.",
            )

        # 0.35 Ultra-Fast Universal Application Launching ("open chrome", "notepad kholo", "calculator on karo", "open whatsapp", "start spotify", "open anti gravity", "file explorer")
        has_launch_verb = bool(re.search(r"\b(open|kholo|khol|launch|start|run|app|application|chalao)\b", cmd_text, flags=re.IGNORECASE))
        from backend.tools.app_tools import app_registry
        c_low = cmd_text.lower().strip()
        if not (any(w in c_diag for w in problem_keywords) or is_hardware_problem or win_min_match or win_max_match or win_restore_match):
            if has_launch_verb or app_registry.resolve_app(c_low) is not None or "explorer" in c_low:
                app_raw = re.sub(r"\b(open|kholo|khol|launch|start|run|app|application|chalao|on\s+karo|karo|kar\s+do|kardo|do)\b", "", cmd_text, flags=re.IGNORECASE).strip()
                # Normalize phonetic spaces
                app_raw = re.sub(r"\banti\s+gravity\b", "antigravity", app_raw, flags=re.IGNORECASE).strip()
                app_raw = re.sub(r"\banti-gravity\b", "antigravity", app_raw, flags=re.IGNORECASE).strip()
                app_raw = re.sub(r"\bvs\s+code\b", "vscode", app_raw, flags=re.IGNORECASE).strip()

                if app_raw and app_raw not in ["youtube", "video", "song", "gaana", "vlog", "latest", "reel", "shorts", "karo", "kar", "do"]:
                    app_entry = app_registry.resolve_app(app_raw) or app_registry.resolve_app(c_low)
                    if app_entry:
                        target_name = app_entry["name"]
                        return ActionPlan(
                            intent=PlanIntent.OPEN_APPLICATION,
                            target_platform="system",
                            target_entity=target_name.lower(),
                            steps=[
                                PlannedStep(
                                    step_id=1,
                                    action_type="launch_app",
                                    tool_call=ToolCall(name="open_application", arguments={"app_name": target_name.lower()}),
                                    description=f"Launch Windows application '{target_name}'",
                                    requires_verification=True,
                                    verification_target=target_name.lower(),
                                )
                            ],
                            immediate_response=f"Ji Boss, {target_name} open kar diya.",
                        )

        # 0.5 Spatial UI Element Clicking ("isme jo upar wala hai", "neeche wala click karo", "left side wala")
        spatial_click_match = re.match(
            r"^(?:isme\s+jo\s+|ab\s+)?(upar\s+wala|neeche\s+wala|niche\s+wala|left\s+side\s+wala|right\s+side\s+wala|beech\s+wala|middle\s+wala)(?:\s+hai)?\s*(?:uspe|uspar|par|pe)?\s*(?:click\s+karo|chalao|lagao|kholo|open\s+karo|select\s+karo)?$",
            cmd_text,
            flags=re.IGNORECASE
        )
        if spatial_click_match:
            target_phrase = spatial_click_match.group(1).lower().strip()
            return ActionPlan(
                intent=PlanIntent.FOLLOWUP_ACTION,
                target_platform="system",
                target_entity=target_phrase,
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="click_element",
                        tool_call=ToolCall(name="click_element", arguments={"target": target_phrase}),
                        description=f"Click UI element '{target_phrase}'",
                    )
                ],
                immediate_response=f"Ji Boss, {target_phrase} par click kar diya.",
            )

        # 0.6 Ambiguous Channel Clarification Trigger
        if any(cmd_text == w or cmd_text.startswith(w) or w in cmd_text for w in [
            "click on that random channel", "click on that channel", "that random channel", "random channel kholo", "koi channel kholo", "channel par click karo", "channel kholo"
        ]):
            return ActionPlan(
                intent=PlanIntent.DIRECT_CHAT,
                is_direct_chat=True,
                direct_chat_response="कौन सा channel? ऊपर वाला या नीचे वाला?",
            )

        # 1. Screen Video Click / Ordinal Commands (e.g. "ye jo 3rd number pe reaction video hai isse lagana", "3rd number pe jo video hai", "teesre number wali video chalao", "ye jo 2nd video hai isse lagana", "upar wali video", "niche wali video", "second number wala short")
        ord_keywords = r"(1st|2nd|3rd|4th|5th|6th|1|2|3|4|5|6|pehli|pehla|first|dusri|dusra|second|secomd|teesri|teesra|teesre|third|chauthi|chautha|fourth|panchwi|panchwa|fifth|upar|top|niche|neeche|bottom)"
        ordinal_search = re.search(r"\b" + ord_keywords + r"(?:\s*(?:number|no|va|vi|ve|st|nd|rd|th|wali|wala))?\b", cmd_text, flags=re.IGNORECASE)
        # Check if user intends to click/play an ordinal video or UI card
        # IMPORTANT: exclude 'open'/'kholo'/'launch' commands — those go to OPEN_APPLICATION
        ordinal_trigger_words = ["video", "clip", "short", "reel", "vlog", "reaction", "song", "wala", "wali", "lagao", "lagana", "chalao", "play", "click", "par", "pe", "jo", "isse", "usse", "screen", "number", "live", "liv", "shot", "shots"]
        ordinal_block_words = ["open", "kholo", "launch", "start", "chalo", "app", "application"]
        if ordinal_search and any(w in cmd_text.lower() for w in ordinal_trigger_words) and not any(w in cmd_text.lower() for w in ordinal_block_words):
            is_short = any(w in cmd_text.lower() for w in ["short", "shorts", "reel", "reels", "clip", "shot", "shots"])


            matched_ord = ordinal_search.group(1).lower()
            ord_map = {
                "1": 1, "1st": 1, "pehli": 1, "pehla": 1, "first": 1, "upar": 1, "top": 1,
                "2": 2, "2nd": 2, "dusri": 2, "dusra": 2, "second": 2, "secomd": 2, "niche": 2, "neeche": 2, "bottom": 2,
                "3": 3, "3rd": 3, "teesri": 3, "teesra": 3, "teesre": 3, "third": 3,
                "4": 4, "4th": 4, "chauthi": 4, "chautha": 4, "fourth": 4,
                "5": 5, "5th": 5, "panchwi": 5, "panchwa": 5, "fifth": 5,
                "6": 6, "6th": 6, "sixth": 6,
            }
            target_idx = ord_map.get(matched_ord, 1)
            steps = []
            if "youtube open" in cmd_text.lower() or "youtube khol" in cmd_text.lower():
                steps.append(PlannedStep(
                    step_id=1,
                    action_type="open_youtube",
                    tool_call=ToolCall(name="play_youtube_video", arguments={"query": ""}),
                    description="Open YouTube homepage",
                ))
            steps.append(PlannedStep(
                step_id=len(steps) + 1,
                action_type="click_screen_video",
                tool_call=ToolCall(name="click_screen_video", arguments={"index": target_idx, "is_short": is_short}),
                description=f"Click {'short' if is_short else 'video'} #{target_idx} on screen",
            ))
            return ActionPlan(
                intent=PlanIntent.FOLLOWUP_ACTION,
                target_platform="youtube",
                target_entity=f"{'Short' if is_short else 'Video'} #{target_idx}",
                steps=steps,
                immediate_response="Ji Boss, chala diya.",
            )

        # 2. Contextual Follow-ups ("dusra wala", "isme se expensive gift wala", "ye wala chalao")
        followup_candidate = context_memory.resolve_followup(cmd_text)
        if followup_candidate:
            return ActionPlan(
                intent=PlanIntent.FOLLOWUP_ACTION,
                target_platform="youtube",
                target_entity=followup_candidate.title,
                steps=[
                    PlannedStep(
                        step_id=1,
                        action_type="play_video",
                        tool_call=ToolCall(
                            name="play_youtube_video",
                            arguments={"query": followup_candidate.title}
                        ),
                        description=f"Play candidate video '{followup_candidate.title}'",
                        requires_verification=True,
                        verification_target=followup_candidate.id,
                    )
                ],
                immediate_response="Ji Boss, chala diya.",
            )

        # 2. Multi-step / YouTube Video Intent
        # e.g., "tarak mehta ep 312", "tarak mehta episode 3114", "chalana Jass Manak wali real hai na vah chala do", "YouTube par expensive gift for Laila wala video chalao"
        yt_patterns = [
            r"^(.+?)\s+(?:ep|episode|episodes|bhag|bhaag)\s*(\d+)(?:\s+(?:chalao|lagao|play|kholo|hai|chala\s+do))?$",
            r"^(?:youtube\s+(?:kholo\s*,\s*|open\s+karo\s*,\s*|par\s+|mein\s+|pe\s+))?(.+?)\s+(?:video|song|gaana|standup|comedy|podcast|reel|short|shorts|vlog)?\s*(?:hai\s+na\s+vah\s+chala\s+do|vah\s+chala\s+do|woh\s+chala\s+do|chala\s+do\s+na|lagao\s+na|chala\s+do|kar\s+do|chalao|chalana|lagao|lagana|laga\s+de|laga\s+dena|play\s+karo|bajao|bajana|baja\s+do|dikhao|dikhana|dikha\s+do|sunao|sunana|suna\s+do|kholo|khol\s+do|search\s+karo|play|dekhna\s+hai|sunna\s+hai)(?:\s+(?:youtube\s+(?:mein|pe|par)|in\s+youtube|on\s+youtube|in\s+chrome))?$",
            r"^(.+?)\s+(?:wali\s+reel|wala\s+short|wali\s+video|wala\s+gaana|wala\s+song|reel|short|shorts|video|gaana|song|vlog)\s+(?:chalana|chalao|lagao|lagana|chala\s+do|play|sunao|dikhao)(?:\s+(?:short|shorts|reel))?.*$",
            r"^(.+?)\s+(?:chalana|chalao|lagao|lagana|play|sunao|sunana|dikhao|dikhana)\s+(?:short|shorts|reel|video|gaana|song|vlog).*$",
            r"^(.+?)\s+(?:wali\s+reel|wala\s+short|wali\s+video|wala\s+gaana|wala\s+song)(?:\s+.*)?$",
            r"^(?:youtube\s+(?:mein|pe|par)\s+)?(.+?)\s+(?:pe|par)\s+click\s+karo$",
            r"^click\s+(?:on\s+)?(.+?)(?:\s+(?:on|in)\s+youtube)?$",
            r"^(?:play|search)\s+(.+?)(?:\s+(?:on|in)\s+youtube|\s+in\s+chrome)?$",
            r"^play\s+(.+)$",
        ]

        yt_block_words = ["delete", "remove", "database", "permission", "clear memory", "forget", "emergency", "stop all"]
        if any(w in cmd_text.lower() for w in yt_block_words):
            return None

        for pattern in yt_patterns:
            m = re.match(pattern, cmd_text)
            if m:
                query_candidate = m.group(1).strip()
                # Clean spatial prefixes
                query_candidate = re.sub(r"\b(right\s+side\s+mein|left\s+side\s+mein|side\s+mein|sidebar\s+mein|screen\s+par|screen\s+pe)\b", "", query_candidate, flags=re.IGNORECASE).strip()
                clean_q = re.sub(
                    r"\b(shivam\s+ai|shivam|jarvis|video|song|gaana|standup|comedy|podcast|vlog|youtube|chrome|on|in|mein|pe|par|search|play|karo|kar\s+do|lagao|lagana|laga\s+do|laga\s+de|laga\s+dena|laga\s+dijiye|laga\s+k\s+de|laga\s+ke\s+do|lagana\s+hai|chalao|chalana|chala\s+do|chala\s+de|chala\s+dena|chala\s+dijiye|chala\s+ke\s+do|chalana\s+hai|bajao|bajana|baja\s+do|dikhao|dikhana|dikha\s+do|sunao|sunana|suna\s+do|kholo|kholna|khol\s+do|open|wala|wali|wale|ka|ki|ke|ye|woh|yeh|vah|hai\s+na|dekhna\s+hai|sunna\s+hai|dikhayo|click|click\s+karo|bhai|yaar|yrr|bro|boss|jaldi|fatfat|zara|thoda|bawaal|mast|tagda|dhamaal|op|faadu)\b",
                    "",
                    query_candidate,
                    flags=re.IGNORECASE
                )
                clean_q = re.sub(r"[,;:\-–—]+", " ", clean_q)
                clean_q = re.sub(r"\s+", " ", clean_q).strip()

                # If episode number was matched in group 2, append it cleanly
                if len(m.groups()) >= 2 and m.group(2):
                    ep_num = m.group(2).strip()
                    clean_q = f"{clean_q} episode {ep_num}".strip()

                if clean_q.lower() in ["youtube", "chrome", "play", "open", "karo", ""]:
                    # Generic YouTube home open
                    return ActionPlan(
                        intent=PlanIntent.PLAY_VIDEO,
                        target_platform="youtube",
                        target_entity="",
                        steps=[
                            PlannedStep(
                                step_id=1,
                                action_type="open_youtube",
                                tool_call=ToolCall(name="play_youtube_video", arguments={"query": ""}),
                                description="Open YouTube home",
                                requires_verification=True,
                            )
                        ],
                        immediate_response="Ji Boss, YouTube open kar diya.",
                    )
                else:
                    # Specific video search & play
                    is_short_intent = any(w in cmd_text.lower() or w in user_text.lower() for w in ["short", "shorts", "reel", "reels", "clip", "shot", "shots"])
                    target_query = f"{clean_q} short" if (is_short_intent and not clean_q.lower().endswith("short")) else clean_q
                    return ActionPlan(
                        intent=PlanIntent.PLAY_VIDEO,
                        target_platform="youtube",
                        target_entity=target_query,
                        steps=[
                            PlannedStep(
                                step_id=1,
                                action_type="play_video",
                                tool_call=ToolCall(
                                    name="play_youtube_video",
                                    arguments={"query": target_query}
                                ),
                                description=f"Search, rank, and play video for '{target_query}'",
                                requires_verification=True,
                                verification_target=target_query,
                            )
                        ],
                        immediate_response="Ji Boss, chala diya.",
                    )

        # 3. Targeted Content & Creator Fallback (Safe & Noise-Proof)
        # Only triggers if the command contains explicit media playback keywords or a known creator/channel
        media_intent_keywords = [
            "play", "video", "song", "gaana", "vlog", "music", "chalao", "chalana", "lagao", "lagana",
            "bajao", "bajana", "sunao", "sunana", "dikhao", "dikhana",
            "short", "shorts", "reel", "reels", "podcast", "youtube"
        ]
        known_creators = [
            "indian backpacker", "aarush bhola", "elvish yadav", "samay raina", "munawar faruqui",
            "salman khan", "sushant mehta", "late night yaari", "sports yaari", "carryminati",
            "techno gamerz", "total gaming", "taarak mehta", "sourav joshi", "fukra insaan",
            "triggered insaan", "round2hell", "bb ki vines", "ashish chanchlani", "ishowspeed",
            "death nut", "karan aujla", "sidhu moose wala", "honey singh", "badshah",
            "arijit singh", "diljit dosanjh", "shubh"
        ]

        has_media_intent = any(re.search(r"\b" + re.escape(w) + r"\b", cmd_text.lower()) for w in media_intent_keywords)
        has_known_creator = any(c in cmd_text.lower() for c in known_creators)

        if (has_media_intent or has_known_creator) and len(cmd_text.strip()) > 2:
            clean_q = re.sub(
                r"\b(shivam\s+ai|shivam|jarvis|video|song|gaana|standup|comedy|podcast|youtube|chrome|on|in|mein|pe|par|search|play|karo|kar\s+do|lagao|lagana|laga\s+do|laga\s+de|laga\s+dena|laga\s+dijiye|laga\s+k\s+de|laga\s+ke\s+do|lagana\s+hai|chalao|chalana|chala\s+do|chala\s+de|chala\s+dena|chala\s+dijiye|chala\s+ke\s+do|chalana\s+hai|bajao|bajana|baja\s+do|dikhao|dikhana|dikha\s+do|sunao|sunana|suna\s+do|kholo|kholna|khol\s+do|open|wala|wali|wale|ka|ki|ke|ye|woh|wo|yeh|vah|hai\s+woh|hai\s+wo|hai\s+vah|hai\s+na|hai|dekhna\s+hai|sunna\s+hai|dikhayo|click|click\s+karo|bhai|yaar|yrr|bro|boss|jaldi|fatfat|zara|thoda|bawaal|mast|tagda|dhamaal|op|faadu|niche|neeche|upar|dikh\s+rahi\s+hai|dikh\s+raha\s+hai|gobhi|jo|isse|usse|was\s+written|is\s+written|written|likha|padh\s+ke|pad\s+ke|text)\b",
                "",
                cmd_text,
                flags=re.IGNORECASE
            )
            clean_q = re.sub(r"[,;:\-–—]+", " ", clean_q)
            clean_q = re.sub(r"\s+", " ", clean_q).strip()

            is_short_intent = any(w in cmd_text.lower() or w in user_text.lower() for w in ["short", "shorts", "reel", "reels", "clip", "shot", "shots"])
            target_to_play = clean_q if clean_q else cmd_text.strip()
            if is_short_intent and not target_to_play.lower().endswith("short"):
                target_to_play = f"{target_to_play} short"
            if target_to_play:
                return ActionPlan(
                    intent=PlanIntent.PLAY_VIDEO,
                    target_platform="youtube",
                    target_entity=target_to_play,
                    steps=[
                        PlannedStep(
                            step_id=1,
                            action_type="play_video",
                            tool_call=ToolCall(
                                name="play_youtube_video",
                                arguments={"query": target_to_play}
                            ),
                            description=f"Search, rank, and play '{target_to_play}' on YouTube",
                            requires_verification=True,
                            verification_target=target_to_play,
                        )
                    ],
                    immediate_response="Ji Boss, chala diya.",
                )

        return None


# Global singleton
action_planner = ActionPlanner()
