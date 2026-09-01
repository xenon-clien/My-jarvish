import win32gui

def enum_all(hwnd, extra):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if title:
            cls = win32gui.GetClassName(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            extra.append((hwnd, title, cls, rect, w, h))

windows = []
win32gui.EnumWindows(enum_all, windows)
print(f"=== ALL VISIBLE TITLED WINDOWS ({len(windows)}) ===")
for hwnd, title, cls, rect, w, h in windows:
    print(f"HWND {hwnd:8} | Class: {cls:25} | Size: {w:4}x{h:4} | Rect: {rect} | Title: '{title}'")
