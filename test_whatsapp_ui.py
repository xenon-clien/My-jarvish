import time
import win32gui
import win32process
import ctypes

def find_whatsapp_window():
    windows = []
    def enum_cb(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            c = win32gui.GetClassName(hwnd)
            if "whatsapp" in t.lower() or "whatsapp" in c.lower():
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if w > 200 and h > 200:
                    extra.append((hwnd, t, c, rect))
    win32gui.EnumWindows(enum_cb, windows)
    return windows

windows = find_whatsapp_window()
print(f"Found {len(windows)} WhatsApp Windows:")
for hwnd, t, c, rect in windows:
    print(f"HWND: {hwnd} | Title: '{t}' | Class: '{c}' | Rect: {rect}")

# Try UIAutomation to inspect buttons
try:
    import comtypes.client
    uia = comtypes.client.CreateObject("{ff48dba4-60ef-4201-aa87-54103eef594e}")
    if windows:
        hwnd = windows[0][0]
        elem = uia.ElementFromHandle(hwnd)
        print("\nSearching for Call buttons via UIAutomation...")
        # Search for buttons
        cond = uia.CreatePropertyCondition(30003, 50000) # ControlType = Button
        buttons = elem.FindAll(4, cond)
        print(f"Found {buttons.Length} buttons in WhatsApp:")
        for i in range(min(15, buttons.Length)):
            btn = buttons.GetElement(i)
            print(f"  Button {i}: Name='{btn.CurrentName}', AutomationId='{btn.CurrentAutomationId}', Rect={btn.CurrentBoundingRectangle.left},{btn.CurrentBoundingRectangle.top}")
except Exception as e:
    print(f"UIAutomation error: {e}")
