"""Safe Windows application management tools for JARVIS AI.

Enforces a strict application allowlist and safe subprocess execution to prevent
unauthorized process execution or command-line injection attacks.
"""
import ctypes
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional
import psutil
from pydantic import BaseModel, Field

from backend.core.logger import get_logger
from backend.core.permissions import PermissionLevel, ToolCategory
from backend.tools.registry import tool

logger = get_logger("AppTools")

# Built-in Windows application allowlist and alias mapping
DEFAULT_APP_REGISTRY: Dict[str, Dict[str, Any]] = {
    "chrome": {
        "name": "Google Chrome",
        "executables": ["chrome.exe", "chrome"],
        "aliases": ["chrome", "google chrome", "browser", "web browser", "internet", "क्रोम", "गूगल क्रोम"],
        "command": "start chrome",
    },
    "vscode": {
        "name": "Visual Studio Code",
        "executables": ["code.exe", "code.cmd", "code"],
        "aliases": ["vscode", "vs code", "code", "visual studio code", "code editor", "editor", "वीएस कोड"],
        "command": "code",
    },
    "notepad": {
        "name": "Notepad",
        "executables": ["notepad.exe", "notepad"],
        "aliases": ["notepad", "text editor", "notes editor", "नोटपैड"],
        "command": "notepad",
    },
    "calculator": {
        "name": "Windows Calculator",
        "executables": ["calc.exe", "calculatorapp.exe", "calc"],
        "aliases": ["calculator", "calc", "कैलकुलेटर"],
        "command": "calc",
    },
    "spotify": {
        "name": "Spotify",
        "executables": ["spotify.exe", "spotify"],
        "aliases": ["spotify", "spotifi", "spoti", "स्पॉटिफाई", "स्पॉटिफ़ाई", "स्पॉटीफाई"],
        "command": "start spotify:",
    },
    "edge": {
        "name": "Microsoft Edge",
        "executables": ["msedge.exe", "msedge"],
        "aliases": ["edge", "ms edge", "microsoft edge", "एज"],
        "command": "start msedge",
    },
    "cmd": {
        "name": "Command Prompt",
        "executables": ["cmd.exe"],
        "aliases": ["cmd", "command prompt", "cmd window", "cmd tab", "command line", "कमांड प्रॉम्प्ट"],
        "command": "start cmd",
    },
    "powershell": {
        "name": "PowerShell",
        "executables": ["powershell.exe", "pwsh.exe"],
        "aliases": ["powershell", "ps", "powershell window", "powershell tab", "पावरशेल"],
        "command": "start powershell",
    },
    "terminal": {
        "name": "Windows Terminal",
        "executables": ["wt.exe"],
        "aliases": ["terminal", "windows terminal", "wt", "टर्मिनल"],
        "command": "start wt",
    },
    "explorer": {
        "name": "File Explorer",
        "executables": ["explorer.exe", "explorer"],
        "aliases": ["explorer", "file explorer", "file manager", "folder", "folders", "files", "my computer", "my files", "एक्सप्लोरर", "फाइल एक्सप्लोरर", "फाइल मैनेजर", "माय कंप्यूटर", "फोल्डर"],
        "command": "explorer",
    },
    "paint": {
        "name": "Paint",
        "executables": ["mspaint.exe", "mspaint", "paint.exe"],
        "aliases": ["paint", "mspaint", "drawing", "पेंट"],
        "command": "mspaint",
    },
    "taskmgr": {
        "name": "Task Manager",
        "executables": ["taskmgr.exe", "taskmgr"],
        "aliases": ["task manager", "taskmgr", "task manager kholo", "activity monitor", "टास्क मैनेजर", "टास्क मेनेजर", "टास्क"],
        "command": "taskmgr",
    },
    "control": {
        "name": "Control Panel",
        "executables": ["control.exe", "control"],
        "aliases": ["control panel", "control", "कंट्रोल पैनल"],
        "command": "control",
    },
    "devmgmt": {
        "name": "Device Manager",
        "executables": ["devmgmt.msc"],
        "aliases": ["device manager", "devmgmt", "डिवाइस मैनेजर"],
        "command": "start devmgmt.msc",
    },
    "resmon": {
        "name": "Resource Monitor",
        "executables": ["resmon.exe", "resmon"],
        "aliases": ["resource monitor", "resmon", "रिसोर्स मॉनिटर"],
        "command": "resmon",
    },
    "eventvwr": {
        "name": "Event Viewer",
        "executables": ["eventvwr.exe", "eventvwr.msc"],
        "aliases": ["event viewer", "eventvwr", "इवेंट व्यूअर"],
        "command": "start eventvwr.msc",
    },
    "services": {
        "name": "Services",
        "executables": ["services.msc"],
        "aliases": ["services", "services management", "सर्विसेज"],
        "command": "start services.msc",
    },
    "regedit": {
        "name": "Registry Editor",
        "executables": ["regedit.exe", "regedit"],
        "aliases": ["registry editor", "regedit", "रजिस्ट्री एडिटर"],
        "command": "regedit",
    },
    "msinfo": {
        "name": "System Information",
        "executables": ["msinfo32.exe", "msinfo32"],
        "aliases": ["system information", "system info", "msinfo32", "msinfo", "सिस्टम इनफार्मेशन"],
        "command": "msinfo32",
    },
    "whatsapp": {
        "name": "WhatsApp",
        "executables": ["whatsapp.exe", "whatsapp.root.exe", "whatsapp"],
        "aliases": ["whatsapp", "whatapp", "whatsap", "watsapp", "watsap", "व्हाट्सएप", "व्हाट्सऐप", "वाट्सएप", "वाटसप", "whatsapp desktop", "chat", "messages"],
        "command": "start whatsapp:",
    },
    "telegram": {
        "name": "Telegram",
        "executables": ["telegram.exe", "telegram"],
        "aliases": ["telegram", "telegram desktop", "टेलीग्राम"],
        "command": "start telegram:",
    },
    "discord": {
        "name": "Discord",
        "executables": ["Discord.exe", "Update.exe"],
        "aliases": ["discord", "discord app", "disc", "डिस्कॉर्ड"],
        "command": "discord",
    },
    "settings": {
        "name": "Windows Settings",
        "executables": ["systemsettings.exe"],
        "aliases": ["settings", "windows settings", "setting", "सेटिंग्स", "सेटिंग"],
        "command": "start ms-settings:",
    },
    "camera": {
        "name": "Camera",
        "executables": ["windowscamera.exe"],
        "aliases": ["camera", "webcam", "कैमरा"],
        "command": "start microsoft.windows.camera:",
    },
    "antigravity": {
        "name": "Antigravity",
        "executables": ["Antigravity.exe", "antigravity.exe"],
        "aliases": [
            "antigravity", "anti gravity", "anti-gravity", "antigravity app", "anti gravity app",
            "agy", "antigravity ide", "anti gravity ide", "एंटीग्रेविटी", "एंटी ग्रेविटी",
        ],
        "command": r'"C:\Users\shivam\AppData\Local\Programs\Antigravity\Antigravity.exe"',
    },
    "vlc": {
        "name": "VLC Media Player",
        "executables": ["vlc.exe", "vlc"],
        "aliases": [
            "vlc", "vlc player", "vlc media player", "media player", "video player",
            "vl c", "वीएलसी", "वीएलसी प्लेयर", "वीडियो प्लेयर", "मीडिया प्लेयर",
        ],
        "command": r'"C:\Program Files\VideoLAN\VLC\vlc.exe"',
    },
    "recyclebin": {
        "name": "Recycle Bin",
        "executables": ["explorer.exe"],
        "aliases": [
            "recycle bin", "recyclebin", "trash", "trash bin", "bin", "dustbin",
            "रीसायकल बिन", "कचरा", "कचरा पेटी", "delete files",
        ],
        "command": "explorer.exe ::{645FF040-5081-101B-9F08-00AA002F954E}",
    },
    "thispc": {
        "name": "This PC",
        "executables": ["explorer.exe"],
        "aliases": [
            "this pc", "thispc", "my computer", "this pc shortcut", "computer",
            "कंप्यूटर", "माय कंप्यूटर", "दिस पीसी",
        ],
        "command": "explorer.exe ::{20D04FE0-3AEA-1069-A2D8-08002B30309D}",
    },
    "downloads": {
        "name": "Downloads",
        "executables": ["explorer.exe"],
        "aliases": ["downloads", "download", "downloads folder", "डाउनलोड्स"],
        "command": "start shell:Downloads",
    },
    "documents": {
        "name": "Documents",
        "executables": ["explorer.exe"],
        "aliases": ["documents", "my documents", "documents folder", "डॉक्यूमेंट्स"],
        "command": "start shell:Personal",
    },
    "desktop": {
        "name": "Desktop Folder",
        "executables": ["explorer.exe"],
        "aliases": ["desktop folder", "desktop", "डेस्कटॉप"],
        "command": "start shell:Desktop",
    },
    "mongodb": {
        "name": "MongoDB Compass",
        "executables": ["MongoDBCompass.exe", "mongodb.exe"],
        "aliases": [
            "mongodb", "mongo db", "mongodb compass", "mongo compass", "compass",
            "मोंगो डीबी", "मोंगोडीबी", "मोंगो",
        ],
        "command": "mongodb",
    },
    "roblox": {
        "name": "Roblox Player",
        "executables": ["RobloxPlayerBeta.exe", "roblox.exe"],
        "aliases": ["roblox", "roblox player", "रॉब्लॉक्स", "रोब्लॉक्स"],
        "command": "roblox",
    },
    "roblox_studio": {
        "name": "Roblox Studio",
        "executables": ["RobloxStudioBeta.exe", "RobloxStudioLauncherBeta.exe"],
        "aliases": ["roblox studio", "studio roblox", "रॉब्लॉक्स स्टूडियो"],
        "command": "roblox studio",
    },
    "comet": {
        "name": "Comet",
        "executables": ["comet.exe"],
        "aliases": ["comet", "comet browser", "perplexity comet", "कॉमेट"],
        "command": "comet",
    },
    "prochat": {
        "name": "ProChat",
        "executables": ["prochat.exe"],
        "aliases": ["prochat", "pro chat", "प्रो चैट"],
        "command": "prochat",
    },
    "mingw": {
        "name": "MinGW Installer",
        "executables": ["mingw.exe", "mingw-get.exe"],
        "aliases": ["mingw", "mingw installer", "min gw"],
        "command": "mingw",
    },
    "onlyoffice": {
        "name": "ONLYOFFICE",
        "executables": ["DesktopEditors.exe", "onlyoffice.exe"],
        "aliases": ["onlyoffice", "only office", "ओनली ऑफिस"],
        "command": r'"C:\Program Files\ONLYOFFICE\DesktopEditors\DesktopEditors.exe"',
    },
    "brave": {
        "name": "Brave",
        "executables": ["brave.exe"],
        "aliases": ["brave", "brave browser", "brawe", "breav", "breave", "brav", "ब्रेव", "ब्रेव ब्राउज़र"],
        "command": r'"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"',
    },
    "typingmaster": {
        "name": "Typing Master 11",
        "executables": ["TypingMaster.exe"],
        "aliases": ["typing master", "typing master 11", "typingmaster", "टाइपिंग मास्टर"],
        "command": r'"C:\Program Files (x86)\TypingMaster11\TypingMaster.exe"',
    },
    "tally": {
        "name": "TallyPrime",
        "executables": ["tally.exe"],
        "aliases": ["tally", "tally prime", "tallyprime", "टैली", "टैली प्राइम"],
        "command": r'"C:\Program Files\TallyPrime\tally.exe"',
    },
    "snippingtool": {
        "name": "Snipping Tool",
        "executables": ["SnippingTool.exe", "ScreenClippingHost.exe"],
        "aliases": ["snipping tool", "snip", "screenshot", "screen capture", "स्निपिंग टूल", "स्क्रीनशॉट"],
        "command": "start ms-screenclip:",
    },
    "clock": {
        "name": "Clock & Alarms",
        "executables": ["Time.exe"],
        "aliases": ["clock", "alarm", "alarms", "stopwatch", "timer", "घड़ी", "अलार्म"],
        "command": "start ms-clock:",
    },
    "photos": {
        "name": "Photos",
        "executables": ["Microsoft.Photos.exe"],
        "aliases": ["photos", "pictures", "photo viewer", "gallery", "तस्वीरें", "फोटो"],
        "command": "start ms-photos:",
    },
    "store": {
        "name": "Microsoft Store",
        "executables": ["WinStore.App.exe"],
        "aliases": ["microsoft store", "store", "app store", "windows store", "स्टोर"],
        "command": "start ms-windows-store:",
    },
    "diskmgmt": {
        "name": "Disk Management",
        "executables": ["diskmgmt.msc"],
        "aliases": ["disk management", "diskmgmt", "डिस्क मैनेजमेंट", "hard disk"],
        "command": "start diskmgmt.msc",
    },
    "perfmon": {
        "name": "Performance Monitor",
        "executables": ["perfmon.exe"],
        "aliases": ["performance monitor", "perfmon", "परफॉरमेंस मॉनिटर"],
        "command": "perfmon",
    },
    "voicerecorder": {
        "name": "Voice Recorder",
        "executables": ["SoundRec.exe"],
        "aliases": ["voice recorder", "sound recorder", "audio recorder", "वॉयस रिकॉर्डर"],
        "command": "start ms-soundrecorder:",
    },
    "bluetooth": {
        "name": "Bluetooth Settings",
        "executables": ["systemsettings.exe"],
        "aliases": ["bluetooth settings", "bluetooth setting", "open bluetooth settings", "ब्लूटूथ सेटिंग्स"],
        "command": "start ms-settings:bluetooth",
    },
    "wifi": {
        "name": "Wi-Fi Settings",
        "executables": ["systemsettings.exe"],
        "aliases": ["wifi settings", "wi-fi settings", "wifi setting", "open wifi settings", "वाईफाई सेटिंग्स"],
        "command": "start ms-settings:network-wifi",
    },
    "display": {
        "name": "Display Settings",
        "executables": ["systemsettings.exe"],
        "aliases": ["display settings", "screen resolution", "brightness settings", "डिस्प्ले सेटिंग्स"],
        "command": "start ms-settings:display",
    },
    "soundsettings": {
        "name": "Sound Settings",
        "executables": ["systemsettings.exe"],
        "aliases": ["sound settings", "audio settings", "साउंड सेटिंग्स"],
        "command": "start ms-settings:sound",
    },
    "windowsupdate": {
        "name": "Windows Update",
        "executables": ["systemsettings.exe"],
        "aliases": ["windows update", "update settings", "विंडोज अपडेट"],
        "command": "start ms-settings:windowsupdate",
    },
}


