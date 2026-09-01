import win32gui
import win32process
import win32api
import win32con
import ctypes

user32 = ctypes.windll.user32

print("Scanning all open windows on Desktop...")
windows = []

def enum_cb(hwnd, extra):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        if title.strip():
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            extra.append((hwnd, pid, cls, title))

win32gui.EnumWindows(enum_cb, windows)

print(f"Found {len(windows)} visible windows:")
for h, p, c, t in windows:
    if any(k in t.lower() or k in c.lower() for k in ["chrome", "youtube", "edge", "cmd", "antigravity"]):
        print(f"  HWND={h} | PID={p} | Class='{c}' | Title='{t}'")

# Test reliable AttachThreadInput focus
print("\nTesting reliable Windows Foreground Focus on Chrome...")
chrome_hwnds = [h for h, p, c, t in windows if "chrome" in c.lower() or "youtube" in t.lower()]
if chrome_hwnds:
    target_hwnd = chrome_hwnds[0]
    print(f"Targeting Chrome HWND: {target_hwnd}")
    
    # 1. Attach Thread Input
    fore_hwnd = win32gui.GetForegroundWindow()
    cur_thread = win32api.GetCurrentThreadId()
    target_thread, _ = win32process.GetWindowThreadProcessId(target_hwnd)
    
    if cur_thread != target_thread:
        user32.AttachThreadInput(cur_thread, target_thread, True)
        user32.AllowSetForegroundWindow(-1)
        win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(target_hwnd)
        user32.AttachThreadInput(cur_thread, target_thread, False)
    
    import time
    time.sleep(0.1)
    new_fore = win32gui.GetForegroundWindow()
    print(f"New Foreground HWND: {new_fore} (Title: '{win32gui.GetWindowText(new_fore)}')")
else:
    print("No Chrome window found open right now.")
