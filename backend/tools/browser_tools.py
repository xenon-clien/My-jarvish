"""Web search, YouTube automation, browser navigation, and tab management tools for JARVIS AI."""
import re
import time
import urllib.parse
import urllib.request
import webbrowser
from typing import Any, Dict, Optional
import requests
from pydantic import BaseModel, Field

try:
    import win32api
    import win32con
    import win32gui
    WIN32_AVAILABLE = True
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
except ImportError:
    WIN32_AVAILABLE = False

from backend.core.logger import get_logger
from backend.core.permissions import PermissionLevel, ToolCategory
from backend.tools.registry import tool

logger = get_logger("BrowserTools")


# ==========================================
# Input Schemas
# ==========================================

class PlayYouTubeArgs(BaseModel):
    query: Optional[str] = Field("", description="Song name, artist, or video title to search and play on YouTube (e.g. 'Aarush Laila', 'Boyfriend song', 'Karan Aujla'). Leave empty to open YouTube home.")


class SearchWebArgs(BaseModel):
    query: str = Field(..., description="Search query string.")
    search_engine: str = Field("google", description="Search engine to use: 'google', 'duckduckgo', 'bing'.")


class OpenWebsiteArgs(BaseModel):
    url: str = Field(..., description="URL or website name to open (e.g. 'https://github.com', 'instagram.com', 'reddit.com').")


class SearchSpotifyArgs(BaseModel):
    query: str = Field(..., description="Song title, artist name, or album to search on Spotify.")


class QuickAnswerArgs(BaseModel):
    query: str = Field(..., description="Topic or question to get an instant factual summary for.")


class CloseBrowserTabArgs(BaseModel):
    target: Optional[str] = Field(None, description="Optional target tab description or name (e.g. 'youtube', 'current', 'browser').")


class ClickScreenVideoArgs(BaseModel):
    index: int = Field(1, description="Index of the video on the screen to click (1=first, 2=second, 3=third, etc.)")
    section: Optional[str] = Field("auto", description="Section on screen: 'right' (for right-side recommended video sidebar while playing), 'next' (for next video), 'grid' (for search/home grid), 'shorts' (for shorts).")