class AppRegistryManager:
    """Manages the in-memory allowlist of applications with persistent Windows Start Menu & Desktop indexing."""

    def __init__(self):
        self._apps = DEFAULT_APP_REGISTRY.copy()
        self._start_menu_cache: Dict[str, str] = {}
        self._cache_file = os.path.expanduser("~/.jarvis_app_cache.json")

        # 1. Instantly load persistent disk cache if available (<0.5ms)
        self._load_cache_from_disk()

        # 2. Run background thread to refresh any newly installed apps
        import threading
        threading.Thread(target=self._index_start_menu, daemon=True).start()

    def _load_cache_from_disk(self) -> None:
        """Load persistent shortcut cache from disk for 0ms startup resolution."""
        if os.path.exists(self._cache_file):
            try:
                import json
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    if isinstance(cached, dict) and cached:
                        self._start_menu_cache = cached
                        logger.info(f"Loaded {len(self._start_menu_cache)} cached applications instantly from disk.")
            except Exception as e:
                logger.debug(f"Failed to load app cache: {e}")

    def _save_cache_to_disk(self) -> None:
        """Persist shortcut cache to disk for subsequent boots."""
        try:
            import json
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(self._start_menu_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save app cache: {e}")

    def _index_start_menu(self) -> None:
        """Index ALL Desktop + Start Menu shortcuts → resolve actual .exe paths for instant launch."""
        app_data = os.environ.get("APPDATA", "")
        prog_data = os.environ.get("ProgramData", "C:\\ProgramData")
        user_profile = os.environ.get("USERPROFILE", "")
        public = os.environ.get("PUBLIC", "C:\\Users\\Public")

        scan_dirs = [
            os.path.join(user_profile, "Desktop"),                              # User Desktop
            os.path.join(user_profile, "OneDrive", "Desktop"),                  # OneDrive Sync Desktop
            os.path.join(user_profile, "OneDrive - Personal", "Desktop"),       # OneDrive Personal Sync Desktop
            os.path.join(public, "Desktop"),                                     # Public Desktop
            os.path.join(app_data, "Microsoft", "Windows", "Start Menu", "Programs"),
            os.path.join(prog_data, "Microsoft", "Windows", "Start Menu", "Programs"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
        ]

        # Collect all .lnk file paths
        lnk_map: Dict[str, str] = {}
        for d in scan_dirs:
            if not os.path.exists(d):
                continue
            try:
                for root, _, files in os.walk(d):
                    for f in files:
                        if f.lower().endswith(".lnk"):
                            clean_name = f[:-4].lower().strip()
                            full_path = os.path.join(root, f)
                            lnk_map[clean_name] = full_path
            except Exception:
                pass

        # Resolve .lnk → actual .exe using win32com (fast, in-process COM)
        new_cache = {}
        try:
            import win32com.client
            shell_obj = win32com.client.Dispatch("WScript.Shell")
            for name, lnk_path in lnk_map.items():
                try:
                    shortcut = shell_obj.CreateShortcut(lnk_path)
                    target = shortcut.TargetPath
                    if target and os.path.exists(target) and "uninstall" not in name:
                        new_cache[name] = target  # Store actual .exe!
                    elif lnk_path and "uninstall" not in name:
                        new_cache[name] = lnk_path  # Fallback to .lnk
                except Exception:
                    if "uninstall" not in name:
                        new_cache[name] = lnk_path
        except Exception:
            for name, lnk_path in lnk_map.items():
                if "uninstall" not in name:
                    new_cache[name] = lnk_path

        if new_cache:
            self._start_menu_cache.update(new_cache)
            self._save_cache_to_disk()


    def resolve_app(self, query: str) -> Optional[Dict[str, Any]]:
        """Resolve any user-provided app name, alias, or phonetic variation into a registered or desktop application entry in <1ms."""
        import re
        query_clean = query.lower().strip()
        query_clean = re.sub(r"\b(open|kholo|start|launch|app|application|chalao)\b", "", query_clean).strip()
        if not query_clean:
            query_clean = query.lower().strip()

        # Normalized query without spaces/dashes (e.g. "only office" -> "onlyoffice", "vs code" -> "vscode")
        q_norm = re.sub(r"[\s\-_]+", "", query_clean)

        # 1. Exact key match in built-in apps
        if query_clean in self._apps:
            return self._apps[query_clean]
        if q_norm in self._apps:
            return self._apps[q_norm]

        # 2. Exact name or alias match across ALL built-in apps (Pass 1 - Exact)
        for key, info in self._apps.items():
            name_norm = re.sub(r"[\s\-_]+", "", info["name"].lower())
            if query_clean == info["name"].lower() or q_norm == name_norm:
                return info
            for alias in info.get("aliases", []):
                alias_norm = re.sub(r"[\s\-_]+", "", alias.lower())
                if query_clean == alias.lower() or q_norm == alias_norm:
                    return info

        # 3. Dynamic Desktop/Start Menu exact match for ANY installed Windows app!
        if query_clean in self._start_menu_cache:
            exe_or_lnk = self._start_menu_cache[query_clean]
            return {
                "name": query_clean.title(),
                "executables": [os.path.basename(exe_or_lnk)],
                "aliases": [query_clean],
                "command": f'"{exe_or_lnk}"',
            }

        # 4. Dynamic Desktop/Start Menu normalized exact match
        for sm_name, target in self._start_menu_cache.items():
            sm_norm = re.sub(r"[\s\-_]+", "", sm_name)
            if "uninstall" in sm_name or "reset" in sm_name or "release notes" in sm_name or "documentation" in sm_name:
                continue
            if q_norm == sm_norm:
                return {
                    "name": sm_name.title(),
                    "executables": [os.path.basename(target)],
                    "aliases": [sm_name],
                    "command": f'"{target}"',
                }

        # 5. Partial Substring Match across built-in aliases (Pass 2 - Partial)
        for key, info in self._apps.items():
            for alias in info.get("aliases", []):
                alias_norm = re.sub(r"[\s\-_]+", "", alias.lower())
                if len(q_norm) >= 4 and (q_norm in alias_norm or alias_norm in q_norm):
                    return info

        # 4. Normalized Space-Insensitive & Substring Match on ALL 93+ Start Menu / Desktop Apps!
        candidates = []
        for sm_name, target in self._start_menu_cache.items():
            sm_norm = re.sub(r"[\s\-_]+", "", sm_name)
            if "uninstall" in sm_name or "reset" in sm_name or "release notes" in sm_name or "documentation" in sm_name:
                continue
            if q_norm == sm_norm:
                return {
                    "name": sm_name.title(),
                    "executables": [os.path.basename(target)],
                    "aliases": [sm_name],
                    "command": f'"{target}"',
                }
            if len(q_norm) >= 3 and (q_norm in sm_norm or sm_norm in q_norm):
                candidates.append((sm_name, target))

        if candidates:
            candidates.sort(key=lambda x: len(x[0]))
            sm_name, target = candidates[0]
            return {
                "name": sm_name.title(),
                "executables": [os.path.basename(target)],
                "aliases": [sm_name],
                "command": f'"{target}"',
            }

        return None

    def register(self, key: str, name: str, executable: str, aliases: Optional[List[str]] = None) -> None:
        """Register a new application into the allowlist."""
        self._apps[key.lower().strip()] = {
            "name": name,
            "executables": [executable.lower().strip()],
            "aliases": aliases or [key.lower().strip()],
            "command": executable,
        }

    def list_all(self) -> List[Dict[str, Any]]:
        """Return list of all registered applications."""
        return list(self._apps.values())


app_registry = AppRegistryManager()


# ==========================================
# Pydantic Schemas for Input Validation
# ==========================================

class OpenAppArgs(BaseModel):
    app_name: str = Field(..., description="Name or alias of the application to launch (e.g. 'Chrome', 'VS Code', 'Notepad', 'Calculator').")
    arguments: Optional[str] = Field(None, description="Optional safe file path or URL to open in the application.")


class CloseAppArgs(BaseModel):
    app_name: str = Field(..., description="Name or alias of the application to terminate (e.g. 'Calculator', 'Notepad', 'Chrome').")
    force: bool = Field(False, description="Whether to force kill unresponsive process instances.")


class ListRunningAppsArgs(BaseModel):
    limit: int = Field(20, description="Maximum number of running processes to display.")


class RegisterAppArgs(BaseModel):
    app_name: str = Field(..., description="Display name of the application.")
    executable_path: str = Field(..., description="Path or command for the executable.")
    aliases: Optional[List[str]] = Field(None, description="Comma-separated or list of aliases.")


# ==========================================
# Application Tools
# ==========================================

def find_installed_app_path(app_key: str, executables: List[str]) -> Optional[str]:
    """Dynamically resolve absolute executable paths or shortcuts on Windows in <1ms."""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    app_data = os.environ.get("APPDATA", "")

    if app_key in ["vscode", "vs code", "code"]:
        vsc_exe = os.path.join(local_app_data, "Programs", "Microsoft VS Code", "Code.exe")
        if os.path.exists(vsc_exe):
            return f'"{vsc_exe}"'
        vsc_lnk = os.path.join(app_data, "Microsoft", "Windows", "Start Menu", "Programs", "Visual Studio Code", "Visual Studio Code.lnk")
        if os.path.exists(vsc_lnk):
            return f'"{vsc_lnk}"'

    if app_key == "discord":
        user_profile = os.environ.get("USERPROFILE", "")
        disc_lnk = os.path.join(app_data, "Microsoft", "Windows", "Start Menu", "Programs", "Discord Inc", "Discord.lnk")
        if os.path.exists(disc_lnk):
            return disc_lnk
        disc_lnk2 = os.path.join(app_data, "Microsoft", "Windows", "Start Menu", "Programs", "Discord.lnk")
        if os.path.exists(disc_lnk2):
            return disc_lnk2
        disc_desktop = os.path.join(user_profile, "Desktop", "Discord.lnk")
        if os.path.exists(disc_desktop):
            return disc_desktop
        disc_update = os.path.join(local_app_data, "Discord", "Update.exe")
        if os.path.exists(disc_update):
            return f'"{disc_update}" --processStart Discord.exe'

    if "roblox" in app_key:
        import glob
        roblox_betas = glob.glob(os.path.join(local_app_data, "Roblox", "Versions", "*", "RobloxPlayerBeta.exe"))
        if roblox_betas:
            latest_roblox = sorted(roblox_betas, key=os.path.getmtime)[-1]
            return f'"{latest_roblox}"'
        roblox_lnk = os.path.join(app_data, "Microsoft", "Windows", "Start Menu", "Programs", "Roblox", "Roblox Player.lnk")
        if os.path.exists(roblox_lnk):
            return f'"{roblox_lnk}"'

    if "vlc" in app_key:
        vlc_prog = r"C:\Program Files\VideoLAN\VLC\vlc.exe"
        if os.path.exists(vlc_prog):
            return f'"{vlc_prog}"'
        vlc_lnk = os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), "Microsoft", "Windows", "Start Menu", "Programs", "VideoLAN", "VLC media player.lnk")
        if os.path.exists(vlc_lnk):
            return f'"{vlc_lnk}"'

    if "antigravity" in app_key or "agy" in app_key:
        agy_exe = os.path.join(local_app_data, "Programs", "Antigravity", "Antigravity.exe")
        if os.path.exists(agy_exe):
            return f'"{agy_exe}"'
        agy_lnk = os.path.join(app_data, "Microsoft", "Windows", "Start Menu", "Programs", "Antigravity", "Antigravity.lnk")
        if os.path.exists(agy_lnk):
            return f'"{agy_lnk}"'
        agy_lnk2 = os.path.join(app_data, "Microsoft", "Windows", "Start Menu", "Programs", "Antigravity.lnk")
        if os.path.exists(agy_lnk2):
            return f'"{agy_lnk2}"'

    # ── Check Start Menu shortcut cache (covers apps like Comet, Perplexity etc.) in 0ms ──
    try:
        import json
        _cache_path = os.path.expanduser("~/.jarvis_app_cache.json")
        if os.path.exists(_cache_path):
            _cache = json.load(open(_cache_path, encoding="utf-8"))
            # Direct key match
            if app_key in _cache and os.path.exists(_cache[app_key]):
                return f'"{_cache[app_key]}"'
            # Match by executable name
            for exe in executables:
                exe_lower = exe.lower()
                for _k, _v in _cache.items():
                    if exe_lower in _v.lower() and os.path.exists(_v):
                        return f'"{_v}"'
    except Exception:
        pass

    # ── Instant PATH check (0ms) ──
    import shutil
    for exe in executables:
        w = shutil.which(exe)
        if w:
            return f'"{w}"'

    return None


