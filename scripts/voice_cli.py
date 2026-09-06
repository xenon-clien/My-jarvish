"""Hands-free Voice Assistant interface with Wake Word & Standby Engine for JARVIS AI.

Listens continuously via microphone, detects Wake Words ('On Jarvis' / 'Hey Jarvis'),
handles Standby Mode ('Off' / 'Sleep'), executes tools with JARVIS Brain,
and speaks responses aloud using the offline Windows TTS engine.
"""
import asyncio
import os
import re
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

# Configure UTF-8 for Windows Console to prevent box character artifacts
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
        os.system("chcp 65001 >nul")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from backend.ai.action_planner import action_planner
from backend.ai.agent import AgentState, JarvisAgent
from backend.ai.intent_engine import fast_intent_engine
from backend.core.config import get_settings
from backend.core.logger import get_logger
from backend.voice.audio_manager import audio_manager
from backend.voice.speech_to_text import stt_manager
from backend.voice.text_to_speech import tts_manager

console = Console()
settings = get_settings()
logger = get_logger("VoiceCLI")

WAKE_WORDS = [
    "shivam ai", "shivam", "hey shivam", "on shivam", "shivam on",
    "jarvis", "on jarvis", "hey jarvis", "jarvis on", "wake up", "on karo"
]
SLEEP_WORDS = ["off", "go to sleep", "sleep jarvis", "sleep shivam", "standby", "so jao", "sleep", "turn off"]


def print_voice_banner(is_standby: bool = False):
    """Display futuristic Dual-AI Voice Mode banner."""
    banner = Text()
    banner.append("🎙️ J.A.R.V.I.S. YOUTUBE PRODUCTION ASSISTANT ONLINE 🎙️\n", style="bold cyan")
    banner.append(f"👤 Master:            {settings.USER_NAME}\n", style="bold white")
    banner.append(f"🧠 Primary Brain:     OpenAI GPT-6 Astra ({settings.ASTRA_MODEL})\n", style="bold green")
    banner.append(f"🛡️ Standby Fallback:  Google Gemini ({settings.AI_MODEL})\n", style="bold cyan")
    banner.append("🎯 Production Target: YOUTUBE ONLY (Single-App Grounded Focus)\n", style="bold yellow")
    banner.append("⚡ Wake Words:        'On Jarvis', 'Hey Jarvis', 'Jarvis'\n", style="bold cyan")
    banner.append("🌙 Standby Words:     'Off', 'Sleep', 'Go to sleep'\n", style="italic dim")
    banner.append("💻 YouTube Controls:  'Pehli short chalao', 'Next short', 'Pause', 'Fullscreen', 'Like karo'", style="cyan")

    console.print(Panel(banner, border_style="bright_blue", title="⚡ JARVIS YOUTUBE-ONLY PRODUCTION SYSTEM ACTIVE ⚡"))


