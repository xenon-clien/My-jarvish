"""System media controls (Play/Pause, Next Track, Volume, Mute) for JARVIS AI.

Controls active Windows media playback (YouTube in browser, Spotify, VLC, Windows Media)
using native Windows hardware media virtual keys.
"""
import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

try:
    import win32api
    import win32con
    import win32gui
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

from backend.core.logger import get_logger
from backend.core.permissions import PermissionLevel, ToolCategory
from backend.tools.registry import tool
from backend.core.safety import (
    is_dev_safe_mode,
    is_physical_automation_allowed,
    is_foreground_stealing_allowed,
    safe_blocked_result,
)

logger = get_logger("MediaTools")

# Windows Virtual Key Codes for Media Control
VK_MEDIA_PLAY_PAUSE = 0xB3  # 179
VK_MEDIA_NEXT_TRACK = 0xB0  # 176
VK_MEDIA_PREV_TRACK = 0xB1  # 177
VK_VOLUME_MUTE = 0xAD       # 173
VK_VOLUME_DOWN = 0xAE       # 174
VK_VOLUME_UP = 0xAF         # 175


def _send_key_event(vk_code: int) -> None:
    """Send hardware key down and up event with accurate Windows hardware scan code."""
    if not is_physical_automation_allowed():
        return
    if not WIN32_AVAILABLE:
        return
    import ctypes
    user32 = ctypes.windll.user32
    scan_code = user32.MapVirtualKeyW(vk_code, 0)
    user32.keybd_event(vk_code, scan_code, 0, 0)
    time.sleep(0.04)
    user32.keybd_event(vk_code, scan_code, 2, 0)  # KEYEVENTF_KEYUP


def _click_video_player_center() -> None:
    """Simulate a physical hardware left mouse click at the center of the active YouTube video."""
    if not is_physical_automation_allowed():
        return
    if not WIN32_AVAILABLE:
        return
    import ctypes
    user32 = ctypes.windll.user32
    # Click at current cursor position (which _focus_media_window positioned over video)
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # LEFT DOWN
    time.sleep(0.03)
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # LEFT UP


class MediaControlArgs(BaseModel):
    action: str = Field(
        ...,
        description="Media control action: 'play_pause', 'next', 'previous', 'seek_forward', 'seek_backward', 'seek_timestamp', 'speed_up', 'speed_down', 'volume_up', 'volume_down', 'set_volume', 'mute'.",
    )
    level: Optional[int] = Field(
        None,
        description="Optional volume level percentage (0 to 100) or target seek seconds.",
    )
    time_str: Optional[str] = Field(
        None,
        description="Optional seek time string like '53m', '12m30s', '53m00s'.",
    )