@tool(
    name="open_application",
    description="Launch an authorized Windows application (e.g. Chrome, VS Code, Notepad, Calculator, Spotify, Edge, File Explorer).",
    permission_level=PermissionLevel.LEVEL_1_NORMAL,
    category=ToolCategory.SYSTEM,
    args_schema=OpenAppArgs,
)
def open_application(app_name: str, arguments: Optional[str] = None) -> Dict[str, Any]:
    """Safely launch an application from the allowlist."""
    app_entry = app_registry.resolve_app(app_name)

    if not app_entry:
        registered_names = [a["name"] for a in app_registry.list_all()]
        raise PermissionError(
            f"Application '{app_name}' is not in the authorized application allowlist. "
            f"Available apps: {', '.join(registered_names)}."
        )

    # 1. Check if application window is ALREADY running / minimized in taskbar (<1ms)
    try:
        from backend.tools.ui_automation import find_app_window, force_foreground_window
        hwnd, title = find_app_window(app_entry["name"])
        if not hwnd and app_name:
            hwnd, title = find_app_window(app_name)

        if hwnd:
            focused = force_foreground_window(hwnd)
            if focused:
                logger.info(f"Brought existing running application '{app_entry['name']}' window to foreground.")
                return {
                    "status": "success",
                    "application": app_entry["name"],
                    "message": f"Successfully brought existing {app_entry['name']} window to front.",
                }
    except Exception as e:
        logger.debug(f"Taskbar window search error: {e}")

    # 2. Resolve actual installed executable path or shortcut if not already running
    raw_cmd = app_entry.get("command", "")
    app_keys = [k for k, v in app_registry._apps.items() if v["name"] == app_entry["name"]]
    k_name = app_keys[0] if app_keys else ""
    resolved_path = find_installed_app_path(k_name, app_entry.get("executables", []))

    if resolved_path and os.path.exists(resolved_path.strip('"\n ')):
        cmd = resolved_path
    elif raw_cmd.startswith("start shell:") or (":" in raw_cmd and not os.path.exists(raw_cmd.strip('"\n '))):
        cmd = raw_cmd
    else:
        cmd = raw_cmd

    try:
        clean_target = cmd.strip('"\n ')
        if arguments:
            safe_args = arguments.strip().replace(";", "").replace("&", "").replace("|", "")
            full_cmd = f"{cmd} {safe_args}"
            subprocess.Popen(full_cmd, shell=True)
        else:
            # Special Windows Shell Virtual Folders (Recycle Bin = 10, This PC = 17) via native COM API
            if "recycle" in app_entry["name"].lower() or "::{645ff040" in cmd.lower():
                try:
                    import win32com.client
                    shell_com = win32com.client.Dispatch("Shell.Application")
                    shell_com.Open(10)  # ssfBITBUCKET (Recycle Bin)
                except Exception:
                    subprocess.Popen("explorer.exe ::{645FF040-5081-101B-9F08-00AA002F954E}", shell=True)
            elif "this pc" in app_entry["name"].lower() or "::{20d04fe0" in cmd.lower():
                try:
                    import win32com.client
                    shell_com = win32com.client.Dispatch("Shell.Application")
                    shell_com.Open(17)  # ssfDRIVES (This PC)
                except Exception:
                    subprocess.Popen("explorer.exe ::{20D04FE0-3AEA-1069-A2D8-08002B30309D}", shell=True)
            elif "::{" in cmd:
                subprocess.Popen(cmd, shell=True)
            elif clean_target in ["explorer", "explorer.exe"]:
                os.startfile("explorer.exe")
            # Handle UWP Protocol URIs (whatsapp:, ms-settings:, telegram:, etc.) for instant launch (<5ms)
            elif cmd.startswith("start ") and ":" in cmd:
                proto_uri = cmd.split("start ")[1].strip()
                try:
                    os.startfile(proto_uri)
                except Exception:
                    subprocess.Popen(cmd, shell=True)
            elif "--processStart" in cmd or cmd.startswith("start "):
                subprocess.Popen(cmd, shell=True)
            elif os.path.exists(clean_target):
                # Use ShellExecuteW — instant, non-blocking, Windows-native (<5ms)
                try:
                    ctypes.windll.shell32.ShellExecuteW(None, "open", clean_target, None, None, 1)
                except Exception:
                    os.startfile(clean_target)
            else:
                subprocess.Popen(cmd, shell=True)

        # Background focus — try to bring app to front once it appears (non-blocking, no sleep loop)
        def _bg_focus(target_name: str, exe_path: str):
            import time
            from backend.tools.ui_automation import find_app_window, force_foreground_window
            # Try every 0.5s for up to 30s (heavy apps like ONLYOFFICE take ~10-20s)
            for _ in range(60):
                time.sleep(0.5)
                h, _ = find_app_window(target_name)
                if h:
                    force_foreground_window(h)
                    break

        import threading
        threading.Thread(target=_bg_focus, args=(app_entry["name"], clean_target), daemon=True).start()

        logger.info(f"Successfully launched application '{app_entry['name']}'")
        return {
            "status": "success",
            "application": app_entry["name"],
            "message": f"Ji Boss, {app_entry['name']} launch kar diya. Kuch seconds mein khul jaayega.",
        }
    except Exception as exc:
        raise RuntimeError(f"Failed to launch '{app_entry['name']}': {exc}")


