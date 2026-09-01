"""JARVIS 3.0 - Application Discovery Engine.

Automatically inspects the local Windows operating system to discover
all installed applications (desktop executables, UWP apps, Start Menu shortcuts,
and system utilities) without hardcoding application lists.
"""
from enum import Enum
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.logger import get_logger

logger = get_logger("AppDiscovery")

try:
    import winreg
    WINREG_AVAILABLE = True
except ImportError:
    WINREG_AVAILABLE = False


class AppCategory(str, Enum):
    BROWSERS = "Browsers"
    COMMUNICATION = "Communication"
    MEDIA = "Media"
    PRODUCTIVITY = "Productivity"
    DEVELOPMENT = "Development"
    FILE_MANAGEMENT = "File Management"
    SYSTEM_UTILITIES = "System Utilities"
    EDUCATION = "Education"
    CREATIVE = "Creative"
    CLOUD = "Cloud"
    SECURITY = "Security"
    GAMING = "Gaming"
    OFFICE = "Office"
    SOCIAL = "Social"
    OTHER = "Other"


class AppType(str, Enum):
    DESKTOP = "desktop"
    WEB = "web"
    SYSTEM = "system"
    UWP = "uwp"


class DiscoveredApp(BaseModel):
    """Represents an application installed on the user's computer."""
    id: str
    name: str
    executable_path: Optional[str] = None
    install_location: Optional[str] = None
    version: Optional[str] = None
    publisher: Optional[str] = None
    launch_command: str
    category: AppCategory = AppCategory.OTHER
    app_type: AppType = AppType.DESKTOP
    adapter_name: str = "GenericDesktopAdapter"
    is_installed: bool = True
    icon_hint: Optional[str] = None


