import win32gui

def enum_handler(hwnd, extra):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        rect = win32gui.GetWindowRect(hwnd)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        if w > 200 and h > 200 and (cls in ["Chrome_WidgetWin_1", "MozillaWindowClass"] or any(b in title.lower() for b in ["chrome", "edge", "youtube", "brave"])):
            extra.append((hwnd, title, cls, rect, w, h))

windows = []
win32gui.EnumWindows(enum_handler, windows)
print(f"=== FOUND {len(windows)} VISIBLE BROWSER WINDOWS ===")
for hwnd, title, cls, rect, w, h in windows:
    print(f"HWND: {hwnd} | Rect: {rect} | Size: {w}x{h} | Title: '{title}'")
