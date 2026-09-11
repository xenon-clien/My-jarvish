"""
J.A.R.V.I.S. Standalone Native Desktop Application.

Runs the complete AI Audio Brain, Voice Engine, Gesture Tracking, and
3D Glowing Golden Arc Reactor Desktop Interface in a single native window.
"""
import asyncio
import os
import sys
import threading
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

# Configure production runtime defaults for native desktop app:
# Allow live browser automation, disable dev safe mode, and keep physical mouse/keyboard input disabled
if "pytest" not in sys.modules and not os.environ.get("PYTEST_CURRENT_TEST"):
    os.environ["JARVIS_DEV_SAFE_MODE"] = "0"
    os.environ["JARVIS_ALLOW_LIVE_BROWSER_AUTOMATION"] = "1"
    if "JARVIS_ALLOW_PHYSICAL_INPUT" not in os.environ:
        os.environ["JARVIS_ALLOW_PHYSICAL_INPUT"] = "0"

from backend.core.logger import get_logger
from backend.voice.audio_manager import audio_manager
from backend.voice.speech_to_text import stt_manager
from backend.voice.text_to_speech import tts_manager
from backend.core.command_processor import command_processor, ExecutionStatus

logger = get_logger("JarvisApp")
_webview_window = None


class JarvisBridgeAPI:
    """Python-to-JavaScript Bridge exposed to the Desktop UI."""

    def send_command(self, text: str) -> str:
        """Process user command from the UI text/voice input."""
        logger.info(f"UI Command received: '{text}'")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            ctx = loop.run_until_complete(command_processor.process_command(text, source="ui"))
            loop.close()

            # Speak response via natural voice
            if ctx.response_message:
                tts_manager.speak(ctx.response_message, block=False)
            return ctx.response_message or "Command executed."
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return f"Error: {e}"


def _on_gesture_event(gesture_name: str, cmd: str = ""):
    """Called whenever a hand gesture is detected by the camera loop."""
    global _webview_window
    logger.info(f"Gesture detected: {gesture_name} -> command: '{cmd}'")
    if _webview_window:
        try:
            # Trigger real-time 3D Split & Morph animation in the desktop UI
            _webview_window.evaluate_js(f"if (typeof onGestureDetected === 'function') onGestureDetected('{gesture_name}');")
        except Exception as e:
            logger.debug(f"JS evaluate error: {e}")

    if cmd:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            ctx = loop.run_until_complete(command_processor.process_command(cmd, source="gesture"))
            loop.close()
            if ctx.response_message:
                tts_manager.speak(ctx.response_message, block=False)
        except Exception as exc:
            logger.error(f"Gesture command execution error: {exc}")


def _voice_listen_loop():
    """Continuous background voice listener for hands-free command execution."""
    logger.info("Continuous Voice Assistant thread started.")
    while True:
        try:
            # Prevent microphone from capturing speaker reverberation/echo
            if tts_manager.is_speaking() or (time.time() - tts_manager.last_spoken_time < 0.70):
                time.sleep(0.10)
                continue

            if stt_manager.enabled and stt_manager.is_microphone_available():
                user_text = stt_manager.listen_once(timeout=6.0, phrase_time_limit=6.5, silence_limit=0.65)
                if user_text and len(user_text.strip()) > 1:
                    tts_manager.stop()
                    logger.info(f"Voice speech captured: '{user_text}'")
                    if _webview_window:
                        try:
                            _webview_window.evaluate_js(f"if (typeof setSpeakingState === 'function') setSpeakingState(true, {repr(user_text)});")
                        except Exception:
                            pass

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    ctx = loop.run_until_complete(command_processor.process_command(user_text, source="voice"))
                    loop.close()

                    if ctx.response_message:
                        if _webview_window:
                            try:
                                _webview_window.evaluate_js(f"if (typeof setSpeakingState === 'function') setSpeakingState(true, {repr(ctx.response_message)});")
                            except Exception:
                                pass
                        tts_manager.speak(ctx.response_message, block=False)
            time.sleep(0.05)
        except Exception as exc:
            logger.debug(f"Voice listen loop error: {exc}")
            time.sleep(0.5)


def _start_background_services():
    """Start Voice background daemon service (AutoSubmit permanently removed)."""
    # Camera & Gesture loop completely disabled for user privacy and security
    logger.info("Camera & Gesture loop disabled for user privacy — camera will never be accessed.")

    # Start continuous background voice listener thread
    threading.Thread(target=_voice_listen_loop, daemon=True, name="JarvisVoiceListener").start()

    # Initial startup chime (Silent on speech until user speaks)
    audio_manager.play_complete_chime()


_SINGLE_INSTANCE_MUTEX = None


def _acquire_single_instance_lock() -> bool:
    """Ensure strictly ONE instance of JARVIS Desktop App runs at any time across the system."""
    global _SINGLE_INSTANCE_MUTEX
    import ctypes
    ERROR_ALREADY_EXISTS = 183
    kernel32 = ctypes.windll.kernel32
    _SINGLE_INSTANCE_MUTEX = kernel32.CreateMutexW(None, False, "JARVIS_DESKTOP_APP_MUTEX_SINGLETON")
    last_error = kernel32.GetLastError()
    if last_error == ERROR_ALREADY_EXISTS:
        logger.warning("Another instance of JARVIS Desktop is already running. Exiting duplicate process immediately.")
        return False
    return True


def main():
    """Launch native Desktop Application window."""
    if not _acquire_single_instance_lock():
        sys.exit(0)

    global _webview_window
    logger.info("Launching JARVIS Native Desktop Application...")

    html_file = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
    api = JarvisBridgeAPI()

    import webview
    _webview_window = webview.create_window(
        title="J.A.R.V.I.S. — Personal AI Assistant",
        url=html_file,
        js_api=api,
        width=1050,
        height=850,
        resizable=True,
        background_color="#030201",
        text_select=False,
    )
    # Start native window and run background services in dedicated worker thread
    webview.start(_start_background_services, debug=False)


if __name__ == "__main__":
    main()