class ApplicationDiscoveryEngine:
    """Discovers installed software via Windows Registry, Start Menu, and System directories."""

    # Categorization mapping based on keywords in name / publisher / executable
    CATEGORY_KEYWORDS = {
        AppCategory.BROWSERS: ["chrome", "firefox", "edge", "brave", "opera", "safari", "browser", "vivaldi", "tor"],
        AppCategory.COMMUNICATION: ["whatsapp", "telegram", "discord", "slack", "zoom", "teams", "skype", "viber", "signal"],
        AppCategory.MEDIA: ["youtube", "spotify", "vlc", "media player", "itunes", "netflix", "prime video", "audacity", "foobar", "kmplayer", "potplayer"],
        AppCategory.PRODUCTIVITY: ["notion", "evernote", "obsidian", "todoist", "trello", "onenote", "ticktick", "anydo"],
        AppCategory.DEVELOPMENT: ["visual studio", "vscode", "code", "pycharm", "intellij", "git", "docker", "postman", "sublime", "notepad++", "anaconda", "cursor", "android studio", "eclipse", "terminal"],
        AppCategory.FILE_MANAGEMENT: ["explorer", "total commander", "winrar", "7-zip", "peazip", "filezilla", "everything"],
        AppCategory.SYSTEM_UTILITIES: ["settings", "task manager", "calculator", "notepad", "paint", "cmd", "powershell", "control panel", "device manager", "regedit", "snipping tool"],
        AppCategory.OFFICE: ["word", "excel", "powerpoint", "outlook", "access", "libreoffice", "wps office"],
        AppCategory.CREATIVE: ["photoshop", "illustrator", "premiere", "blender", "canva", "figma", "gimp", "inkscape", "coreldraw", "davinci"],
        AppCategory.GAMING: ["steam", "epic games", "riot client", "valorant", "minecraft", "ea app", "battle.net", "gog galaxy", "xbox", "roblox"],
        AppCategory.SECURITY: ["antivirus", "windows security", "malwarebytes", "bitdefender", "avast", "nordvpn", "expressvpn"],
        AppCategory.CLOUD: ["google drive", "dropbox", "onedrive", "icloud", "mega"],
    }

    # Dedicated Adapter mappings
    DEDICATED_ADAPTER_MAP = {
        "youtube": "YouTubeAdapter",
        "chrome": "ChromeAdapter",
        "google chrome": "ChromeAdapter",
        "whatsapp": "WhatsAppAdapter",
        "explorer": "FileManagerAdapter",
        "file explorer": "FileManagerAdapter",
        "settings": "SystemAdapter",
        "calculator": "SystemAdapter",
        "calc": "SystemAdapter",
        "notepad": "SystemAdapter",
    }

    @classmethod
    def discover_all_applications(cls) -> List[DiscoveredApp]:
        """Scan registry, shortcuts, and system paths to discover all installed apps."""
        discovered: Dict[str, DiscoveredApp] = {}

        # 1. System Built-in Core Utilities
        for app in cls._get_builtin_system_apps():
            discovered[app.id] = app

        # 2. Registry Scan (64-bit and 32-bit)
        if WINREG_AVAILABLE:
            for app in cls._scan_windows_registry():
                if app.id not in discovered:
                    discovered[app.id] = app

        # 3. Start Menu Shortcuts Scan
        for app in cls._scan_start_menu():
            if app.id not in discovered:
                discovered[app.id] = app

        # 4. WindowsApps / Execution Aliases Scan
        for app in cls._scan_windows_apps_aliases():
            if app.id not in discovered:
                discovered[app.id] = app

        # 5. Common Web Applications
        for app in cls._get_supported_web_apps():
            discovered[app.id] = app

        logger.info(f"Discovered {len(discovered)} total installed applications and tools on system.")
        return sorted(list(discovered.values()), key=lambda a: a.name.lower())

    @classmethod
    def _slugify(cls, text: str) -> str:
        s = text.lower().strip()
        s = re.sub(r"[^\w\s-]", "", s)
        s = re.sub(r"[\s-]+", "_", s)
        return s

    @classmethod
    def _deduce_category(cls, name: str, publisher: Optional[str] = None) -> AppCategory:
        text = f"{name} {publisher or ''}".lower()
        for cat, kws in cls.CATEGORY_KEYWORDS.items():
            if any(re.search(rf"\b{re.escape(kw)}\b", text) or kw in text for kw in kws):
                return cat
        return AppCategory.OTHER

    @classmethod
    def _deduce_adapter(cls, name: str) -> str:
        clean = name.lower()
        for k, adapter in cls.DEDICATED_ADAPTER_MAP.items():
            if k in clean:
                return adapter
        return "GenericDesktopAdapter"

    @classmethod
    def _get_builtin_system_apps(cls) -> List[DiscoveredApp]:
        """Essential Windows Built-in applications."""
        return [
            DiscoveredApp(
                id="file_explorer",
                name="File Explorer",
                launch_command="explorer",
                category=AppCategory.FILE_MANAGEMENT,
                app_type=AppType.SYSTEM,
                adapter_name="FileManagerAdapter",
            ),
            DiscoveredApp(
                id="notepad",
                name="Notepad",
                launch_command="notepad",
                category=AppCategory.SYSTEM_UTILITIES,
                app_type=AppType.SYSTEM,
                adapter_name="SystemAdapter",
            ),
            DiscoveredApp(
                id="calculator",
                name="Calculator",
                launch_command="calc",
                category=AppCategory.SYSTEM_UTILITIES,
                app_type=AppType.SYSTEM,
                adapter_name="SystemAdapter",
            ),
            DiscoveredApp(
                id="windows_settings",
                name="Settings",
                launch_command="start ms-settings:",
                category=AppCategory.SYSTEM_UTILITIES,
                app_type=AppType.SYSTEM,
                adapter_name="SystemAdapter",
            ),
            DiscoveredApp(
                id="task_manager",
                name="Task Manager",
                launch_command="taskmgr",
                category=AppCategory.SYSTEM_UTILITIES,
                app_type=AppType.SYSTEM,
                adapter_name="SystemAdapter",
            ),
            DiscoveredApp(
                id="paint",
                name="Paint",
                launch_command="mspaint",
                category=AppCategory.CREATIVE,
                app_type=AppType.SYSTEM,
                adapter_name="GenericDesktopAdapter",
            ),
            DiscoveredApp(
                id="cmd",
                name="Command Prompt",
                launch_command="cmd",
                category=AppCategory.DEVELOPMENT,
                app_type=AppType.SYSTEM,
                adapter_name="GenericDesktopAdapter",
            ),
        ]

    @classmethod
    def _get_supported_web_apps(cls) -> List[DiscoveredApp]:
        """Major web applications with dedicated support."""
        return [
            DiscoveredApp(
                id="youtube",
                name="YouTube",
                launch_command="https://www.youtube.com",
                category=AppCategory.MEDIA,
                app_type=AppType.WEB,
                adapter_name="YouTubeAdapter",
            ),
        ]

    @classmethod
    def _scan_windows_registry(cls) -> List[DiscoveredApp]:
        """Scan standard Windows uninstall registry locations for installed programs."""
        if not WINREG_AVAILABLE:
            return []

        apps = []
        reg_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_READ | winreg.KEY_WOW64_64KEY),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_READ | winreg.KEY_WOW64_32KEY),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_READ),
        ]

        for root, subkey, access in reg_paths:
            try:
                key = winreg.OpenKey(root, subkey, 0, access)
                num_subkeys, _, _ = winreg.QueryInfoKey(key)
                for i in range(num_subkeys):
                    try:
                        sub_name = winreg.EnumKey(key, i)
                        sub_k = winreg.OpenKey(key, sub_name, 0, access)
                        
                        def _val(v_name):
                            try:
                                return winreg.QueryValueEx(sub_k, v_name)[0]
                            except Exception:
                                return None

                        disp_name = _val("DisplayName")
                        if not disp_name or len(disp_name.strip()) < 2:
                            continue
                        
                        # Filter out Windows updates and KB packages
                        if disp_name.startswith("Security Update") or disp_name.startswith("Update for"):
                            continue

                        disp_ver = _val("DisplayVersion")
                        publisher = _val("Publisher")
                        install_loc = _val("InstallLocation")
                        disp_icon = _val("DisplayIcon")

                        # Determine executable
                        exe_path = None
                        if disp_icon and disp_icon.lower().endswith(".exe") and os.path.exists(disp_icon):
                            exe_path = disp_icon
                        elif install_loc and os.path.isdir(install_loc):
                            for f in os.listdir(install_loc):
                                if f.lower().endswith(".exe") and not any(u in f.lower() for u in ["unins", "setup", "helper"]):
                                    exe_path = os.path.join(install_loc, f)
                                    break

                        app_id = cls._slugify(disp_name)
                        launch_cmd = f'"{exe_path}"' if exe_path else disp_name

                        apps.append(DiscoveredApp(
                            id=app_id,
                            name=disp_name.strip(),
                            executable_path=exe_path,
                            install_location=install_loc,
                            version=disp_ver,
                            publisher=publisher,
                            launch_command=launch_cmd,
                            category=cls._deduce_category(disp_name, publisher),
                            app_type=AppType.DESKTOP,
                            adapter_name=cls._deduce_adapter(disp_name),
                        ))
                    except Exception:
                        continue
            except Exception as e:
                logger.debug(f"Registry scan error for {subkey}: {e}")

        return apps

    @classmethod
    def _scan_start_menu(cls) -> List[DiscoveredApp]:
        """Scan Windows Start Menu folders for application shortcuts."""
        apps = []
        user_start = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"))
        common_start = Path(os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"))

        for start_dir in [user_start, common_start]:
            if not start_dir.exists():
                continue
            for root, _, files in os.walk(start_dir):
                for f in files:
                    if f.lower().endswith(".lnk"):
                        name = f[:-4].strip()
                        if any(ex in name.lower() for ex in ["uninstall", "help", "readme", "documentation"]):
                            continue
                        app_id = cls._slugify(name)
                        apps.append(DiscoveredApp(
                            id=app_id,
                            name=name,
                            launch_command=os.path.join(root, f),
                            category=cls._deduce_category(name),
                            app_type=AppType.DESKTOP,
                            adapter_name=cls._deduce_adapter(name),
                        ))
        return apps

    @classmethod
    def _scan_windows_apps_aliases(cls) -> List[DiscoveredApp]:
        """Scan %LOCALAPPDATA%\\Microsoft\\WindowsApps for execution aliases."""
        apps = []
        p = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps"))
        if p.exists():
            for f in p.glob("*.exe"):
                name = f.stem.title()
                app_id = cls._slugify(name)
                apps.append(DiscoveredApp(
                    id=app_id,
                    name=name,
                    executable_path=str(f),
                    launch_command=str(f),
                    category=cls._deduce_category(name),
                    app_type=AppType.UWP,
                    adapter_name=cls._deduce_adapter(name),
                ))
        return apps


application_discovery_engine = ApplicationDiscoveryEngine()
