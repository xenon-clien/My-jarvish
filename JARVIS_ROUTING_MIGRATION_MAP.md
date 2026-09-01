# =====================================================================
# JARVIS ULTRA ROUTING MIGRATION MAP & CONTEXT RESOLUTION MATRIX
# =====================================================================

This document maps how raw user utterances resolve through the Domain -> App -> Action pipeline.

## 1. Application Context Precedence Order
```
1. EXPLICIT APPLICATION IN COMMAND   (e.g., "YouTube ka agla short chalao" -> app = "youtube")
               ↓ (if none)
2. PARENT COMPOUND TASK CONTEXT     (e.g., in step 2 of "YouTube kholo aur 1st short chalao")
               ↓ (if none)
3. VERIFIED FOREGROUND ACTIVE WINDOW (e.g., Win32 GetForegroundWindow() detects "chrome" / "spotify")
               ↓ (if none)
4. RECENT TASK CONTEXT (< 30s)       (e.g., previous turn was interacting with "whatsapp")
               ↓ (if none)
5. DEFAULT SYSTEM DOMAIN            (e.g., "system")
```

---

## 2. Command Resolution Examples
| User Transcript | Active Context | Resolved Domain | Resolved App | Canonical Action / Tool |
|---|---|:---:|:---:|---|
| `"next short"` | YouTube | `media` | `youtube` | `youtube.next_short` / `click_screen_video` |
| `"next song"` | Spotify | `media` | `spotify` | `spotify.next_track` / `control_media('next')` |
| `"YouTube ka next short"` | Spotify (Foreground) | `media` | `youtube` | `youtube.next_short` (Explicit override) |
| `"Harsh ko message karo"` | Any | `communication` | `whatsapp` | `whatsapp.send_whatsapp_message` |
| `"battery status"` | Any | `system` | `system` | `system.get_battery_status` |
| `"Downloads kholo"` | Any | `file` | `explorer` | `file_tools.list_directory('Downloads')` |
| `"YouTube kholo aur pehla short chalao"` | Desktop | `media` | `youtube` | **Step 1:** `youtube.open`<br>**Step 2:** `youtube.play_short(1)` |