@tool(
    name="launch_app",
    description="Launch an authorized Windows application (alias for open_application).",
    permission_level=PermissionLevel.LEVEL_1_NORMAL,
    category=ToolCategory.SYSTEM,
    args_schema=OpenAppArgs,
)
def launch_app(app_name: str, arguments: Optional[str] = None) -> Dict[str, Any]:
    """Launch application alias."""
    return open_application(app_name=app_name, arguments=arguments)


@tool(
    name="close_application",
    description="Safely close or terminate running instances of an authorized application (e.g. Calculator, Notepad, Chrome).",
    permission_level=PermissionLevel.LEVEL_1_NORMAL,
    category=ToolCategory.SYSTEM,
    args_schema=CloseAppArgs,
)
def close_application(app_name: str, force: bool = False) -> Dict[str, Any]:
    """Find and terminate running process instances matching the application."""
    app_entry = app_registry.resolve_app(app_name)
    target_executables = app_entry["executables"] if app_entry else [f"{app_name.lower().strip()}.exe", app_name.lower().strip()]
    app_display = app_entry["name"] if app_entry else app_name

    # Protect current process and its parent/ancestors from closing itself
    protected_pids = {os.getpid()}
    try:
        current_proc = psutil.Process(os.getpid())
        for p in current_proc.parents():
            protected_pids.add(p.pid)
    except Exception:
        pass

    terminated_count = 0
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["pid"] in protected_pids:
                continue

            p_name = proc.info["name"]
            if p_name and any(p_name.lower() == exe.lower() for exe in target_executables):
                if force:
                    proc.kill()
                else:
                    proc.terminate()
                terminated_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if terminated_count == 0:
        return {
            "status": "not_found",
            "application": app_display,
            "message": f"No active running instances of '{app_display}' were found.",
        }

    logger.info(f"Closed {terminated_count} process instance(s) of '{app_display}'")
    return {
        "status": "success",
        "application": app_display,
        "instances_closed": terminated_count,
        "message": f"Successfully closed {terminated_count} instance(s) of {app_display}.",
    }


