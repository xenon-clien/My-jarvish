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

from backend.core.logger import get_logger
from backend.voice.audio_manager import audio_manager
from backend.voice.speech_to_text import stt_manager
from backend.voice.text_to_speech import tts_manager
from backend.ai.agent import JarvisAgent
from backend.tools.autosubmit_watcher import start_autosubmit_watcher

logger = get_logger("JarvisApp")
agent = JarvisAgent()
_webview_window = None


class JarvisBridgeAPI:
    """Python-to-JavaScript Bridge exposed to the Desktop UI."""

    def send_command(self, text: str) -> str:
        """Process user command from the UI text/voice input."""
        logger.info(f"UI Command received: '{text}'")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(agent.process_user_input(text))
            loop.close()

            # Speak response via natural Swara voice
            if response.message:
                tts_manager.speak(response.message, block=False)
            return response.message or "Command executed."
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
            response = loop.run_until_complete(agent.process_user_input(cmd))
            loop.close()
            if response.message:
                tts_manager.speak(response.message, block=False)
        except Exception as exc:
            logger.error(f"Gesture command execution error: {exc}")


def _voice_listen_loop():
    """Continuous background voice listener for hands-free command execution."""
    logger.info("Continuous Voice Assistant thread started.")
    while True:
        try:
            if tts_manager.is_speaking():
                time.sleep(0.15)
                continue

            if stt_manager.enabled and stt_manager.is_microphone_available():
                user_text = stt_manager.listen_once(timeout=2.0, phrase_time_limit=5.0, silence_limit=0.25)
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
                    response = loop.run_until_complete(agent.process_user_input(user_text))
                    loop.close()

                    if response.message:
                        if _webview_window:
                            try:
                                _webview_window.evaluate_js(f"if (typeof setSpeakingState === 'function') setSpeakingState(true, {repr(response.message)});")
                            except Exception:
                                pass
                        tts_manager.speak(response.message, block=False)
            time.sleep(0.05)
        except Exception as exc:
            logger.debug(f"Voice listen loop error: {exc}")
            time.sleep(0.5)


def _start_background_services():
    """Start Voice, Gesture, and AutoSubmit background daemon services."""
    start_autosubmit_watcher()

    # Start Gesture Camera Loop with real-time UI split callback
    try:
        from backend.plugins.gesture.gesture_loop import start_gesture_loop
        start_gesture_loop(command_callback=_on_gesture_event)
        logger.info("Gesture Loop initialized with Desktop UI bridge.")
    except Exception as e:
        logger.warning(f"Gesture Loop init failed: {e}")

    # Start continuous background voice listener thread
    threading.Thread(target=_voice_listen_loop, daemon=True, name="JarvisVoiceListener").start()

    # Initial sweet greeting
    audio_manager.play_complete_chime()
    tts_manager.speak("नमस्ते शिवम! मैं तैयार हूँ, बताइए क्या मदद करूँ?", block=False)


def main():
    """Launch native Desktop Application window."""
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