async def run_voice_loop():
    """Main continuous voice interaction loop with Wake Word & Standby Engine."""
    print_voice_banner()

    # 1. Run Comprehensive Startup Hardware, OS & Network Health Checks
    from backend.diagnostics.startup_checker import StartupHealthChecker
    from backend.diagnostics.engine import diagnostic_engine
    from rich.table import Table

    startup_health = StartupHealthChecker.run_all_checks()
    console.print(StartupHealthChecker.format_banner(startup_health))

    agent = JarvisAgent()

    # Start AutoSubmit watcher — auto-clicks Submit/Proceed buttons in Antigravity
    try:
        from backend.tools.autosubmit_watcher import start_autosubmit_watcher
        start_autosubmit_watcher()
    except Exception as _e:
        logger.debug(f"AutoSubmit watcher could not start: {_e}")

    # Gesture loop disabled per user request (webcam OFF)
    _gesture_queue = None

    # Initial chime (Silent until user speaks)
    audio_manager.play_complete_chime()

    mic_available = stt_manager.is_microphone_available()
    if not mic_available:
        console.print("[bold yellow]⚠️ No microphone detected. Operating in Keyboard Mode.[/bold yellow]\n")

    is_standby = False
    console.print("\n[bold green]● J.A.R.V.I.S. is listening... (Speak anytime in Hindi/English, or type '/diag' for health dashboard)[/bold green]\n")

    while True:
        try:
            user_text = None

            # ── Check Gesture Queue first (hand gesture commands have priority) ──
            if _gesture_queue:
                try:
                    raw_gesture = _gesture_queue.get_nowait()
                    if raw_gesture:
                        g_map = {
                            "OPEN_PALM": "next video",
                            "CLOSED_FIST": "pause video",
                            "TWO_FINGERS": "comments dikhao",
                        }
                        user_text = g_map.get(raw_gesture, raw_gesture)
                        console.print(f"\n[bold magenta]🤚 Gesture Detected:[/bold magenta] {raw_gesture} -> Executing '{user_text}'")
                except Exception:
                    pass

            if not user_text and mic_available and stt_manager.enabled:
                user_text = stt_manager.listen_once(timeout=6.0, phrase_time_limit=12.0, silence_limit=0.95)

            # If silence or no speech detected during the listening window, loop back quietly
            if not user_text:
                if not mic_available:
                    console.print(f"[{settings.USER_NAME}] ❯ ", style="bold cyan", end="")
                    user_text = input().strip()
                else:
                    await asyncio.sleep(0.05)
                    continue

            if not user_text:
                continue

            # Instantly stop any previous speech playback as soon as user commands something new
            tts_manager.stop()

            # ── STT Artifact Normalization ──────────────────────────────────────────
            # Fix digit-substitution artifacts from speech engine (e.g. "m1nim1se" → "minimize")
            _stt_fixes = [
                (r"\bm[1i]n[1i]m[1i]se?\b",   "minimize"),
                (r"\bm[1i]n[1i]m[1i]ze?\b",   "minimize"),
                (r"\bant[1i]\b",               "anti"),
                (r"\bantigrav[1i]ty\b",         "antigravity"),
                (r"\bantigrav[1i]t[1i]\b",      "antigravity"),
                (r"\bpr[1i]ce\b",              "minimize"),   # "price anti" = STT mishear of "minimize anti"
                (r"\bmax[1i]m[1i]ze?\b",        "maximize"),
                (r"\bmax[1i]m[1i]se?\b",        "maximize"),
            ]
            for _pat, _rep in _stt_fixes:
                user_text = re.sub(_pat, _rep, user_text, flags=re.IGNORECASE)
            # Expand "anti" alone → "antigravity" when next to a window action verb
            user_text = re.sub(r"\b(minimize|maximize|restore|close)\s+anti\b", r"\1 antigravity", user_text, flags=re.IGNORECASE)
            # ────────────────────────────────────────────────────────────────────────

            cleaned_text = user_text.lower().strip()
            console.print(f"\n[bold green]🗣️ You said:[/bold green] \"{user_text}\"")

            # Process every non-empty user statement and question
            if not user_text or len(user_text.strip()) < 1:
                continue

            # Standby mode check
            if is_standby:
                if any(w in cleaned_text for w in WAKE_WORDS):
                    is_standby = False
                    audio_manager.play_wake_chime()
                    console.print("[bold green]⚡ JARVIS WOKE UP![/bold green]")

                    # Remove the wake word from command if command followed it
                    stripped_cmd = cleaned_text
                    for w in WAKE_WORDS:
                        stripped_cmd = stripped_cmd.replace(w, "").strip()

                    if not stripped_cmd:
                        tts_manager.speak("हाँजी बॉस।", block=False)
                        continue
                    else:
                        user_text = stripped_cmd
                else:
                    # Ignore background chatter in standby mode
                    await asyncio.sleep(0.1)
                    continue

            # Check if user wants to put JARVIS into Standby
            if cleaned_text in SLEEP_WORDS or any(cleaned_text == w for w in SLEEP_WORDS):
                is_standby = True
                audio_manager.play_wake_chime()
                farewell = "स्टैंडबाय मोड ऑन।"
                console.print(f"[bold yellow]JARVIS:[/bold yellow] {farewell}")
                tts_manager.speak(farewell, block=True)
                continue

            # ── Observability & Developer CLI Commands ──
            if cleaned_text.startswith("/test"):
                from scripts.reproduce_debug import test_youtube_first_short, test_youtube_second_short, test_system_volume, run_all_tests
                parts = cleaned_text.split()
                target = parts[1] if len(parts) > 1 else "all"
                console.print(f"\n[bold magenta]🧪 RUNNING REPRODUCER TEST:[/bold magenta] {target}")
                if target == "youtube-first-short":
                    await test_youtube_first_short()
                elif target == "youtube-second-short":
                    await test_youtube_second_short()
                elif target == "system-volume":
                    await test_system_volume()
                else:
                    await run_all_tests()
                continue

            if cleaned_text.startswith("/trace"):
                from backend.observability.command_tracer import command_tracer
                parts = cleaned_text.split()
                if len(parts) > 1:
                    cid = parts[1].strip()
                    panel_text = command_tracer.format_debug_panel(cid)
                else:
                    recent = command_tracer.get_recent_traces(1)
                    panel_text = command_tracer.format_debug_panel(recent[0].command_id) if recent else "No recent command traces found."
                console.print(Panel(panel_text, title="🔍 Command Lifecycle Trace", border_style="cyan"))
                continue

            # ── AI Provider Architecture & Developer Commands ──
            if cleaned_text in ["/provider reset astra", "/provider reset", "provider reset astra"]:
                from backend.ai.providers import ai_provider_router
                res = ai_provider_router.reset_astra_state()
                console.print(Panel(
                    f"[bold green]✅ Astra State Reset Successful[/bold green]\n"
                    f"[bold]Status:[/bold]   {res['astra_status']}\n"
                    f"[bold]Model:[/bold]    {res['astra_model']}\n"
                    f"[bold]Message:[/bold]  Live routing re-enabled.",
                    title="⚡ Provider Circuit Breaker Reset",
                    border_style="green",
                ))
                continue

            if cleaned_text in ["/provider status", "provider status", "/ai-status", "ai status", "ai-status"]:
                from backend.ai.providers import ai_provider_router
                stat = ai_provider_router.get_status_summary()
                status_color = "green" if stat['astra_status'] == "AVAILABLE" else "yellow" if stat['astra_status'] == "TEMPORARILY_DEGRADED" else "red"
                ai_panel = (
                    f"[bold cyan]OPENAI GPT-6 ASTRA[/bold cyan]\n"
                    f"  [bold]Role:[/bold]              PRIMARY BRAIN / COMMANDER\n"
                    f"  [bold]Purpose:[/bold]           Natural Language + Structured Tool Calling + Reasoning\n"
                    f"  [bold]Model:[/bold]             {stat['astra_model']}\n"
                    f"  [bold]Status:[/bold]            [{status_color}]{stat['astra_status']}[/{status_color}]\n"
                    f"  [bold]Reason:[/bold]            {stat.get('astra_reason') or 'Nominal operational status'}\n"
                    f"  [bold]Total Requests:[/bold]    {stat['total_requests']}\n"
                    f"  [bold]Success / Fail:[/bold]    {stat['successful_requests']} / {stat['consecutive_failures']}\n"
                    f"  [bold]Fallback Routed:[/bold]   {stat['fallback_requests']}\n\n"
                    f"[bold blue]GOOGLE GEMINI[/bold blue]\n"
                    f"  [bold]Role:[/bold]              STANDBY AUTOMATIC FALLBACK\n"
                    f"  [bold]Purpose:[/bold]           Zero-Downtime High-Reliability Standby Brain\n"
                    f"  [bold]Model:[/bold]             {stat['gemini_model']}\n"
                    f"  [bold]Status:[/bold]            🟢 STANDBY READY (Auto-invoked on quota/degradation)\n\n"
                    f"[bold magenta]NVIDIA NEMOTRON / OPENROUTER[/bold magenta]\n"
                    f"  [bold]Status:[/bold]            🚫 DISABLED from normal runtime (Decoupled)"
                )
                console.print(Panel(ai_panel, title="🤖 JARVIS AI PROVIDER ARCHITECTURE", border_style="bright_blue"))
                continue

            if cleaned_text in ["/issues", "issues", "bug list"]:
                from backend.diagnostics.issue_tracker import issue_tracker
                open_issues = issue_tracker.get_open_issues()
                if not open_issues:
                    console.print("[bold green]✅ No open diagnostic issues currently tracked.[/bold green]")
                else:
                    issues_table = Table(title="📋 JARVIS ACTIVE DIAGNOSTIC ISSUES", border_style="yellow")
                    issues_table.add_column("Issue ID", style="bold cyan", width=12)
                    issues_table.add_column("Domain", width=10)
                    issues_table.add_column("Command", width=24)
                    issues_table.add_column("Severity", width=10)
                    issues_table.add_column("Status", width=12)
                    issues_table.add_column("Root Cause / Layer", style="yellow", width=30)
                    for iss in open_issues:
                        sev_style = "red" if iss.severity in ["CRITICAL", "ERROR"] else "yellow"
                        issues_table.add_row(
                            iss.issue_id,
                            iss.domain,
                            iss.command[:22],
                            f"[{sev_style}]{iss.severity}[/{sev_style}]",
                            iss.status,
                            iss.root_cause[:28] if iss.root_cause else (iss.affected_layer or "Pending"),
                        )
                    console.print(issues_table)
                continue

            if cleaned_text in ["/last-error", "last error"]:
                from backend.observability.command_tracer import command_tracer
                recent = command_tracer.get_recent_traces(limit=10)
                failed = next((t for t in recent if t.verification_status == "FAIL" or t.error), None)
                if not failed:
                    console.print("[bold green]✅ No recent errors found in command trace history.[/bold green]")
                else:
                    console.print(Panel(
                        f"[bold]Command ID:[/bold]  {failed.command_id}\n"
                        f"[bold]Command:[/bold]     \"{failed.raw_transcript}\"\n"
                        f"[bold]Domain:[/bold]      {failed.domain}\n"
                        f"[bold]Intent:[/bold]      {failed.intent}\n"
                        f"[bold]Status:[/bold]      {failed.verification_status}\n"
                        f"[bold red]Error:[/bold red]       {failed.error or 'Verification Mismatch'}\n"
                        f"[bold]Trace File:[/bold]  {failed.playwright_trace_path or 'N/A'}",
                        title="🚨 Last Runtime Error",
                        border_style="red",
                    ))
                continue

            if cleaned_text in ["/diagnose-last-error", "diagnose last error"]:
                from backend.diagnostics.self_debug_manager import self_debug_manager
                with console.status("[bold magenta]NVIDIA Nemotron is analyzing empirical failure evidence...[/bold magenta]", spinner="dots"):
                    await self_debug_manager.diagnose_latest_failure()
                continue

            if cleaned_text in ["/nemotron-status", "nemotron status"]:
                from backend.diagnostics.nemotron_guard import nemotron_guard
                stat = nemotron_guard.get_status_summary()
                console.print(Panel(
                    f"[bold]Model:[/bold]           {stat['model']}\n"
                    f"[bold]Status:[/bold]          {stat['status']}\n"
                    f"[bold]Requests Today:[/bold]  {stat['requests_today']} / {stat['max_daily_requests']}\n"
                    f"[bold]Remaining:[/bold]       {stat['quota_remaining']}\n"
                    f"[bold]Enabled:[/bold]         {stat['enabled']}\n"
                    f"[bold]Paid Fallback:[/bold]   {stat['paid_fallback']}",
                    title="⚡ NVIDIA Nemotron Debugger Quota & Safety Guard",
                    border_style="magenta",
                ))
                continue

            if cleaned_text in ["/nemotron-enable", "nemotron enable"]:
                from backend.diagnostics.nemotron_guard import nemotron_guard
                nemotron_guard.set_enabled(True)
                console.print("[bold green]✅ NVIDIA Nemotron Debugger has been ENABLED.[/bold green]")
                continue

            if cleaned_text in ["/nemotron-disable", "nemotron disable"]:
                from backend.diagnostics.nemotron_guard import nemotron_guard
                nemotron_guard.set_enabled(False)
                console.print("[bold yellow]⚠️ NVIDIA Nemotron Debugger has been DISABLED.[/bold yellow]")
                continue

            if cleaned_text in ["/regression-status", "regression status"]:
                console.print("[bold cyan]🧪 Running Automated Regression Suite in background...[/bold cyan]")
                from subprocess import Popen, PIPE
                proc = Popen(["python", "-m", "pytest", "tests/test_regression_suite.py", "-q"], stdout=PIPE, stderr=PIPE, text=True)
                stdout, _ = proc.communicate()
                console.print(Panel(stdout.strip(), title="🧪 Regression Test Results", border_style="cyan"))
                continue

            # Check Diagnostic Dashboard Commands
            if cleaned_text in ["/diag", "diag", "diagnostics", "/health", "health", "system health", "bug dashboard"]:
                health_data = diagnostic_engine.get_feature_health()
                diag_table = Table(title="📊 JARVIS LIVE FEATURE HEALTH & TELEMETRY", border_style="bright_magenta")
                diag_table.add_column("Subsystem", style="bold cyan", width=16)
                diag_table.add_column("Status", width=12)
                diag_table.add_column("Attempts", width=10)
                diag_table.add_column("Success Rate", width=14)
                diag_table.add_column("Avg Latency", width=14)
                diag_table.add_column("Top Error / Root Cause", style="yellow", width=28)

                for feat, h in health_data.items():
                    icon = "🟢 HEALTHY" if h.healthStatus == "HEALTHY" else ("🟡 DEGRADED" if h.healthStatus == "DEGRADED" else "🔴 BROKEN")
                    style_str = "green" if h.successRatePercent >= 90 else ("yellow" if h.successRatePercent >= 60 else "red")
                    diag_table.add_row(
                        feat,
                        icon,
                        str(h.totalAttempts),
                        f"[{style_str}]{h.successRatePercent}%[/{style_str}]",
                        f"{h.avgLatencyMs} ms",
                        h.topErrorCode or "None",
                    )
                console.print(diag_table)
                continue
                continue

            if cleaned_text.startswith("/why") or cleaned_text.startswith("why did this fail"):
                parts = cleaned_text.split()
                if len(parts) > 1:
                    cid = parts[1].strip()
                    explanation = diagnostic_engine.why_did_this_fail(cid)
                else:
                    recent = diagnostic_engine.get_recent_traces(1)
                    explanation = diagnostic_engine.why_did_this_fail(recent[0].correlationId) if recent else "No recent transactions found."
                console.print(Panel(explanation, title="Root-Cause Analysis", border_style="cyan"))
                continue

            # Check complete exit phrases
            if cleaned_text in ["exit", "quit", "power down", "goodbye jarvis", "bye jarvis"]:
                farewell = "अलविदा बॉस।"
                console.print(f"[bold yellow]JARVIS:[/bold yellow] {farewell}")
                audio_manager.play_wake_chime()
                tts_manager.speak(farewell, block=True)
                break

            # Play subtle wake chime
            audio_manager.play_wake_chime()

            # ── Canonical Command Processor Execution ─────────────────────────
            from backend.core.command_processor import command_processor, ExecutionStatus
            from backend.observability.failure_bundle import failure_bundle_manager

            with console.status("[bold cyan]JARVIS is executing...[/bold cyan]", spinner="dots"):
                ctx = await command_processor.process_command(user_text, source="voice")

            # Display and speak response
            if ctx.status == ExecutionStatus.VERIFIED_FAILURE:
                failure_bundle_manager.create_failure_bundle(
                    command_id=ctx.command_id,
                    error_message=ctx.response_message,
                )
                console.print(Panel(
                    f"[bold red]❌ Error:[/bold red] {ctx.response_message}",
                    border_style="red",
                ))
                audio_manager.play_error_chime()
                tts_manager.speak("Boss, action execute karne mein issue aaya.", block=True)
            else:
                console.print(f"[bold cyan]JARVIS ({ctx.command_id}):[/bold cyan] {ctx.response_message}\n")
                audio_manager.play_complete_chime()

                is_media_action = ctx.domain == "media" or any(re.search(r"\b" + re.escape(w) + r"\b", cleaned_text) for w in [
                    "video", "song", "gaana", "vlog", "reel", "reels", "short", "shorts", "youtube", "click", "like", "scroll", "next", "previous", "pause", "play"
                ])

                if is_media_action:
                    # Ultra-short acknowledgement so it never overlaps with media
                    tts_manager.speak("जी बॉस!", block=True)
                elif ctx.action:
                    # Keep implementation voice concise
                    spoken_txt = ctx.response_message.split("\n")[0].split(".")[0].strip()
                    if not spoken_txt or len(spoken_txt) > 50:
                        spoken_txt = "Ji Boss, ho gaya."
                    tts_manager.speak(spoken_txt, block=False)
                elif ctx.response_message:
                    # Conversational dialogue: speak cleanly
                    tts_manager.speak(ctx.response_message, block=False)

        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold yellow]Voice Assistant stopped by user.[/bold yellow]")
            break
        except Exception as exc:
            console.print(f"\n[bold red]Error in voice loop:[/bold red] {exc}\n")
            await asyncio.sleep(1.0)

def acquire_single_instance_lock():
    """Ensure only ONE instance of JARVIS voice assistant is running at any time."""
    if sys.platform == "win32":
        import ctypes
        ERROR_ALREADY_EXISTS = 183
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\JARVIS_VOICE_CLI_MUTEX_SINGLETON")
        last_error = ctypes.windll.kernel32.GetLastError()
        if last_error == ERROR_ALREADY_EXISTS:
            console.print(Panel(
                "[bold red]⚠️ JARVIS Voice Assistant is already running in another window![/bold red]\n"
                "[yellow]Ek time par do instances run karne se double voice echo ho sakti hai.\n"
                "Kripya purani window use karein ya Task Manager se purana process band karein.[/yellow]",
                title="Single Instance Lock",
                border_style="red"
            ))
            return None
        return mutex
    return True


if __name__ == "__main__":
    _mutex = acquire_single_instance_lock()
    if _mutex:
        try:
            asyncio.run(run_voice_loop())
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[bold yellow]👋 JARVIS Voice Loop stopped safely.[/bold yellow]")
        except Exception as _err:
            console.print(f"\n[bold red]Error in JARVIS Voice loop:[/bold red] {_err}")
        finally:
            if sys.platform == "win32" and _mutex:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(_mutex)

