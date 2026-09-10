from __future__ import annotations

import json
import re
from typing import Any

from jarvis.ai.providers import AIProviderRouter
from jarvis.core.models import Intent
from jarvis.youtube.catalog import ACTIONS


SYSTEM_PROMPT = """You are the semantic planner inside a Windows JARVIS assistant.
Production profile: YOUTUBE ONLY.
Return exactly one JSON object and no prose.
Allowed application: youtube.
Allowed actions and argument shapes:
%s
Rules:
- Never invent mouse coordinates, keyboard scripts, selectors, URLs, shell commands, or Python function names.
- Use one-based ordinals: first=1, second=2, third=3.
- If the user asks a non-YouTube app, return {\"unsupported_app\": true, \"application\": \"name\"}.
- For YouTube return {\"application\":\"youtube\",\"action\":\"...\",\"arguments\":{},\"confidence\":0.0-1.0}.
- Keep user search text intact.
""" % json.dumps(ACTIONS, ensure_ascii=False)


class SemanticPlanner:
    def __init__(self, router: AIProviderRouter):
        self.router = router

    def plan(self, text: str) -> Intent | None:
        reply = self.router.generate(SYSTEM_PROMPT, text)
        if not reply.success:
            return None
        obj = self._extract_json(reply.text)
        if not isinstance(obj, dict) or obj.get("unsupported_app"):
            return None
        if obj.get("application") != "youtube":
            return None
        action = obj.get("action")
        if action not in ACTIONS:
            return None
        args = obj.get("arguments") or {}
        if not isinstance(args, dict):
            return None
        if not self._validate(action, args):
            return None
        return Intent("youtube", action, args, float(obj.get("confidence", 0.7)), source=reply.provider)

    @staticmethod
    def _extract_json(text: str) -> Any:
        text = text.strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S)
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r"\{.*\}", text, flags=re.S)
            if not m:
                return None
            try:
                return json.loads(m.group(0))
            except Exception:
                return None

    @staticmethod
    def _validate(action: str, args: dict[str, Any]) -> bool:
        if action in {"play_short", "play_video"} and "ordinal" in args:
            try:
                if int(args["ordinal"]) < 1:
                    return False
                args["ordinal"] = int(args["ordinal"])
            except Exception:
                return False
        if action == "set_volume" and "level" in args:
            try:
                args["level"] = max(0, min(100, int(args["level"])))
            except Exception:
                return False
        if action in {"set_fullscreen", "set_theater_mode", "set_miniplayer", "set_captions", "set_like"} and "enabled" in args:
            if not isinstance(args["enabled"], bool):
                return False
        return True