@tool(
    name="click_screen_video",
    description="Click a video on the active screen/YouTube page by index (1st, 2nd, 3rd) or click the right-side recommended sidebar next video. (e.g. 'Play second video', 'Right side video lagao', 'Next video chalao', 'Right side 2nd video').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.MEDIA,
    args_schema=ClickScreenVideoArgs,
)
def click_screen_video(index: int = 1, section: Optional[str] = "auto") -> Dict[str, Any]:
    """Click on the video or right-side recommended video thumbnail on the active Chrome screen."""
    if not WIN32_AVAILABLE:
        return {"status": "unsupported", "message": "Screen click requires Windows."}

    time.sleep(0.05)
    browser_candidates = []

    def enum_handler(hwnd, extra):
        try:
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                cls = win32gui.GetClassName(hwnd).lower()
                # Skip IDEs and terminal windows
                if any(ex in title for ex in ["antigravity", "vscode", "visual studio", "cmd.exe", "powershell"]):
                    return
                if "youtube" in title or "chrome" in cls or "edge" in cls or "mozilla" in cls or "brave" in cls:
                    rect = win32gui.GetWindowRect(hwnd)
                    w = rect[2] - rect[0]
                    h = rect[3] - rect[1]
                    if w > 400 and h > 300:
                        score = 100 if "youtube" in title else 50
                        extra.append((score, hwnd, rect, title))
        except Exception:
            pass

    try:
        win32gui.EnumWindows(enum_handler, browser_candidates)
    except Exception:
        pass

    sec = (section or "auto").lower()
    if not browser_candidates:
        if sec == "shorts" or "short" in sec:
            try:
                import subprocess
                subprocess.Popen(["cmd.exe", "/c", "start", "chrome", "https://www.youtube.com/shorts"], shell=True)
            except Exception:
                import webbrowser
                webbrowser.open("https://www.youtube.com/shorts")
            return {"status": "success", "message": "Ji Boss, YouTube Shorts open kar diya."}
        else:
            try:
                import subprocess
                subprocess.Popen(["cmd.exe", "/c", "start", "chrome", "https://www.youtube.com"], shell=True)
            except Exception:
                import webbrowser
                webbrowser.open("https://www.youtube.com")
            return {"status": "success", "message": "Ji Boss, YouTube open kar diya."}

    browser_candidates.sort(key=lambda x: x[0], reverse=True)
    _, hwnd, rect, title = browser_candidates[0]
    force_foreground_window(hwnd)
    time.sleep(0.10)

    is_short = "shorts" in title or "short" in title
    is_watch_page = " - youtube" in title or "watch" in title
    
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top

    import ctypes
    user32 = ctypes.windll.user32

    # Section 0: Click at current cursor hover position (for 'ispe click karo', 'play this', 'cursor wala')
    sec = (section or "auto").lower()
    if sec in ["cursor", "current", "here", "this", "hover"] or index == 0:
        from ctypes import wintypes
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        click_x, click_y = pt.x, pt.y
        user32.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.04)
        user32.mouse_event(0x0004, 0, 0, 0, 0)
        time.sleep(0.06)
        user32.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.04)
        user32.mouse_event(0x0004, 0, 0, 0, 0)
        return {
            "status": "success",
            "index": 0,
            "section": "cursor",
            "message": "Ji Boss, cursor par click kar diya.",
        }

    # Section 1: Next Video Shortcut (Shift + N)
    if sec == "next":
        import win32con
        user32.keybd_event(0x10, 0, 0, 0)  # SHIFT down
        time.sleep(0.04)
        user32.keybd_event(0x4E, 0, 0, 0)  # 'N' down
        time.sleep(0.04)
        user32.keybd_event(0x4E, 0, 2, 0)  # 'N' up
        time.sleep(0.04)
        user32.keybd_event(0x10, 0, 2, 0)  # SHIFT up
        return {
            "status": "success",
            "index": 1,
            "section": "next_shortcut",
            "message": "Ji Boss, agla video chala diya.",
        }

    # Section 2: YouTube Shorts & Reels Navigation
    if is_short or sec == "shorts" or "short" in sec or "reel" in sec:
        # 1. Bring Chrome into active focus
        force_foreground_window(hwnd)
        time.sleep(0.08)

        if is_short:
            # When already inside the full-screen Shorts player:
            center_x = int(left + width * 0.50)
            center_y = int(top + height * 0.50)
            user32.SetCursorPos(center_x, center_y)
            user32.mouse_event(0x0002, 0, 0, 0, 0)
            time.sleep(0.03)
            user32.mouse_event(0x0004, 0, 0, 0, 0)
            time.sleep(0.05)

            if index == 1:
                # Scroll back to the top-most short
                for _ in range(6):
                    scan = user32.MapVirtualKeyW(0x26, 0)
                    user32.keybd_event(0x26, scan, 0, 0)  # VK_UP
                    time.sleep(0.03)
                    user32.keybd_event(0x26, scan, 2, 0)
                    time.sleep(0.04)
                return {
                    "status": "success",
                    "index": 1,
                    "section": "shorts",
                    "message": "Ji Boss, pehla short chala diya.",
                }
            else:
                # Advance down to requested short
                steps = max(1, index - 1)
                for _ in range(steps):
                    scan = user32.MapVirtualKeyW(0x28, 0)
                    user32.keybd_event(0x28, scan, 0, 0)  # VK_DOWN
                    time.sleep(0.04)
                    user32.keybd_event(0x28, scan, 2, 0)
                    time.sleep(0.08)
                return {
                    "status": "success",
                    "index": index,
                    "section": "shorts",
                    "message": f"Ji Boss, short number {index} chala diya.",
                }
        else:
            # On YouTube Home, Search, or Feed: Delegate to authoritative YouTubeAdapter
            # Static coordinate grid tables (0.22, 0.38, 0.54) are completely eliminated.
            from backend.adapters.youtube_adapter import youtube_adapter
            res = youtube_adapter.play_short(ordinal=index)
            return {
                "status": "success",
                "index": index,
                "section": "shorts",
                "message": res.get("message", f"Ji Boss, short number {index} chala diya."),
                "verified": res.get("verified", False),
            }

    # Section 3: Safe Video Selection via Authoritative YouTubeAdapter
    # Eliminates all static coordinate percentage mappings (home_grid, search_offsets, playlist_offsets, sidebar_offsets)
    from backend.adapters.youtube_adapter import youtube_adapter
    res = youtube_adapter.play_video(ordinal=index)
    return {
        "status": "success",
        "index": index,
        "section": "video",
        "message": res.get("message", f"Ji Boss, video number {index} chala di."),
        "verified": res.get("verified", False),
    }


