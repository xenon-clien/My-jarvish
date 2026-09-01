import win32gui
import win32api
import win32con
import win32clipboard
import time
import ctypes

user32 = ctypes.windll.user32

def navigate_active_browser_url(url: str = "https://www.youtube.com/shorts"):
    print(f"Navigating active Chrome/Browser to: {url}")
    
    # 1. Dismiss any open modal dialog first
    user32.keybd_event(0x1B, 0, 0, 0)  # ESCAPE
    time.sleep(0.04)
    user32.keybd_event(0x1B, 0, 2, 0)
    time.sleep(0.05)
    
    # 2. Put target URL on clipboard
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(url, win32clipboard.CF_UNICODETEXT)
    win32clipboard.CloseClipboard()
    time.sleep(0.03)
    
    # 3. Focus Address Bar (Ctrl + L)
    user32.keybd_event(0x11, 0, 0, 0)  # CTRL down
    user32.keybd_event(0x4C, 0, 0, 0)  # 'L' down
    time.sleep(0.04)
    user32.keybd_event(0x4C, 0, 2, 0)  # 'L' up
    user32.keybd_event(0x11, 0, 2, 0)  # CTRL up
    time.sleep(0.06)
    
    # 4. Paste URL (Ctrl + V)
    user32.keybd_event(0x11, 0, 0, 0)  # CTRL down
    user32.keybd_event(0x56, 0, 0, 0)  # 'V' down
    time.sleep(0.04)
    user32.keybd_event(0x56, 0, 2, 0)  # 'V' up
    user32.keybd_event(0x11, 0, 2, 0)  # CTRL up
    time.sleep(0.06)
    
    # 5. Press Enter (0x0D)
    scan_enter = user32.MapVirtualKeyW(0x0D, 0)
    user32.keybd_event(0x0D, scan_enter, 0, 0)
    time.sleep(0.04)
    user32.keybd_event(0x0D, scan_enter, 2, 0)
    print("URL navigation dispatched successfully!")

if __name__ == "__main__":
    navigate_active_browser_url("https://www.youtube.com/shorts")
