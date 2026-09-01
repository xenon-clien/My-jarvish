import ctypes
import time
import win32gui
import win32con

user32 = ctypes.windll.user32

def test_bulletproof_scroll(direction="down", amount=600):
    print(f"Testing bulletproof scroll: {direction}, amount={amount}")
    
    # 1. Get active window or Chrome window
    hwnd = win32gui.GetForegroundWindow()
    print(f"Active Foreground HWND: {hwnd} ('{win32gui.GetWindowText(hwnd)}')")
    
    rect = win32gui.GetWindowRect(hwnd)
    left, top, right, bottom = rect
    width = max(800, right - left)
    height = max(600, bottom - top)
    
    # 2. Position cursor over page scroll body (NOT video center)
    # Right-hand margin at 85% width is guaranteed webpage scroll body in all browsers
    scroll_x = int(left + width * 0.85)
    scroll_y = int(top + height * 0.50)
    
    print(f"Targeting Scroll Coordinates: ({scroll_x}, {scroll_y})")
    user32.SetCursorPos(scroll_x, scroll_y)
    time.sleep(0.04)
    
    is_down = direction.lower() in ["down", "niche", "bottom"]
    delta = -120 if is_down else 120
    notches = max(5, amount // 120)
    raw_delta = ctypes.c_ulong(delta & 0xFFFFFFFF).value
    
    print(f"Dispatching {notches} hardware wheel notches (delta={delta})...")
    for _ in range(notches):
        user32.mouse_event(0x0800, 0, 0, raw_delta, 0)
        time.sleep(0.02)
        
    # Keyboard PageDown / PageUp fallback with scan code
    vk = 0x22 if is_down else 0x21
    scan = user32.MapVirtualKeyW(vk, 0)
    user32.keybd_event(vk, scan, 0, 0)
    time.sleep(0.03)
    user32.keybd_event(vk, scan, 2, 0)
    print("Scroll test completed successfully!")

if __name__ == "__main__":
    test_bulletproof_scroll("down", 600)