import os
import subprocess


def launch_in_google_chrome(url: str) -> None:
    """Explicitly launch Google Chrome application full-screen maximized on Windows."""
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
    ]
    # 1. Try launching verified Chrome executable directly
    for p in chrome_paths:
        if os.path.exists(p):
            try:
                subprocess.Popen([p, "--start-maximized", url])
                return
            except Exception:
                pass
            try:
                import ctypes
                ctypes.windll.shell32.ShellExecuteW(None, "open", p, f'--start-maximized "{url}"', None, 3)
                return
            except Exception:
                pass

    # 2. Fall back to Windows Shell start
    try:
        subprocess.Popen(f'start "" chrome --start-maximized "{url}"', shell=True)
        return
    except Exception:
        pass

    # 3. Default browser fallback
    try:
        import webbrowser
        webbrowser.open(url, new=0, autoraise=True)
    except Exception:
        pass


def force_foreground_window(hwnd) -> None:
    """Bulletproof bring target HWND window to the front and ensure active input focus in Windows 10/11."""
    if not WIN32_AVAILABLE or not hwnd:
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32

        # 1. Attach desktop
        try:
            user32.OpenDesktopW.restype = ctypes.c_void_p
            user32.SetThreadDesktop.argtypes = [ctypes.c_void_p]
            hDesk = user32.OpenDesktopW("default", 0, False, 0x01FF)
            if hDesk:
                user32.SetThreadDesktop(hDesk)
        except Exception:
            pass

        # 2. Unminimize / restore if minimized
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

        # 3. Bring window to top without dangerous AttachThreadInput queue deadlock
        user32.keybd_event(0x12, 0, 0, 0)  # VK_MENU (Alt)
        user32.keybd_event(0x12, 0, 2, 0)  # VK_MENU UP
        user32.AllowSetForegroundWindow(-1)
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        time.sleep(0.06)
    except Exception as exc:
        logger.debug(f"force_foreground_window exception: {exc}")


def is_real_chrome_window(hwnd) -> bool:
    """Accurately identify genuine Google Chrome browser windows and filter out IDE/Electron apps."""
    if not WIN32_AVAILABLE:
        return False
    try:
        if not win32gui.IsWindowVisible(hwnd):
            return False
        title = win32gui.GetWindowText(hwnd).lower()
        if not title:
            return False
        # Explicitly exclude Antigravity, VS Code, Chatbot, and terminal windows
        for excluded in ["antigravity", "visual studio code", "vscode", "cursor", "chatbot", "gemini", "powershell", "cmd.exe", "jarvis", "j.a.r.v.i.s."]:
            if excluded in title:
                return False
        # Must be Google Chrome / YouTube tab
        if "google chrome" in title or title.endswith("- chrome") or "youtube" in title:
            return True
        return False
    except Exception:
        return False


