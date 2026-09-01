import win32gui

windows = []
def enum_all(hwnd, extra):
    if win32gui.IsWindowVisible(hwnd):
        t = win32gui.GetWindowText(hwnd)
        c = win32gui.GetClassName(hwnd)
        rect = win32gui.GetWindowRect(hwnd)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        if w > 100 and h > 100 and t:
            windows.append((hwnd, t, c, rect))

win32gui.EnumWindows(enum_all, windows)
print(f"Total Visible Windows: {len(windows)}")
for hwnd, t, c, rect in windows:
    print(f"HWND {hwnd:8d} | Class: {c:25s} | Rect: {rect} | Title: '{t}'")