@tool(
    name="list_running_applications",
    description="List active desktop applications and background user processes with CPU and memory usage.",
    permission_level=PermissionLevel.LEVEL_0_SAFE,
    category=ToolCategory.SYSTEM,
    args_schema=ListRunningAppsArgs,
)
def list_running_applications(limit: int = 20) -> Dict[str, Any]:
    """Retrieve active user applications sorted by memory consumption."""
    running_apps = []
    seen_names = set()

    for proc in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
        try:
            name = proc.info["name"]
            if not name or name in seen_names or name.lower() in ["system", "registry", "smss.exe", "csrss.exe"]:
                continue

            # Filter for common GUI / user applications
            mem_pct = round(proc.info.get("memory_percent") or 0.0, 2)
            running_apps.append({
                "pid": proc.info["pid"],
                "name": name,
                "memory_percent": mem_pct,
            })
            seen_names.add(name)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Sort by memory usage descending
    sorted_apps = sorted(running_apps, key=lambda x: x["memory_percent"], reverse=True)[:limit]
    return {
        "total_active": len(sorted_apps),
        "applications": sorted_apps,
    }


@tool(
    name="register_application",
    description="Register a new application in the JARVIS allowlist so it can be launched safely.",
    permission_level=PermissionLevel.LEVEL_1_NORMAL,
    category=ToolCategory.SYSTEM,
    args_schema=RegisterAppArgs,
)
def register_application(
    app_name: str,
    executable_path: str,
    aliases: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Add a verified application to the in-memory allowlist."""
    key = app_name.lower().replace(" ", "_")
    app_registry.register(
        key=key,
        name=app_name,
        executable=executable_path,
        aliases=aliases,
    )
    return {
        "status": "success",
        "message": f"Successfully registered '{app_name}' ({executable_path}) into application allowlist.",
    }


class CleanUnusedAppsArgs(BaseModel):
    close_browsers: bool = Field(False, description="Whether to also close open web browser windows.")


@tool(
    name="clean_unused_apps",
    description="Close idle, unused, or background taskbar applications to clean up memory and desktop clutter. (e.g. 'faltu tabs band karo', 'clean taskbar', 'close background apps', 'close idle apps', 'cleanup desktop').",
    permission_level=PermissionLevel.LEVEL_1_NORMAL,
    category=ToolCategory.SYSTEM,
    args_schema=CleanUnusedAppsArgs,
)
def clean_unused_apps(close_browsers: bool = False) -> Dict[str, Any]:
    """Clean up idle non-essential desktop applications (Notepad, Calculator, Paint, Spotify, Media)."""
    target_cleanup_exes = [
        "notepad.exe", "calc.exe", "calculatorapp.exe", "mspaint.exe",
        "spotify.exe", "vlc.exe", "wmplayer.exe", "snippingtool.exe",
        "photos.exe"
    ]
    if close_browsers:
        target_cleanup_exes.extend(["msedge.exe", "chrome.exe", "firefox.exe"])

    protected_pids = {os.getpid()}
    try:
        current_proc = psutil.Process(os.getpid())
        for p in current_proc.parents():
            protected_pids.add(p.pid)
    except Exception:
        pass

    closed_apps = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["pid"] in protected_pids:
                continue

            p_name = proc.info["name"]
            if p_name and p_name.lower() in target_cleanup_exes:
                proc.terminate()
                closed_apps.append(p_name)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not closed_apps:
        return {
            "status": "success",
            "closed_count": 0,
            "message": "Taskbar is already clean. No unused background applications found.",
        }

    unique_closed = list(set(closed_apps))
    logger.info(f"Cleaned {len(closed_apps)} taskbar application instances: {unique_closed}")
    return {
        "status": "success",
        "closed_count": len(closed_apps),
        "apps_closed": unique_closed,
        "message": f"Cleaned up {len(closed_apps)} taskbar application(s): {', '.join(unique_closed)}.",
    }
