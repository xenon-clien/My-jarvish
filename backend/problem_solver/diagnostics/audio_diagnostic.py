"""Audio Output and Microphone Diagnostic Engine for Windows."""
import subprocess
from typing import Any, Dict, List, Optional
import psutil

from backend.core.logger import get_logger
from backend.problem_solver.models import (
    DiagnosticItem, DiagnosticReport, DiagnosticStatus, ProblemCategory
)

logger = get_logger("AudioDiagnostic")


class AudioDiagnostic:
    """Diagnoses Windows audio playback devices, microphones, volume, mute, and Windows Audio services."""

    @staticmethod
    def run_diagnostic() -> DiagnosticReport:
        """Execute audio stack diagnostics on Windows."""
        items: List[DiagnosticItem] = []
        raw_evidence: Dict[str, Any] = {}
        overall_status = DiagnosticStatus.HEALTHY
        summary_points = []

        # 1. Inspect Windows Audio Services (Audiosrv, AudioEndpointBuilder)
        audio_services = ["Audiosrv", "AudioEndpointBuilder"]
        srv_data = {}
        for s_name in audio_services:
            try:
                srv = psutil.win_service_get(s_name)
                srv_data[s_name] = srv.status()
            except Exception:
                srv_data[s_name] = "not_found"

        raw_evidence["audio_services"] = srv_data

        audiosrv_running = srv_data.get("Audiosrv") == "running"
        endpoint_running = srv_data.get("AudioEndpointBuilder") == "running"

        if audiosrv_running and endpoint_running:
            items.append(DiagnosticItem(
                name="Windows Audio Services",
                status=DiagnosticStatus.HEALTHY,
                value="Running (Audiosrv & AudioEndpointBuilder)",
                details="Core Windows Audio pipeline services are active.",
            ))
        else:
            items.append(DiagnosticItem(
                name="Windows Audio Services",
                status=DiagnosticStatus.PROBLEM_DETECTED,
                value=f"Audiosrv: {srv_data.get('Audiosrv')}, EndpointBuilder: {srv_data.get('AudioEndpointBuilder')}",
                details="One or more Windows Audio system services are stopped.",
            ))
            overall_status = DiagnosticStatus.PROBLEM_DETECTED
            summary_points.append("Windows Audio service is stopped or not responding")

        # 2. Inspect Audio Endpoints via PowerShell CoreAudio / PnP
        audio_devices = []
        try:
            cmd = "powershell -NoProfile -Command \"Get-PnpDevice -Class 'AudioEndpoint', 'MEDIA' | Select-Object -Property FriendlyName, Status, Class, Problem | ConvertTo-Json -Compress\""
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                import json
                try:
                    data = json.loads(res.stdout.strip())
                    if isinstance(data, dict):
                        audio_devices = [data]
                    elif isinstance(data, list):
                        audio_devices = data
                except Exception:
                    audio_devices = []
        except Exception as e:
            logger.debug(f"PnP audio query error: {e}")

        raw_evidence["audio_devices"] = audio_devices

        if not audio_devices:
            items.append(DiagnosticItem(
                name="Audio Endpoints & Hardware",
                status=DiagnosticStatus.PROBLEM_DETECTED,
                value="No Audio Devices Found",
                details="No speaker, headphone, or soundcard found in Device Manager.",
            ))
            overall_status = DiagnosticStatus.PROBLEM_DETECTED
            summary_points.append("No audio devices detected")
        else:
            has_ok_speaker = False
            has_ok_mic = False
            for d in audio_devices:
                name = d.get("FriendlyName", "Audio Device")
                status = d.get("Status", "Unknown")
                problem = d.get("Problem", 0)

                is_ok = status == "OK" and problem == 0
                if any(w in name.lower() for w in ["speaker", "headphone", "audio", "realtek", "high definition"]):
                    if is_ok:
                        has_ok_speaker = True
                if any(w in name.lower() for w in ["mic", "microphone", "input", "array"]):
                    if is_ok:
                        has_ok_mic = True

                if not is_ok:
                    items.append(DiagnosticItem(
                        name=f"Audio Device: {name}",
                        status=DiagnosticStatus.PROBLEM_DETECTED,
                        value=f"Error (Code {problem})",
                        details=f"Audio device reported error state: {status}",
                        error_code=f"Code {problem}",
                    ))
                    overall_status = DiagnosticStatus.PROBLEM_DETECTED
                    summary_points.append(f"Audio device '{name}' error")

            if has_ok_speaker:
                items.append(DiagnosticItem(
                    name="Audio Output (Speakers/Headphones)",
                    status=DiagnosticStatus.HEALTHY,
                    value="Detected & Functional",
                    details="Valid audio output endpoint active in Windows.",
                ))
            if has_ok_mic:
                items.append(DiagnosticItem(
                    name="Audio Input (Microphone)",
                    status=DiagnosticStatus.HEALTHY,
                    value="Detected & Functional",
                    details="Microphone recording endpoint active in Windows.",
                ))

        if overall_status == DiagnosticStatus.HEALTHY:
            summary = "Audio playback and microphone devices are operational."
        else:
            summary = f"Audio issue detected: {'; '.join(summary_points)}."

        return DiagnosticReport(
            category=ProblemCategory.AUDIO,
            overall_status=overall_status,
            summary=summary,
            items=items,
            raw_evidence=raw_evidence,
            suggested_focus="audio_service" if not audiosrv_running else "audio_endpoint",
        )