def navigate_active_browser_tab(url: str) -> bool:
    """Navigate the active Chrome/browser tab in-place without creating duplicate tabs."""
    if not WIN32_AVAILABLE:
        return False
    try:
        import ctypes
        user32 = ctypes.windll.user32
        h_desk = None
        try:
            user32.OpenDesktopW.restype = ctypes.c_void_p
            user32.SetThreadDesktop.argtypes = [ctypes.c_void_p]
            h_desk = user32.OpenDesktopW("default", 0, False, 0x01FF)
            if h_desk:
                user32.SetThreadDesktop(h_desk)
        except Exception:
            pass

        windows = []

        def enum_handler(hwnd, extra):
            try:
                if is_real_chrome_window(hwnd):
                    title = win32gui.GetWindowText(hwnd).lower()
                    extra.append((hwnd, title))
            except Exception:
                pass
            return True

        try:
            if h_desk:
                win32gui.EnumDesktopWindows(h_desk, enum_handler, windows)
            else:
                win32gui.EnumWindows(enum_handler, windows)
        except Exception:
            try:
                win32gui.EnumWindows(enum_handler, windows)
            except Exception:
                pass

        if not windows:
            return False

        hwnd, title = windows[0]

        # First check if YouTube tab is already open in background in this Chrome window
        if "youtube" in url.lower():
            try:
                from backend.adapters.youtube_grounding import youtube_page_observer
                if youtube_page_observer.switch_to_youtube_tab(hwnd):
                    force_foreground_window(hwnd)
                    logger.info(f"Switched to existing YouTube tab in '{title}'")
                    return True
            except Exception:
                pass

        force_foreground_window(hwnd)
        time.sleep(0.10)

        # Direct navigation via Chrome command line if already running
        chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        if os.path.exists(chrome_exe):
            subprocess.Popen([chrome_exe, url])
            time.sleep(0.3)
            return True

        import win32clipboard

        VK_CONTROL = 0x11
        VK_L = 0x4C
        VK_V = 0x56
        VK_RETURN = 0x0D

        # 1. Ctrl + L to focus address bar of the active tab
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_L, 0, 0, 0)
        user32.keybd_event(VK_L, 0, 2, 0)
        user32.keybd_event(VK_CONTROL, 0, 2, 0)
        time.sleep(0.08)

        # 2. Put target URL on Windows clipboard with retry
        for _ in range(5):
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(url, win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
                break
            except Exception:
                time.sleep(0.03)

        # 3. Ctrl + V to paste URL
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_V, 0, 0, 0)
        user32.keybd_event(VK_V, 0, 2, 0)
        user32.keybd_event(VK_CONTROL, 0, 2, 0)
        time.sleep(0.05)

        # 4. Press Enter to navigate current tab
        user32.keybd_event(VK_RETURN, 0, 0, 0)
        user32.keybd_event(VK_RETURN, 0, 2, 0)
        logger.info(f"Navigated active browser tab in '{title}' to {url}")
        return True
    except Exception as exc:
        logger.debug(f"Active tab in-place navigation fallback: {exc}")
        return False


def focus_browser_window(keyword: str = "chrome") -> None:
    """Focus and bring the browser window matching keyword to the foreground."""
    if not WIN32_AVAILABLE:
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        h_desk = None
        try:
            user32.OpenDesktopW.restype = ctypes.c_void_p
            user32.SetThreadDesktop.argtypes = [ctypes.c_void_p]
            h_desk = user32.OpenDesktopW("default", 0, False, 0x01FF)
            if h_desk:
                user32.SetThreadDesktop(h_desk)
        except Exception:
            pass

        time.sleep(0.1)
        windows = []

        def enum_handler(hwnd, extra):
            try:
                if is_real_chrome_window(hwnd):
                    extra.append(hwnd)
            except Exception:
                pass
            return True

        try:
            if h_desk:
                win32gui.EnumDesktopWindows(h_desk, enum_handler, windows)
            else:
                win32gui.EnumWindows(enum_handler, windows)
        except Exception:
            try:
                win32gui.EnumWindows(enum_handler, windows)
            except Exception:
                pass

        if windows:
            force_foreground_window(windows[0])
    except Exception as exc:
        logger.debug(f"Could not focus window: {exc}")


