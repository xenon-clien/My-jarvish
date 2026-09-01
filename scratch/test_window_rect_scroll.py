import win32gui
import win32con
import ctypes
import time
import os
import sys

user32 = ctypes.windll.user32

def test_window_rect_scroll():
    # Find Chrome window
    browser_windows = []
    def enum_cb(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd).lower()
            c = win32gui.GetClassName(hwnd).lower()
            if "youtube" in t or "chrome" in c or "edge" in c:
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if w > 400 and h > 300:
                    extra.append((hwnd, rect, t))
    win32gui.EnumWindows(enum_cb, browser_windows)
    
    if not browser_windows:
        print("No Chrome/Browser window detected.")
        return
        
    hwnd, rect, title = browser_windows[0]
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    print(f"Target Window: HWND {hwnd}, Title: '{title}'")
    print(f"Bounds: Left={left}, Top={top}, Right={right}, Bottom={bottom}, Width={width}, Height={height}")
    
    # Calculate exact right-hand margin inside Chrome
    scroll_x = int(left + width * 0.85)
    scroll_y = int(top + height * 0.55)
    print(f"Positioning Cursor at Webpage Body: ({scroll_x}, {scroll_y})")
    
    user32.SetCursorPos(scroll_x, scroll_y)
    time.sleep(0.05)
    
    # Dispatch wheel delta
    delta = -120
    raw_delta = ctypes.c_ulong(delta & 0xFFFFFFFF).value
    print("Dispatching 6 wheel notches...")
    for _ in range(6):
        user32.mouse_event(0x0800, 0, 0, raw_delta, 0)
        time.sleep(0.02)
        
    print("Scroll execution completed!")

if __name__ == "__main__":
    test_window_rect_scroll()
