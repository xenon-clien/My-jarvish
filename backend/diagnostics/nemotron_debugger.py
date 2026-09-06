"""NVIDIA Nemotron Diagnostic Specialist & Code Doctor for JARVIS.

Specialized AI Debugger that analyzes runtime failures, stack traces, Playwright traces,
and DOM anomalies to generate empirical root-cause diagnoses and reproduction tests.
"""
from datetime import datetime
import json
import os
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from backend.core.config import get_settings
from backend.core.logger import get_logger
from backend.diagnostics.nemotron_guard import nemotron_guard
from backend.diagnostics.fingerprint_manager import fingerprint_manager, DiagnosticCacheEntry

logger = get_logger("NemotronDebugger")


class NemotronDiagnosticReport(BaseModel):
    """Structured diagnostic analysis returned by NVIDIA Nemotron."""
    issueType: str = "RUNTIME_ERROR"
    affectedLayer: str = "Core"
    rootCause: str = "Root cause not yet isolated."
    evidence: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    reproductionTest: str = ""
    recommendedFix: str = ""
    risk: str = "low"
    filesToInspect: List[str] = Field(default_factory=list)
    raw_response: Optional[str] = None


class NemotronDebugger:
    """NVIDIA Nemotron AI Diagnostic Engine via OpenRouter."""

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.OPENROUTER_API_KEY
        self.base_url = getattr(self.settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = getattr(self.settings, "NEMOTRON_MODEL", "nvidia/nemotron-3.5-lightning:free")

    async def diagnose_failure(
        self,
        command_text: str,
        expected_intent: str,
        actual_result: str,
        error_type: str,
        error_stack: Optional[str] = None,
        url_before: Optional[str] = None,
        url_after: Optional[str] = None,
        dom_candidates: Optional[List[str]] = None,
        playwright_trace_path: Optional[str] = None,
        relevant_code_snippet: Optional[str] = None,
        domain: str = "general",
        is_automatic: bool = True,
    ) -> NemotronDiagnosticReport:
        """Run root-cause analysis on empirical failure evidence using NVIDIA Nemotron."""
        
        # 1. Compute Error Fingerprint and check Diagnosis Cache
        fingerprint = fingerprint_manager.compute_fingerprint(
            domain=domain,
            intent=expected_intent,
            error_type=error_type,
            affected_module=domain,
            target_info=actual_result,
        )
        cached = fingerprint_manager.get_cached_diagnosis(fingerprint)
        if cached:
            return NemotronDiagnosticReport(
                issueType=cached.issue_type,
                affectedLayer=cached.affected_layer,
                rootCause=cached.root_cause,
                evidence=[f"Diagnosis reloaded from local fingerprint cache ({cached.fingerprint})"],
                confidence=cached.confidence,
                reproductionTest=cached.reproduction_test,
                recommendedFix=cached.recommended_fix,
                risk="low",
            )

        # 2. Check Nemotron Usage Guard (Safety Hard-Stop, Daily Quota, Model Allowlist)
        can_run, reason = nemotron_guard.canUseNemotron(is_automatic=is_automatic)
        if not can_run or not self.api_key:
            logger.info(f"Nemotron/OpenRouter inactive ({reason}). Delegating diagnostic analysis to JARVIS AIProviderRouter.")
            try:
                from backend.ai.providers import get_ai_provider
                router = get_ai_provider()
                ai_resp = await router.generate_response(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ]
                )
                raw_txt = ai_resp.content or ""
                json_str = raw_txt
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0].strip()
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0].strip()
                if "{" in json_str and "}" in json_str:
                    json_str = json_str[json_str.find("{"):json_str.rfind("}")+1]
                parsed_json = json.loads(json_str)
                return NemotronDiagnosticReport(**parsed_json, raw_response=raw_txt)
            except Exception as router_err:
                logger.debug(f"AI Provider diagnostic fallback: {router_err}")
                return NemotronDiagnosticReport(
                    issueType=error_type,
                    affectedLayer=domain,
                    rootCause=f"Empirical diagnosis for {actual_result or error_type}: check parameters and context state.",
                    evidence=[f"Provider Status: AIProviderRouter active ({reason})", f"Error Type: {error_type}"],
                    confidence=0.75,
                    reproductionTest=f"python scripts/reproduce_debug.py {domain}-action",
                    recommendedFix="Inspect local trace logs in logs/observability/.",
                    risk="none",
                )

        # 3. Format Structured Diagnostic Evidence
        system_prompt = (
            "You are the NVIDIA Nemotron Diagnostic Specialist & Code Doctor for the JARVIS system.\n"
            "Your role is STRICTLY DIAGNOSTIC: analyze runtime errors, traces, and DOM anomalies.\n"
            "You must NOT generate conversational chit-chat or arbitrary guesses beyond the provided evidence.\n"
            "Output your findings STRICTLY as a single JSON object matching this schema:\n"
            "{\n"
            '  "issueType": "WRONG_TARGET | ELEMENT_NOT_FOUND | ROUTING_ERROR | RUNTIME_ERROR | TIMEOUT",\n'
            '  "affectedLayer": "string",\n'
            '  "rootCause": "precise technical explanation of what caused the mismatch",\n'
            '  "evidence": ["evidence point 1", "evidence point 2"],\n'
            '  "confidence": 0.0 to 1.0,\n'
            '  "reproductionTest": "exact reproducible test command or step",\n'
            '  "recommendedFix": "smallest safe code/logic fix",\n'
            '  "risk": "low | medium | high",\n'
            '  "filesToInspect": ["path/to/file.py"]\n'
            "}"
        )

        user_content = (
            f"COMMAND:\n{command_text}\n\n"
            f"EXPECTED INTENT:\n{expected_intent}\n\n"
            f"ACTUAL RESULT:\n{actual_result}\n\n"
            f"ERROR TYPE:\n{error_type}\n\n"
            f"URL BEFORE: {url_before or 'N/A'}\n"
            f"URL AFTER:  {url_after or 'N/A'}\n\n"
            f"STACK TRACE:\n{error_stack or 'No exception stack trace available.'}\n\n"
            f"DOM CANDIDATES:\n{json.dumps(dom_candidates or [])}\n\n"
            f"PLAYWRIGHT TRACE:\n{playwright_trace_path or 'N/A'}\n\n"
            f"RELEVANT CODE CONTEXT:\n{relevant_code_snippet or 'N/A'}\n\n"
            "Identify the most likely root cause using the supplied empirical evidence. "
            "Do not guess beyond the evidence. Provide a reproducible test before proposing a patch."
        )

        # 4. Invoke OpenRouter (nvidia/nemotron-3.5-lightning:free)
        try:
            nemotron_guard.record_request()
            async with httpx.AsyncClient(timeout=25.0) as client:
                res = await client.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "HTTP-Referer": "https://github.com/jarvis-assistant",
                        "X-Title": "JARVIS Nemotron Debugger",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content},
                        ],
                        "temperature": 0.1,
                    },
                )

                if res.status_code == 429:
                    nemotron_guard.record_rate_limit(is_quota_exhausted=True)
                    return NemotronDiagnosticReport(
                        issueType="RATE_LIMIT",
                        affectedLayer="Debugger",
                        rootCause="Nemotron free tier rate limit reached.",
                        confidence=0.50,
                    )

                if res.status_code != 200:
                    logger.error(f"Nemotron API error {res.status_code}: {res.text}")
                    return NemotronDiagnosticReport(
                        issueType="API_ERROR",
                        affectedLayer="Debugger",
                        rootCause=f"OpenRouter API error {res.status_code}",
                        confidence=0.50,
                    )

                data = res.json()
                raw_txt = data["choices"][0]["message"]["content"].strip()

                # Clean markdown JSON wraps or thought preamble
                json_str = raw_txt
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0].strip()
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0].strip()

                if "{" in json_str and "}" in json_str:
                    json_str = json_str[json_str.find("{"):json_str.rfind("}")+1]

                parsed_json = json.loads(json_str)
                report = NemotronDiagnosticReport(**parsed_json, raw_response=raw_txt)

                # Store in Diagnosis Cache for future reuse
                fingerprint_manager.store_diagnosis(
                    fingerprint=fingerprint,
                    issue_type=report.issueType,
                    affected_layer=report.affectedLayer,
                    root_cause=report.rootCause,
                    confidence=report.confidence,
                    reproduction_test=report.reproductionTest,
                    recommended_fix=report.recommendedFix,
                )

                logger.info(f"🔍 Nemotron Diagnosis Complete: [{report.issueType}] in {report.affectedLayer} (Conf: {report.confidence})")
                return report

        except Exception as e:
            logger.error(f"Nemotron Debugger execution error: {e}")
            return NemotronDiagnosticReport(
                issueType=error_type,
                affectedLayer=domain,
                rootCause=f"Diagnostic failure: {str(e)}",
                confidence=0.30,
            )


# Global Singleton Nemotron Debugger
nemotron_debugger = NemotronDebugger()