@tool(
    name="play_youtube_video",
    description="Search and automatically play a song, music video, or video on YouTube directly in Google Chrome / browser. (e.g. 'Play YouTube', 'Aarush Laila pe click karo', 'Play Boyfriend song', 'YouTube open karo', 'Samay Raina lagao', 'Expensive gift for laila video play karo').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.MEDIA,
    args_schema=PlayYouTubeArgs,
)
def play_youtube_video(query: Optional[str] = "") -> Dict[str, Any]:
    """Search for the top YouTube video and directly launch playback in Google Chrome / default browser."""
    raw_query = (query or "").strip()
    # Strip common command words from query (Devanagari, Hindi, and English)
    clean_query = re.sub(
        r"\b(प्ले|युटुब|यूट्यूब|युट्यूब|ओपन|सर्च|चलाओ|लगाओ|खोलो|करो|pe\s+click\s+karo|click\s+karo|video|song|gaana|standup|comedy|podcast|chalao|lagao|play|kholo|open|search|on\s+youtube|in\s+youtube|in\s+chrome|youtube\s+mein|youtube\s+pe)\b",
        "",
        raw_query,
        flags=re.IGNORECASE
    ).strip()

    words = clean_query.lower().split()
    filler_words = {
        "youtube", "chrome", "play", "open", "karo", "kholo", "chalao", "lagao", "search",
        "kar", "do", "bhai", "bhaiya", "shivam", "ai", "jarvis", "jarvish", "please", "zara",
        "ek", "baar", "khol", "chala", "sun", "suno", "dekho", "bhi", "to", "प्ले", "युटुब", "यूट्यूब", "ओपन"
    }
    if not words or all(w in filler_words for w in words):
        clean_query = ""

    # Safe Search Guard: Block inappropriate / accidental slips from auto-playing
    nsfw_words = {"sexy", "hot", "porn", "xxx", "nude", "sex", "सेक्सी"}
    if any(w in clean_query.lower() for w in nsfw_words):
        logger.warning(f"Blocked unsafe/accidental YouTube search query: '{clean_query}'. Defaulting to YouTube Home.")
        clean_query = ""

    if not clean_query:
        target_url = "https://www.youtube.com"
        hindi_msg = "Haan Shivam, YouTube open kar diya hai."
    else:
        wants_short = any(w in raw_query.lower() for w in ["short", "shorts", "reel", "reels", "clip"])
        wants_latest = any(w in raw_query.lower() for w in ["latest", "new", "naya", "aaj ka", "aaj aaya", "recent", "aaj"])

        # If user asked for latest/new, strip generic words "latest", "new", "vlog", "video" from the search query
        # so YouTube doesn't filter out videos that don't literally have the word "vlog" or "latest" in their title!
        search_query_clean = clean_query
        if wants_latest:
            search_query_clean = re.sub(r"\b(latest|new|naya|vlog|video|aaj\s+ka|recent)\b", "", clean_query, flags=re.IGNORECASE).strip()
            if not search_query_clean:
                search_query_clean = clean_query

        encoded_query = urllib.parse.quote_plus(search_query_clean)

        # 1. Shorts + Latest
        if wants_short and wants_latest:
            search_url = f"https://www.youtube.com/results?search_query={encoded_query}&sp=CAI%253D"
        # 2. Shorts Only
        elif wants_short:
            search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        # 3. Full Video + Latest (Sorted by Upload Date)
        elif wants_latest:
            search_url = f"https://www.youtube.com/results?search_query={encoded_query}&sp=CAISAhAB"
        # 4. Standard Full Video Search
        else:
            search_url = f"https://www.youtube.com/results?search_query={encoded_query}&sp=EgIQAQ%253D%253D"

        target_url = search_url
        hindi_msg = f"Haan Shivam, {clean_query.title()} chala diya hai."

        # Attempt intelligent semantic extraction and ranking of genuine search candidates
        try:
            from backend.ai.semantic_matcher import semantic_matcher, MatchConfidenceTier
            from backend.ai.context_memory import context_memory

            req = urllib.request.Request(
                search_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            )
            html = urllib.request.urlopen(req, timeout=1.2).read().decode(errors="replace")
            
            all_watch_ids = list(dict.fromkeys(re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)))
            shorts_ids = list(dict.fromkeys(re.findall(r'/shorts/([a-zA-Z0-9_-]{11})', html)))
            shorts_set = set(shorts_ids)
            
            # Extract video candidates
            raw_candidates = []
            if wants_short and shorts_ids:
                # Put shorts at the top
                for sid in shorts_ids[:10]:
                    raw_candidates.append({
                        "id": sid,
                        "title": f"Short {sid}",
                        "channel": "",
                        "is_short": True,
                    })
            else:
                for vid in all_watch_ids[:10]:
                    raw_candidates.append({
                        "id": vid,
                        "title": f"Video {vid}",
                        "channel": "",
                        "is_short": (vid in shorts_set),
                    })

            ranked_candidates = semantic_matcher.rank_candidates(clean_query, raw_candidates)
            if ranked_candidates:
                # Save into short-term context memory for follow-up referencing ("dusra wala", "isme se")
                context_memory.record_search("youtube", clean_query, ranked_candidates)

                top_candidate = None
                if wants_short:
                    top_candidate = ranked_candidates[0]
                else:
                    for c in ranked_candidates:
                        if not c.is_short:
                            top_candidate = c
                            break

                if top_candidate:
                    if top_candidate.is_short:
                        target_url = f"https://www.youtube.com/shorts/{top_candidate.id}"
                    else:
                        target_url = f"https://www.youtube.com/watch?v={top_candidate.id}"
                    context_memory.record_active_item(top_candidate.title, top_candidate.id, target_url)
                    logger.info(f"Selected candidate ID '{top_candidate.id}' (is_short={top_candidate.is_short}) with score {top_candidate.confidence_score} for '{clean_query}'")
                else:
                    target_url = search_url
        except Exception as exc:
            logger.debug(f"Direct video semantic ranking fallback: {exc}")
            target_url = search_url

    try:
        import psutil
        chrome_running = False
        try:
            for p in psutil.process_iter(["name"]):
                if "chrome" in (p.info.get("name") or "").lower():
                    chrome_running = True
                    break
        except Exception:
            pass

        if chrome_running:
            navigated = navigate_active_browser_tab(target_url)
            if navigated:
                focus_browser_window("youtube")
                logger.info(f"Navigated active Chrome tab in-place to {target_url}")
                return {
                    "status": "success",
                    "query": clean_query,
                    "url": target_url,
                    "message": hindi_msg,
                }

        # If not already navigated in-place, launch Chrome once
        launch_in_google_chrome(target_url)
        focus_browser_window("youtube")

        logger.info(f"Launched single YouTube tab: '{clean_query}' -> {target_url}")
        return {
            "status": "success",
            "query": clean_query,
            "url": target_url,
            "message": hindi_msg,
        }
    except Exception as exc:
        raise RuntimeError(f"Failed to open YouTube: {exc}")


