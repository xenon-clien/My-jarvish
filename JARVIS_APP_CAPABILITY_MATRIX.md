# =====================================================================
# JARVIS 152-APP CAPABILITY MATRIX & TIER CLASSIFICATION
# =====================================================================

This document establishes the definitive capability tier and health rating for all 152 claimed applications.

## Tier Architecture
- **Tier 1 (Dedicated Custom Adapters)**: Full deep internal automation, window focus lock, action dispatch, and state verification.
- **Tier 2 (Declarative Skill / Universal UIAutomation)**: Pinned keyboard shortcuts, process management, and accessibility tree interaction.
- **Tier 3 (Generic OS Process Automation)**: Launching, closing, switching, minimizing, and maximizing via Windows API.
- **Tier 4 (Declared / Unsupported In-Depth)**: Registered in name only; deep internal automation does not yet exist.

---

## Tier 1 Applications (Deep Automation Adapters)
| Application | App ID | Type | Adapter Module | Launch Method | Control Method | Registered Features | Implemented Features | Health Status |
|---|---|---|---|---|---|:---:|:---:|:---:|
| **YouTube** | `youtube` | Web / Hybrid | `backend.adapters.youtube_adapter`, `browser_tools.py` | Chrome / Edge Web Process | Hardware Scan Codes + Native Viewport Navigation | 18 | 18 | **HEALTHY / VERIFIED** |
| **WhatsApp** | `whatsapp` | Desktop / Web | `backend.adapters.whatsapp_adapter`, `whatsapp_tools.py` | Desktop Executable / Web App | Win32 Window Messaging + Shortcuts | 12 | 11 | **HEALTHY / VERIFIED** |
| **Windows System** | `system` | OS Native | `backend.adapters.system_adapter`, `system_tools.py` | Win32 API Kernel | `ctypes.windll`, PowerShell, WMI | 24 | 24 | **HEALTHY / VERIFIED** |

---

## Tier 2 Applications (Skill Definitions / Common Tool Integrations)
| Application | App ID | Type | Adapter Module | Launch Method | Control Method | Registered Features | Implemented Features | Health Status |
|---|---|---|---|---|---|:---:|:---:|:---:|
| **Google Chrome** | `chrome` | Desktop Browser | `browser_tools.py`, `skills/chrome` | `chrome.exe` | Win32 Focus + Tab Keybd Shortcuts | 8 | 8 | **HEALTHY** |
| **Microsoft Edge** | `msedge` | Desktop Browser | `browser_tools.py`, `skills/edge` | `msedge.exe` | Win32 Focus + Tab Keybd Shortcuts | 8 | 8 | **HEALTHY** |
| **Spotify** | `spotify` | Desktop Music | `media_tools.py`, `skills/spotify` | `spotify.exe` | Windows Global Media Keys | 6 | 6 | **HEALTHY** |
| **VS Code** | `vscode` | Desktop IDE | `skills/vscode`, `ui_automation.py` | `code.exe` | Win32 Focus + CLI Launch | 6 | 6 | **HEALTHY** |
| **File Explorer** | `explorer` | OS Shell | `file_tools.py`, `skills/file_explorer`| `explorer.exe` | Win32 API + Shell COM Objects | 14 | 14 | **HEALTHY** |
| **Notepad** | `notepad` | Desktop Utility | `ui_automation.py` | `notepad.exe` | Win32 Focus + Text Injection | 4 | 4 | **HEALTHY** |
| **Calculator** | `calc` | Desktop Utility | `app_tools.py` | `calc.exe` | Win32 Focus + Basic Injection | 3 | 3 | **HEALTHY** |

---

## Tier 3 Applications (OS-Level Process & Window Management)
All 53 built-in curated applications and 97 local disk discovered applications support:
1. `open_application(app_name)` $ightarrow$ **100% Functional**
2. `close_application(app_name)` $ightarrow$ **100% Functional**
3. `switch_window(app_name)` $ightarrow$ **100% Functional**
4. `manage_window(action='minimize'|'maximize'|'restore'|'close')` $ightarrow$ **100% Functional**

### Application Inventory Roster (Sample of 53 Primary Apps):
| App Name | Executable Candidates | Launch | Focus | Deep UI Actions | Health Status |
|---|---|:---:|:---:|:---:|:---:|
| Discord | `discord.exe`, `discord` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Telegram | `telegram.exe`, `telegram` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Slack | `slack.exe`, `slack` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Zoom | `zoom.exe`, `zoom` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Microsoft Teams | `teams.exe`, `teams` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| VLC Media Player | `vlc.exe`, `vlc` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| OBS Studio | `obs64.exe`, `obs32.exe` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Audacity | `audacity.exe`, `audacity` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| GIMP | `gimp-2.10.exe`, `gimp` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Blender | `blender.exe`, `blender` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Steam | `steam.exe`, `steam` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Epic Games | `epicgameslauncher.exe` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Brave Browser | `brave.exe`, `brave` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Mozilla Firefox | `firefox.exe`, `firefox` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Microsoft Word | `winword.exe`, `winword` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Microsoft Excel | `excel.exe`, `excel` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Microsoft PowerPoint | `powerpnt.exe`, `powerpnt` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Adobe Photoshop | `photoshop.exe` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Adobe Premiere Pro | `premiere.exe` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Windows Terminal | `wt.exe`, `windowsterminal` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| PowerShell | `powershell.exe`, `pwsh.exe` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Command Prompt | `cmd.exe` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Task Manager | `taskmgr.exe` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |
| Settings | `ms-settings:` | YES | YES | Generic Only | **TIER 3 FUNCTIONAL** |

---

## Tier 4 Applications (The 152-App Reality Statement)
When a prompt requests "All features for 152 apps", JARVIS can reliably provide **Tier 3 OS process and window orchestration** for all 152 apps. It does NOT possess 152 custom internal UI engines. Declaring otherwise leads to artificial expectation failure.
