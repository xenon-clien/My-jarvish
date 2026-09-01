"""JARVIS 3.0 - Canonical Intents.

Defines the standard canonical intent taxonomy. All supported languages
(Hindi, English, Hinglish, Devanagari) resolve to these canonical intents.
"""
from enum import Enum


class CanonicalIntent(str, Enum):
    # YouTube & Video Capabilities
    YOUTUBE_OPEN = "youtube.open"
    YOUTUBE_PLAY_FIRST_SHORT = "youtube.play_first_short"
    YOUTUBE_NEXT_SHORT = "youtube.next_short"
    YOUTUBE_PREV_SHORT = "youtube.prev_short"
    YOUTUBE_SEARCH = "youtube.search"
    YOUTUBE_PLAY = "youtube.play"
    YOUTUBE_PAUSE = "youtube.pause"
    YOUTUBE_RESUME = "youtube.resume"
    YOUTUBE_NEXT = "youtube.next_video"
    YOUTUBE_PREV = "youtube.prev_video"
    YOUTUBE_SEEK_FORWARD = "youtube.seek_forward"
    YOUTUBE_SEEK_BACKWARD = "youtube.seek_backward"
    YOUTUBE_FULLSCREEN = "youtube.fullscreen"
    YOUTUBE_LIKE = "youtube.like"
    YOUTUBE_SUBSCRIBE = "youtube.subscribe"
    YOUTUBE_OPEN_COMMENTS = "youtube.open_comments"
    YOUTUBE_SHARE = "youtube.share"

    # Chrome & Browser Capabilities
    CHROME_OPEN = "chrome.open"
    CHROME_NEW_TAB = "chrome.new_tab"
    CHROME_CLOSE_TAB = "chrome.close_tab"
    CHROME_NEXT_TAB = "chrome.next_tab"
    CHROME_PREV_TAB = "chrome.prev_tab"
    CHROME_REFRESH = "chrome.refresh"
    CHROME_ZOOM_IN = "chrome.zoom_in"
    CHROME_ZOOM_OUT = "chrome.zoom_out"
    CHROME_RESET_ZOOM = "chrome.reset_zoom"
    CHROME_FIND_ON_PAGE = "chrome.find_on_page"
    CHROME_OPEN_INCOGNITO = "chrome.open_incognito"
    CHROME_OPEN_HISTORY = "chrome.open_history"
    CHROME_OPEN_BOOKMARKS = "chrome.open_bookmarks"
    CHROME_OPEN_DOWNLOADS = "chrome.open_downloads"

    # Downloads & Files
    DOWNLOADS_STATUS = "downloads.status"
    DOWNLOADS_LAST = "downloads.last_downloaded"
    DOWNLOADS_OPEN_FOLDER = "downloads.open_folder"

    FILES_OPEN = "files.open"
    FILES_SEARCH = "files.search"
    FILES_FIND_EXT = "files.find_by_extension"
    FILES_FIND_LARGE = "files.find_large"
    FILES_FIND_RECENT = "files.find_recent"
    FILES_SHOW_HIDDEN = "files.show_hidden"
    FILES_HIDE_HIDDEN = "files.hide_hidden"
    FILES_CREATE_FOLDER = "files.create_folder"

    # WhatsApp & Communication
    WHATSAPP_OPEN = "whatsapp.open"
    WHATSAPP_SEND_MESSAGE = "whatsapp.send_message"
    WHATSAPP_VOICE_CALL = "whatsapp.voice_call"
    WHATSAPP_VIDEO_CALL = "whatsapp.video_call"
    WHATSAPP_END_CALL = "whatsapp.end_call"
    WHATSAPP_SEARCH_CONTACT = "whatsapp.search_contact"

    # Generic Desktop Apps
    DESKTOP_OPEN_APP = "desktop.open_app"
    DESKTOP_CLOSE_APP = "desktop.close_app"
    DESKTOP_FOCUS_APP = "desktop.focus_app"
    DESKTOP_MINIMIZE_APP = "desktop.minimize_app"
    DESKTOP_MAXIMIZE_APP = "desktop.maximize_app"
    DESKTOP_APP_STATUS = "desktop.app_status"
    DESKTOP_LIST_APPS = "apps.list"
    DESKTOP_APP_CAPABILITIES = "apps.capabilities"

    # System & Hardware Controls
    SYSTEM_VOLUME_UP = "system.volume_up"
    SYSTEM_VOLUME_DOWN = "system.volume_down"
    SYSTEM_SET_VOLUME = "system.set_volume"
    SYSTEM_MUTE = "system.mute"
    SYSTEM_UNMUTE = "system.unmute"
    SYSTEM_STATUS = "system.status"
    SYSTEM_BATTERY = "system.battery"
    SYSTEM_TIME = "system.time"
    SYSTEM_LOCK = "system.lock"
    SYSTEM_SLEEP = "system.sleep"

    # Diagnostics & Developer
    DIAGNOSTICS_HEALTH_CHECK = "diagnostics.health_check"
    DIAGNOSTICS_RUN = "diagnostics.run"
    DIAGNOSTICS_BUGS = "diagnostics.bugs"

    # Emergency & Control
    SYSTEM_STOP = "system.stop"
    SYSTEM_CANCEL = "system.cancel"

    # Conversational & Complex
    CONVERSATIONAL_CHAT = "ai.chat"
    COMPLEX_PLAN = "ai.plan"
    UNKNOWN = "unknown"