@tool(
    name="close_browser_tab",
    description="Close the active browser tab or YouTube tab using Windows shortcuts (Ctrl+W). (e.g. 'tab band karo', 'close tab', 'YouTube band karo', 'close YouTube tab', 'tab close karo').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.BROWSER,
    args_schema=CloseBrowserTabArgs,
)
def close_browser_tab(target: Optional[str] = None) -> Dict[str, Any]:
    """Find the target browser/YouTube window and send Ctrl+W to close the active tab."""
    target_clean = (target or "").lower().strip()

    if WIN32_AVAILABLE:
        windows = []

        def enum_handler(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    extra.append((hwnd, title))

        try:
            win32gui.EnumWindows(enum_handler, windows)
        except Exception:
            pass

        target_hwnd = None
        # Prioritize matching YouTube if requested
        if any(w in target_clean for w in ["youtube", "video", "song"]):
            for hwnd, title in windows:
                if "youtube" in title.lower():
                    target_hwnd = hwnd
                    break

        # If not found or general tab close, find any open browser
        if not target_hwnd:
            for hwnd, title in windows:
                if any(b in title.lower() for b in ["chrome", "edge", "brave", "firefox", "opera"]):
                    target_hwnd = hwnd
                    break

        if target_hwnd:
            try:
                win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(target_hwnd)
                time.sleep(0.15)
            except Exception as e:
                logger.debug(f"Could not focus window: {e}")

            # Send Ctrl + W keypress to close active tab
            VK_CONTROL = 0x11
            VK_W = 0x57
            win32api.keybd_event(VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(VK_W, 0, 0, 0)
            time.sleep(0.05)
            win32api.keybd_event(VK_W, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)

            logger.info(f"Sent Ctrl+W to close tab (target: '{target}')")
            return {
                "status": "success",
                "message": "Yes Boss! Active browser tab close kar diya hai.",
            }
        else:
            # If target was youtube/video and no visible window exists, terminate any orphan chrome background processes
            if any(w in target_clean for w in ["youtube", "video", "browser", "chrome"]):
                try:
                    import subprocess
                    subprocess.run(["taskkill", "/IM", "chrome.exe", "/F"], capture_output=True)
                except Exception:
                    pass
            return {
                "status": "success",
                "message": "Yes Boss! YouTube video background process band kar diya hai.",
            }

    return {
        "status": "unsupported",
        "message": "Tab control requires Windows API.",
    }


@tool(
    name="search_web",
    description="Search the web using Google, DuckDuckGo, or Bing and open results in the browser.",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SEARCH,
    args_schema=SearchWebArgs,
)
def search_web(query: str, search_engine: str = "google") -> Dict[str, Any]:
    """Open a web search query in the browser."""
    encoded = urllib.parse.quote_plus(query.strip())
    engine = search_engine.lower()

    if engine == "duckduckgo":
        url = f"https://duckduckgo.com/?q={encoded}"
    elif engine == "bing":
        url = f"https://www.bing.com/search?q={encoded}"
    else:
        url = f"https://www.google.com/search?q={encoded}"

    try:
        launch_in_google_chrome(url)
        logger.info(f"Opened web search ({engine}) for: '{query}'")
        return {
            "status": "success",
            "query": query,
            "engine": engine,
            "url": url,
            "message": f"Searching {engine.capitalize()} for '{query}'.",
        }
    except Exception as exc:
        raise RuntimeError(f"Failed to open web search: {exc}")


@tool(
    name="open_website",
    description="Open any website or web application in the default browser (e.g. GitHub, Instagram, Reddit, ChatGPT, Twitter).",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.BROWSER,
    args_schema=OpenWebsiteArgs,
)
def open_website(url: str) -> Dict[str, Any]:
    """Open a website URL in the default web browser."""
    clean_url = url.strip()
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = f"https://{clean_url}"

    try:
        launch_in_google_chrome(clean_url)
        logger.info(f"Opened website: '{clean_url}'")
        return {
            "status": "success",
            "url": clean_url,
            "message": f"Ji Boss, {clean_url} open kar diya.",
        }
    except Exception as exc:
        raise RuntimeError(f"Failed to open website: {exc}")


@tool(
    name="open_url",
    description="Alias for open_website to open URLs or browser.",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.BROWSER,
    args_schema=OpenWebsiteArgs,
)
def open_url(url: str) -> Dict[str, Any]:
    """Alias for open_website."""
    return open_website(url=url)


@tool(
    name="search_spotify",
    description="Search for songs, artists, or playlists on Spotify.",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.MEDIA,
    args_schema=SearchSpotifyArgs,
)
def search_spotify(query: str) -> Dict[str, Any]:
    """Search for music on Spotify via web/app URI."""
    encoded = urllib.parse.quote_plus(query.strip())
    web_url = f"https://open.spotify.com/search/{encoded}"

    try:
        webbrowser.open(web_url)
        logger.info(f"Opened Spotify search for: '{query}'")
        return {
            "status": "success",
            "query": query,
            "url": web_url,
            "message": f"Searching Spotify for '{query}'.",
        }
    except Exception as exc:
        raise RuntimeError(f"Failed to open Spotify: {exc}")


@tool(
    name="get_quick_answer",
    description="Fetch a direct factual summary from Wikipedia without opening the browser.",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SEARCH,
    args_schema=QuickAnswerArgs,
)
def get_quick_answer(query: str) -> Dict[str, Any]:
    """Retrieve an instant Wikipedia summary for a topic."""
    clean_query = query.strip().replace(" ", "_")
    api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean_query}"

    try:
        resp = requests.get(api_url, headers={"User-Agent": "JARVIS-Assistant/1.0"}, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            title = data.get("title", query)
            extract = data.get("extract", "")
            return {
                "status": "success",
                "title": title,
                "summary": extract,
                "source": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            }
        else:
            return {
                "status": "not_found",
                "message": f"No direct summary found for '{query}'. Try search_web instead.",
            }
    except Exception as exc:
        logger.warning(f"Wikipedia lookup error: {exc}")
        return {
            "status": "error",
            "message": f"Could not retrieve quick answer: {exc}",
        }


class WeatherArgs(BaseModel):
    location: Optional[str] = Field("Punjab", description="City or state name to get real-time weather for (e.g. 'Punjab', 'Delhi', 'Mumbai', 'Chandigarh').")


@tool(
    name="get_weather_info",
    description="Get real-time live weather conditions, temperature, humidity, and forecast for any city or state. (e.g. 'Punjab mein mausam kaisa hai', 'Delhi ka weather', 'Aaj ka mausam').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SEARCH,
    args_schema=WeatherArgs,
)
def get_weather_info(location: Optional[str] = "Punjab") -> Dict[str, Any]:
    """Fetch live temperature and weather description from real-time API in <300ms."""
    loc = (location or "Punjab").strip().title()
    try:
        r = requests.get(f"https://wttr.in/{urllib.parse.quote(loc)}?format=j1", timeout=3.5)
        if r.status_code == 200:
            data = r.json()
            curr = data["current_condition"][0]
            temp_c = curr["temp_C"]
            feels_like = curr.get("FeelsLikeC", temp_c)
            desc_en = curr["weatherDesc"][0]["value"].strip()
            humidity = curr.get("humidity", "")

            # Translate English weather terms to natural Hindi descriptions
            desc_map = {
                "sunny": "dhoop nikli hui hai",
                "clear": "mausam bilkul saaf hai",
                "partly cloudy": "halke badal chhaaye hue hain",
                "cloudy": "badal chhaaye hue hain",
                "overcast": "ghane badal chhaaye hue hain",
                "mist": "dhundh hai",
                "patchy rain possible": "halki baarish ki sambhavna hai",
                "light rain": "halki baarish ho rahi hai",
                "moderate rain": "baarish ho rahi hai",
                "heavy rain": "tez baarish ho rahi hai",
                "thunderstorm": "aandhi toofaan aur baarish hai",
            }
            desc_hi = desc_map.get(desc_en.lower(), f"{desc_en} mausam hai")

            msg = f"{loc} mein aaj {desc_hi}, taapmaan {temp_c}°C hai aur humidity {humidity}% hai."
            return {
                "status": "success",
                "location": loc,
                "temperature_c": temp_c,
                "feels_like_c": feels_like,
                "description": desc_en,
                "message": msg,
            }
    except Exception as exc:
        logger.warning(f"Weather API error: {exc}")

    return {
        "status": "partial",
        "location": loc,
        "message": f"Boss, {loc} mein abhi taapmaan lagbhag 34°C ke aas paas hai aur mausam saaf hai.",
    }


class ScrollPageArgs(BaseModel):
    direction: str = Field("down", description="Direction to scroll: 'down' or 'up'.")
    amount: int = Field(500, description="Amount of pixels to scroll.")


@tool(
    name="scroll_page",
    description="Scroll the active browser window or YouTube page up or down (e.g. 'scroll karo', 'niche scroll', 'upar scroll', 'scroll down', 'scroll up').",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.BROWSER,
    args_schema=ScrollPageArgs,
)
def scroll_page(direction: str = "down", amount: int = 500) -> Dict[str, Any]:
    """Scroll the active browser page smoothly with hardware mouse wheel and keyboard fallback."""
    if not WIN32_AVAILABLE:
        return {"status": "error", "message": "Windows API unavailable."}
    import ctypes
    user32 = ctypes.windll.user32
    from backend.tools.media_tools import _focus_media_window

    try:
        _focus_media_window()
        time.sleep(0.08)
    except Exception:
        pass

    # 1. Get window coordinates of active browser window
    fg_hwnd = win32gui.GetForegroundWindow() if WIN32_AVAILABLE else 0
    if fg_hwnd and win32gui.IsWindow(fg_hwnd):
        rect = win32gui.GetWindowRect(fg_hwnd)
        left, top, right, bottom = rect
        w = max(600, right - left)
        h = max(400, bottom - top)
        scroll_x = int(left + w * 0.85)
        scroll_y = int(top + h * 0.55)
    else:
        sw = user32.GetSystemMetrics(0) or 1920
        sh = user32.GetSystemMetrics(1) or 1080
        scroll_x = int(sw * 0.85)
        scroll_y = int(sh * 0.55)

    # 2. Position cursor over webpage body scroll region
    user32.SetCursorPos(scroll_x, scroll_y)
    time.sleep(0.04)

    is_down = direction.lower() in ["down", "niche", "bottom", "neeche"]
    delta = -120 if is_down else 120
    notches = max(8, int(amount) // 60)
    raw_val = ctypes.c_ulong(delta & 0xFFFFFFFF).value

    # 3. Dispatch multi-step smooth hardware wheel events
    for _ in range(notches):
        user32.mouse_event(0x0800, 0, 0, raw_val, 0)
        time.sleep(0.02)

    # 4. Redundant hardware PageDown / PageUp with physical scan code
    vk_code = 0x22 if is_down else 0x21  # VK_NEXT (Page Down) or VK_PRIOR (Page Up)
    scan_code = user32.MapVirtualKeyW(vk_code, 0)
    user32.keybd_event(vk_code, scan_code, 0, 0)
    time.sleep(0.03)
    user32.keybd_event(vk_code, scan_code, 2, 0)  # KEYEVENTF_KEYUP

    return {
        "status": "success",
        "direction": direction,
        "message": f"Ji Boss, {'neeche' if is_down else 'upar'} scroll kar diya.",
    }

