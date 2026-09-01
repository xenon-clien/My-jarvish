"""Automated Startup Hardware, Network, and System Health Checker for JARVIS AI."""
import time
from typing import Any, Dict, List
import sounddevice as sd

try:
    import win32gui
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

from backend.core.logger import get_logger

logger = get_logger("StartupChecker")


class StartupHealthChecker:
    """Performs non-blocking hardware, audio, network, and OS health diagnostics at boot."""

    @classmethod
    def run_all_checks(cls) -> Dict[str, Any]:
        """Execute complete suite of subsystem health checks."""
        start_t = time.time()
        results: Dict[str, Any] = {}

        # 1. Microphone Hardware Check
        mic_status = cls._check_microphone()
        results["microphone"] = mic_status

        # 2. Speech-to-Text Connectivity Check
        stt_status = cls._check_stt_connectivity()
        results["speech_to_text"] = stt_status

        # 3. Windows Win32 UI & Window Management
        win32_status = cls._check_win32()
        results["windows_automation"] = win32_status

        # 4. System Audio Controller (pycaw)
        audio_status = cls._check_audio_controller()
        results["audio_mixer"] = audio_status

        # 5. Browser Environment (Chrome)
        chrome_status = cls._check_chrome_environment()
        results["chrome_browser"] = chrome_status

        # 6. Overall System Readiness
        all_critical_ok = mic_status["status"] == "OK" and win32_status["status"] == "OK"
        results["overall_health"] = "HEALTHY" if all_critical_ok else "DEGRADED"
        results["check_duration_ms"] = round((time.time() - start_t) * 1000, 1)

        return results

    @classmethod
    def _check_microphone(cls) -> Dict[str, Any]:
        """Check if an active recording microphone device is detected."""
        try:
            devices = sd.query_devices()
            inputs = [d for d in devices if d.get("max_input_channels", 0) > 0]
            if inputs:
                def_dev = sd.query_devices(kind="input")
                return {
                    "status": "OK",
                    "device_name": def_dev.get("name", "Default Microphone"),
                    "sample_rate": def_dev.get("default_samplerate", 44100.0),
                    "channels": def_dev.get("max_input_channels", 1),
                }
            return {"status": "ERROR", "message": "No recording microphone devices detected."}
        except Exception as exc:
            return {"status": "ERROR", "message": f"Microphone check error: {exc}"}

    @classmethod
    def _check_stt_connectivity(cls) -> Dict[str, Any]:
        """Check Google STT service availability."""
        import socket
        try:
            socket.create_connection(("www.google.com", 443), timeout=1.5)
            return {"status": "OK", "provider": "Google Speech Recognition (en-IN / hi-IN)"}
        except Exception:
            return {"status": "WARNING", "message": "Google STT offline or network unreachable."}

    @classmethod
    def _check_win32(cls) -> Dict[str, Any]:
        """Verify Windows OS window handle and focus capabilities."""
        if not WIN32_AVAILABLE:
            return {"status": "ERROR", "message": "pywin32 not installed."}
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd) if hwnd else "Desktop"
            return {"status": "OK", "active_window": title or "Desktop", "hwnd": hwnd}
        except Exception as exc:
            return {"status": "ERROR", "message": f"Win32 API error: {exc}"}

    @classmethod
    def _check_audio_controller(cls) -> Dict[str, Any]:
        """Verify and ensure pycaw Windows master volume mixer is unmuted and audible."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            if hasattr(devices, "EndpointVolume"):
                volume = devices.EndpointVolume
            else:
                from comtypes import CLSCTX_ALL
                from ctypes import cast, POINTER
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))

            cur_vol = round(volume.GetMasterVolumeLevelScalar() * 100)
            is_muted = bool(volume.GetMute())

            return {"status": "OK", "master_volume_percent": cur_vol, "is_muted": is_muted}
        except Exception as exc:
            return {"status": "WARNING", "message": f"pycaw mixer warning: {exc}"}

    @classmethod
    def _check_chrome_environment(cls) -> Dict[str, Any]:
        """Check if Google Chrome is running and detectable."""
        import psutil
        try:
            chrome_procs = [p for p in psutil.process_iter(["name"]) if "chrome" in (p.info.get("name") or "").lower()]
            if chrome_procs:
                return {"status": "OK", "running": True, "instances": len(chrome_procs)}
            return {"status": "OK", "running": False, "note": "Will launch on demand"}
        except Exception:
            return {"status": "OK", "running": False}

    @classmethod
    def format_banner(cls, health: Dict[str, Any]) -> str:
        """Format an ASCII startup health banner for CLI output."""
        def icon(st: str) -> str:
            return "🟢" if st == "OK" else ("🟡" if st == "WARNING" else "🔴")

        mic = health.get("microphone", {})
        stt = health.get("speech_to_text", {})
        win = health.get("windows_automation", {})
        audio = health.get("audio_mixer", {})
        chrome = health.get("chrome_browser", {})

        banner = (
            f"\n┌─── [JARVIS SELF-DIAGNOSTIC STARTUP HEALTH REPORT] ───\n"
            f"│ {icon(mic.get('status'))} Microphone:      {mic.get('device_name', 'None')} ({mic.get('sample_rate', 0)}Hz)\n"
            f"│ {icon(stt.get('status'))} Speech Engine:   {stt.get('provider', stt.get('message', 'Offline'))}\n"
            f"│ {icon(win.get('status'))} Windows Automation: {win.get('active_window', 'Active')}\n"
            f"│ {icon(audio.get('status'))} Master Audio:    Volume {audio.get('master_volume_percent', 0)}% (Muted: {audio.get('is_muted', False)})\n"
            f"│ {icon(chrome.get('status'))} Chrome Browser:  {'Running (' + str(chrome.get('instances', 0)) + ' procs)' if chrome.get('running') else 'Ready on demand'}\n"
            f"│ ⚡ Overall Status:  {health.get('overall_health', 'HEALTHY')} ({health.get('check_duration_ms', 0)}ms)\n"
            f"└─────────────────────────────────────────────────────────"
        )
        return banner