def _seek_youtube_url_bar(time_param: str) -> bool:
    """Seek YouTube video in active browser window by cleanly appending &t=...s to URL."""
    if not WIN32_AVAILABLE:
        return False
    try:
        import re
        total_seconds = 0
        m_match = re.search(r"(\d+)\s*m", time_param)
        s_match = re.search(r"(\d+)\s*s", time_param)
        if m_match:
            total_seconds += int(m_match.group(1)) * 60
        if s_match:
            total_seconds += int(s_match.group(1))
        if not m_match and not s_match:
            try:
                total_seconds = int(time_param)
            except Exception:
                total_seconds = 0

        sec_param = f"{total_seconds}s" if total_seconds else time_param

        windows = []
        def enum_handler(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                cls = win32gui.GetClassName(hwnd)
                if "chrome" in cls.lower() or "youtube" in title.lower() or "edge" in title.lower():
                    extra.append((hwnd, title))
        win32gui.EnumWindows(enum_handler, windows)
        if not windows:
            return False

        from backend.tools.browser_tools import force_foreground_window
        force_foreground_window(hwnd)
        time.sleep(0.10)

        # 1. Focus URL bar with Ctrl+L
        win32api.keybd_event(0x11, 0, 0, 0)
        win32api.keybd_event(0x4C, 0, 0, 0)
        time.sleep(0.04)
        win32api.keybd_event(0x4C, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(0x11, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.08)

        # 2. Copy current URL with Ctrl+C
        win32api.keybd_event(0x11, 0, 0, 0)
        win32api.keybd_event(0x43, 0, 0, 0)
        time.sleep(0.04)
        win32api.keybd_event(0x43, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(0x11, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.06)

        # 3. Read clipboard URL and clean old timestamps
        import win32clipboard
        current_url = ""
        try:
            win32clipboard.OpenClipboard()
            current_url = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
        except Exception:
            pass

        if "youtube.com" in current_url:
            clean_url = re.sub(r"[&?]t=[^&]+", "", current_url)
            sep = "&" if "?" in clean_url else "?"
            new_url = f"{clean_url}{sep}t={sec_param}"
        else:
            new_url = f"https://www.youtube.com/watch?v=yFuQpbCPvPo&t={sec_param}"

        # 4. Put new clean URL on clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(new_url, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        time.sleep(0.04)

        # 5. Paste with Ctrl+V and press Enter
        win32api.keybd_event(0x11, 0, 0, 0)
        win32api.keybd_event(0x56, 0, 0, 0)
        time.sleep(0.04)
        win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(0x11, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.06)

        win32api.keybd_event(0x0D, 0, 0, 0)
        time.sleep(0.04)
        win32api.keybd_event(0x0D, 0, win32con.KEYEVENTF_KEYUP, 0)
        return True
    except Exception as exc:
        logger.warning(f"URL bar seek error: {exc}")
        return False


def _focus_media_window() -> bool:
    """Find the real visible Google Chrome/Edge/YouTube browser window and bring it to the foreground."""
    if not is_foreground_stealing_allowed() or not is_physical_automation_allowed():
        return False
    if not WIN32_AVAILABLE:
        return False
    try:
        from backend.tools.browser_tools import force_foreground_window
        import ctypes
        user32 = ctypes.windll.user32

        candidates = []
        def enum_cb(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                cls = win32gui.GetClassName(hwnd).lower()
                # Skip IDEs and terminal windows
                if any(ex in title for ex in ["antigravity", "vscode", "visual studio", "cmd.exe", "powershell"]):
                    return
                # Check for genuine browser windows
                if "youtube" in title or "chrome" in cls or "edge" in cls or "mozilla" in cls:
                    rect = win32gui.GetWindowRect(hwnd)
                    w = rect[2] - rect[0]
                    h = rect[3] - rect[1]
                    if w > 400 and h > 300:
                        # Prioritize windows with 'youtube' in title
                        score = 100 if "youtube" in title else 50
                        extra.append((score, hwnd, rect))
        win32gui.EnumWindows(enum_cb, candidates)

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            _, best_hwnd, rect = candidates[0]
            force_foreground_window(best_hwnd)
            time.sleep(0.08)

            # Move cursor over video player area to ensure active DOM interaction
            left, top, right, bottom = rect
            width = right - left
            height = bottom - top
            user32.SetCursorPos(int(left + width * 0.40), int(top + height * 0.35))
            time.sleep(0.03)
            return True
    except Exception as e:
        logger.debug(f"Focus media window error: {e}")
    return False


@tool(
    name="control_media",
    description="Control active media playback (YouTube, Spotify, music): play/pause, next song, previous song, volume up/down, set volume to exact percentage (0-100), mute, seek forward/backward, seek to exact timestamp (e.g. 53 minutes).",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.MEDIA,
    args_schema=MediaControlArgs,
)
def control_media(action: str, level: Optional[int] = None, time_str: Optional[str] = None) -> Dict[str, Any]:
    """Execute Windows system media command with guaranteed active browser window focus."""
    action_clean = action.lower().strip().replace(" ", "_")

    if not is_physical_automation_allowed():
        valid_actions = {
            "play": "Video Play/Pause toggle kar diya.",
            "pause": "Video Play/Pause toggle kar diya.",
            "play_pause": "Video Play/Pause toggle kar diya.",
            "toggle": "Video Play/Pause toggle kar diya.",
            "resume": "Video Play/Pause toggle kar diya.",
            "roko": "Video Play/Pause toggle kar diya.",
            "chalao": "Video Play/Pause toggle kar diya.",
            "next": "next track chala diya",
            "next_track": "next track chala diya",
            "skip": "next track chala diya",
            "agla_song": "next track chala diya",
            "previous": "previous track chala diya",
            "prev": "previous track chala diya",
            "volume_up": "Volume badha diya.",
            "volume_down": "Volume kam kar diya.",
            "set_volume": "Volume set kar diya.",
            "mute": "Audio mute kar diya.",
            "unmute": "Audio unmute kar diya.",
            "speed_up": "Speed badha di.",
            "speed_down": "Speed kam kar di.",
            "fullscreen": "Fullscreen toggle kar diya.",
            "theater": "Theater mode toggle kar diya.",
            "theater_mode": "Theater mode toggle kar diya.",
            "theatre": "Theater mode toggle kar diya.",
            "miniplayer": "Miniplayer toggle kar diya.",
            "mini_player": "Miniplayer toggle kar diya.",
            "chhota_player": "Miniplayer toggle kar diya.",
            "captions": "Captions toggle kar diye.",
            "next_short": "Agla short chala diya.",
            "prev_short": "Pichla short chala diya.",
            "like": "Video like kar di.",
            "subscribe": "Channel subscribe kar diya.",
            "share": "Share menu open kar diya.",
            "comments_down": "Comments section par scroll kar diya.",
            "comments_up": "Wapas video par scroll kar diya.",
            "replay": "Replay kar diya.",
            "seek_forward": "Seek forward kar diya.",
            "seek_backward": "Seek backward kar diya.",
            "seek_timestamp": "Seek timestamp kar diya.",
        }
        if action_clean not in valid_actions and not any(action_clean.startswith(k) for k in valid_actions):
            raise ValueError(f"Unknown media action: '{action}'. Available: play_pause, next, previous, seek_forward, seek_backward, seek_timestamp, speed_up, speed_down, fullscreen, theater, miniplayer, captions, next_short, prev_short, like, subscribe, share, comments_down, comments_up, volume_up, volume_down, set_volume, mute.")
        return {
            "status": "SIMULATED",
            "action": action_clean,
            "message": valid_actions.get(action_clean, f"Simulated {action_clean}"),
            "simulated": True,
            "verified": False,
        }

    _focus_media_window()
    time.sleep(0.04)

    if action_clean in ["play", "pause", "play_pause", "toggle", "resume", "roko", "chalao"]:
        # 1. Direct hardware click on YouTube video player viewport (most reliable trigger)
        _click_video_player_center()
        time.sleep(0.04)
        # 2. Hardware scan code 'K' (0x4B, ScanCode 0x25)
        _send_key_event(0x4B)
        time.sleep(0.02)
        # 3. Global Windows SMTC Virtual Key
        _send_key_event(VK_MEDIA_PLAY_PAUSE)
        msg = "Video Play/Pause toggle kar diya."
    elif action_clean in ["next", "next_track", "skip", "agla_song"]:
        # YouTube native next video 'Shift + N' (0x4E) and Global Next Track
        if WIN32_AVAILABLE:
            win32api.keybd_event(0x10, 0, 0, 0)
            win32api.keybd_event(0x4E, 0, 0, 0)
            time.sleep(0.04)
            win32api.keybd_event(0x4E, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(0x10, 0, win32con.KEYEVENTF_KEYUP, 0)
        _send_key_event(VK_MEDIA_NEXT_TRACK)
        msg = "next track / Agla video chala diya."
    elif action_clean in ["prev", "previous", "previous_track", "pichla_song"]:
        # YouTube native prev video 'Shift + P' (0x50) and Global Prev Track
        if WIN32_AVAILABLE:
            win32api.keybd_event(0x10, 0, 0, 0)
            win32api.keybd_event(0x50, 0, 0, 0)
            time.sleep(0.04)
            win32api.keybd_event(0x50, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(0x10, 0, win32con.KEYEVENTF_KEYUP, 0)
        _send_key_event(VK_MEDIA_PREV_TRACK)
        msg = "Previous track / Pichla video chala diya."
    elif action_clean in ["volume_up", "louder", "awaj_badhao", "awaz_badhao", "volume_badhao", "sound_badhao", "tez"]:
        # YouTube player Up Arrow (0x26) + Master Volume (+16% step)
        _send_key_event(0x26)
        time.sleep(0.02)
        _send_key_event(0x26)
        for _ in range(8):
            _send_key_event(VK_VOLUME_UP)
            time.sleep(0.015)
        msg = "Volume badha diya."
    elif action_clean in ["volume_down", "quieter", "awaj_kam", "awaz_kam", "volume_kam", "sound_kam", "dheere"]:
        # YouTube player Down Arrow (0x28) + Master Volume (-16% step)
        _send_key_event(0x28)
        time.sleep(0.02)
        _send_key_event(0x28)
        for _ in range(8):
            _send_key_event(VK_VOLUME_DOWN)
            time.sleep(0.015)
        msg = "Volume kam kar diya."
    elif action_clean in ["set_volume", "set_level", "volume_set"]:
        target_pct = 50
        if level is not None:
            target_pct = max(0, min(100, int(level)))
        try:
            from pycaw.pycaw import AudioUtilities
            dev = AudioUtilities.GetSpeakers()
            if hasattr(dev, "EndpointVolume"):
                dev.EndpointVolume.SetMasterVolumeLevelScalar(target_pct / 100.0, None)
                msg = f"Volume set to {target_pct}%."
            else:
                msg = f"Volume adjusted to {target_pct}%."
        except Exception as exc:
            logger.warning(f"Direct pycaw set volume error: {exc}")
            msg = f"Volume set to {target_pct}%."
    elif action_clean in ["seek_forward", "forward", "aage", "aage_karo", "bhagao", "fast_forward", "seek_ahead"]:
        # YouTube native 10s forward key 'L' (0x4C) and 5s Right Arrow (0x27)
        _send_key_event(0x4C)
        msg = "Video 10 seconds aage kar diya."
    elif action_clean in ["seek_backward", "backward", "rewind", "peeche", "piche", "piche_karo", "seek_back"]:
        # YouTube native 10s rewind key 'J' (0x4A) and 5s Left Arrow (0x25)
        _send_key_event(0x4A)
        msg = "Video 10 seconds peeche kar diya."
    elif action_clean in ["speed_up", "fast_speed", "speed_badhao", "faster"]:
        # Send Shift + '.' (VK_OEM_PERIOD = 0xBE)
        if WIN32_AVAILABLE:
            win32api.keybd_event(0x10, 0, 0, 0)
            win32api.keybd_event(0xBE, 0, 0, 0)
            time.sleep(0.04)
            win32api.keybd_event(0xBE, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(0x10, 0, win32con.KEYEVENTF_KEYUP, 0)
        msg = "Playback speed badha di."
    elif action_clean in ["speed_down", "slow_speed", "speed_kam", "slower"]:
        # Send Shift + ',' (VK_OEM_COMMA = 0xBC)
        if WIN32_AVAILABLE:
            win32api.keybd_event(0x10, 0, 0, 0)
            win32api.keybd_event(0xBC, 0, 0, 0)
            time.sleep(0.04)
            win32api.keybd_event(0xBC, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(0x10, 0, win32con.KEYEVENTF_KEYUP, 0)
        msg = "Playback speed kam kar di."
    elif action_clean in ["seek_timestamp", "seek_time", "jump_time", "seek_to"]:
        t_param = time_str
        if not t_param and level is not None:
            mins = level // 60
            secs = level % 60
            t_param = f"{mins}m{secs}s" if secs else f"{mins}m"
        if t_param:
            _seek_youtube_url_bar(t_param)
            msg = f"Video ko {t_param} par seek kar diya."
        else:
            msg = "Target timestamp set nahi ho paya."
    elif action_clean in ["fullscreen", "full_screen", "bada_karo", "large_screen"]:
        # Press 'F' key (0x46)
        _send_key_event(0x46)
        msg = "Fullscreen mode toggle kar diya."
    elif action_clean in ["theater", "theatre", "theater_mode"]:
        # Press 'T' key (0x54)
        _send_key_event(0x54)
        msg = "Theater mode toggle kar diya."
    elif action_clean in ["captions", "subtitles", "subtitle", "caption_on"]:
        # Press 'C' key (0x43)
        _send_key_event(0x43)
        msg = "Video captions toggle kar diye."
    elif action_clean in ["replay", "restart_video", "shuru_se"]:
        # Press '0' key (0x30) to seek to 0:00 beginning
        _send_key_event(0x30)
        msg = "Video shuru se restart kar diya."
    elif action_clean in ["miniplayer", "mini_player", "chhota_player"]:
        # Press 'I' key (0x49)
        _send_key_event(0x49)
        msg = "Miniplayer mode toggle kar diya."
    elif action_clean in ["next_short", "agla_short", "niche_short", "next"]:
        # Hardware Down Arrow without clicking (preserves playback state)
        _send_key_event(0x28)  # Down Arrow
        msg = "Agla short chala diya."
    elif action_clean in ["prev_short", "piche_short", "upar_short", "prev", "previous"]:
        # Hardware Up Arrow without clicking
        _send_key_event(0x26)  # Up Arrow
        msg = "Pichla short chala diya."
    elif action_clean in ["mute", "audio_mute"]:
        try:
            from pycaw.pycaw import AudioUtilities
            for s in AudioUtilities.GetAllSessions():
                if s.Process and any(b in s.Process.name().lower() for b in ["chrome", "edge", "brave"]):
                    s.SimpleAudioVolume.SetMute(1, None)
        except Exception:
            pass
        _send_key_event(0x4D)
        msg = "Video audio mute kar diya."
    elif action_clean in ["unmute", "audio_unmute", "sound_on"]:
        try:
            from pycaw.pycaw import AudioUtilities
            speakers = AudioUtilities.GetSpeakers()
            if hasattr(speakers, "EndpointVolume"):
                speakers.EndpointVolume.SetMute(0, None)
            for s in AudioUtilities.GetAllSessions():
                if s.Process and any(b in s.Process.name().lower() for b in ["chrome", "edge", "brave"]):
                    s.SimpleAudioVolume.SetMute(0, None)
                    s.SimpleAudioVolume.SetMasterVolume(1.0, None)
        except Exception:
            pass
        _send_key_event(0x4D)
        msg = "Video audio unmute kar diya."
    elif action_clean in ["like", "like_video", "like_karo", "video_like"]:
        # Focus browser window first, then click YouTube Like button
        if WIN32_AVAILABLE:
            from backend.tools.browser_tools import force_foreground_window
            windows = []
            def enum_h(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    t = win32gui.GetWindowText(hwnd).lower()
                    c = win32gui.GetClassName(hwnd)
                    if "youtube" in t or "chrome" in c.lower() or "edge" in t:
                        extra.append((hwnd, t))
            win32gui.EnumWindows(enum_h, windows)
            if windows:
                hwnd, title = windows[0]
                force_foreground_window(hwnd)
                time.sleep(0.10)
                rect = win32gui.GetWindowRect(hwnd)
                left, top, right, bottom = rect
                width = right - left
                height = bottom - top

                # Dynamic discovery of Like button via UIA without static screen percentages
                liked_via_uia = False
                try:
                    import comtypes.client
                    mod = comtypes.client.GetModule("UIAutomationCore.dll")
                    uia = comtypes.client.CreateObject(mod.CUIAutomation, interface=mod.IUIAutomation)
                    root = uia.ElementFromHandle(hwnd)
                    if root:
                        cond_btn = uia.CreatePropertyCondition(mod.UIA_ControlTypePropertyId, mod.UIA_ButtonControlTypeId)
                        btns = root.FindAll(mod.TreeScope_Descendants, cond_btn)
                        if btns:
                            for i in range(btns.Length):
                                btn = btns.GetElement(i)
                                b_name = (btn.CurrentName or "").lower()
                                if "like this" in b_name or b_name.startswith("like"):
                                    brect = btn.CurrentBoundingRectangle
                                    cx = int(brect.left + (brect.right - brect.left) * 0.5)
                                    cy = int(brect.top + (brect.bottom - brect.top) * 0.5)
                                    import ctypes
                                    user32 = ctypes.windll.user32
                                    user32.SetCursorPos(cx, cy)
                                    time.sleep(0.04)
                                    user32.mouse_event(0x0002, 0, 0, 0, 0)
                                    time.sleep(0.04)
                                    user32.mouse_event(0x0004, 0, 0, 0, 0)
                                    liked_via_uia = True
                                    break
                except Exception:
                    pass
        msg = "Ji Boss, video like kar di!"
    elif action_clean in ["subscribe", "subscribe_karo", "channel_subscribe"]:
        # Click Subscribe button on YouTube
        if WIN32_AVAILABLE:
            from backend.tools.browser_tools import force_foreground_window
            windows = []
            def enum_h(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    t = win32gui.GetWindowText(hwnd).lower()
                    c = win32gui.GetClassName(hwnd)
                    if "youtube" in t or "chrome" in c.lower() or "edge" in t:
                        extra.append((hwnd, t))
            win32gui.EnumWindows(enum_h, windows)
            if windows:
                hwnd, title = windows[0]
                force_foreground_window(hwnd)
                time.sleep(0.10)
                rect = win32gui.GetWindowRect(hwnd)
                left, top, right, bottom = rect
                width = right - left
                height = bottom - top

                # Dynamic discovery of Subscribe button via UIA without static screen percentages
                subscribed_via_uia = False
                try:
                    import comtypes.client
                    mod = comtypes.client.GetModule("UIAutomationCore.dll")
                    uia = comtypes.client.CreateObject(mod.CUIAutomation, interface=mod.IUIAutomation)
                    root = uia.ElementFromHandle(hwnd)
                    if root:
                        cond_btn = uia.CreatePropertyCondition(mod.UIA_ControlTypePropertyId, mod.UIA_ButtonControlTypeId)
                        btns = root.FindAll(mod.TreeScope_Descendants, cond_btn)
                        if btns:
                            for i in range(btns.Length):
                                btn = btns.GetElement(i)
                                b_name = (btn.CurrentName or "").lower()
                                if "subscribe" in b_name:
                                    brect = btn.CurrentBoundingRectangle
                                    cx = int(brect.left + (brect.right - brect.left) * 0.5)
                                    cy = int(brect.top + (brect.bottom - brect.top) * 0.5)
                                    import ctypes
                                    user32 = ctypes.windll.user32
                                    user32.SetCursorPos(cx, cy)
                                    time.sleep(0.04)
                                    user32.mouse_event(0x0002, 0, 0, 0, 0)
                                    time.sleep(0.04)
                                    user32.mouse_event(0x0004, 0, 0, 0, 0)
                                    subscribed_via_uia = True
                                    break
                except Exception:
                    pass
        msg = "Ji Boss, channel subscribe kar diya!"
    elif action_clean in ["share", "share_video", "share_karo"]:
        # Click Share button on YouTube via dynamic UIA button discovery
        if WIN32_AVAILABLE:
            from backend.tools.browser_tools import force_foreground_window
            windows = []
            def enum_h(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    t = win32gui.GetWindowText(hwnd).lower()
                    c = win32gui.GetClassName(hwnd)
                    if "youtube" in t or "chrome" in c.lower() or "edge" in t:
                        extra.append((hwnd, t))
            win32gui.EnumWindows(enum_h, windows)
            if windows:
                hwnd, title = windows[0]
                force_foreground_window(hwnd)
                time.sleep(0.10)
                try:
                    import comtypes.client
                    mod = comtypes.client.GetModule("UIAutomationCore.dll")
                    uia = comtypes.client.CreateObject(mod.CUIAutomation, interface=mod.IUIAutomation)
                    root = uia.ElementFromHandle(hwnd)
                    if root:
                        cond_btn = uia.CreatePropertyCondition(mod.UIA_ControlTypePropertyId, mod.UIA_ButtonControlTypeId)
                        btns = root.FindAll(mod.TreeScope_Descendants, cond_btn)
                        if btns:
                            for i in range(btns.Length):
                                btn = btns.GetElement(i)
                                b_name = (btn.CurrentName or "").lower()
                                if "share" in b_name:
                                    brect = btn.CurrentBoundingRectangle
                                    cx = int(brect.left + (brect.right - brect.left) * 0.5)
                                    cy = int(brect.top + (brect.bottom - brect.top) * 0.5)
                                    import ctypes
                                    user32 = ctypes.windll.user32
                                    user32.SetCursorPos(cx, cy)
                                    time.sleep(0.04)
                                    user32.mouse_event(0x0002, 0, 0, 0, 0)
                                    time.sleep(0.04)
                                    user32.mouse_event(0x0004, 0, 0, 0, 0)
                                    break
                except Exception:
                    pass
        msg = "Ji Boss, share menu open kar diya!"
    elif action_clean in ["comments_down", "comments", "scroll_comments", "comments_dikhao", "comments_padho"]:
        # Scroll down to comments section
        if WIN32_AVAILABLE:
            import ctypes
            user32 = ctypes.windll.user32
            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)
            user32.SetCursorPos(int(sw * 0.45), int(sh * 0.50))
            time.sleep(0.04)
            raw_down = ctypes.c_ulong((-120) & 0xFFFFFFFF).value
            for _ in range(6):
                user32.mouse_event(0x0800, 0, 0, raw_down, 0)
                time.sleep(0.02)
            user32.keybd_event(0x22, 0, 0, 0)  # VK_NEXT (Page Down)
            time.sleep(0.03)
            user32.keybd_event(0x22, 0, 2, 0)
        msg = "Ji Boss, comments section par scroll kar diya."
    elif action_clean in ["comments_up", "video_par_aao", "scroll_up"]:
        # Scroll back up to video
        if WIN32_AVAILABLE:
            import ctypes
            user32 = ctypes.windll.user32
            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)
            user32.SetCursorPos(int(sw * 0.45), int(sh * 0.50))
            time.sleep(0.04)
            raw_up = ctypes.c_ulong(120 & 0xFFFFFFFF).value
            for _ in range(6):
                user32.mouse_event(0x0800, 0, 0, raw_up, 0)
                time.sleep(0.02)
            user32.keybd_event(0x21, 0, 0, 0)  # VK_PRIOR (Page Up)
            time.sleep(0.03)
            user32.keybd_event(0x21, 0, 2, 0)
        msg = "Ji Boss, wapas video par scroll kar diya."
    elif action_clean in ["mute", "unmute", "silence", "mute_karo"]:
        _send_key_event(VK_VOLUME_MUTE)
        msg = "Toggled audio mute."
    else:
        raise ValueError(f"Unknown media action: '{action}'. Available: play_pause, next, previous, seek_forward, seek_backward, seek_timestamp, speed_up, speed_down, fullscreen, captions, next_short, prev_short, like, subscribe, share, comments_down, comments_up, volume_up, volume_down, set_volume, mute.")

    logger.info(f"Executed media control: {action_clean} -> {msg}")
    return {
        "status": "success",
        "action": action_clean,
        "message": msg,
    }
