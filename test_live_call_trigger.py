import os
import time
import win32gui
import win32process
import ctypes

phone = "918054840494"
print(f"Opening WhatsApp chat for {phone}...")
os.system(f'start "" "whatsapp://send?phone={phone}"')

print("Waiting 2.5 seconds for WhatsApp window to render...")
time.sleep(2.5)

windows = []
def enum_cb(hwnd, extra):
    if win32gui.IsWindowVisible(hwnd):
        t = win32gui.GetWindowText(hwnd)
        c = win32gui.GetClassName(hwnd)
        if "whatsapp" in t.lower() or "whatsapp" in c.lower():
            extra.append((hwnd, t, c, win32gui.GetWindowRect(hwnd)))

win32gui.EnumWindows(enum_cb, windows)
print(f"Found WhatsApp windows: {windows}")

if windows:
    hwnd, t, c, rect = windows[0]
    print(f"Focusing window {hwnd}...")
    from backend.tools.browser_tools import force_foreground_window
    force_foreground_window(hwnd)
    time.sleep(0.3)
    
    # Try UIAutomation find voice call button
    try:
        import comtypes.client
        uia = comtypes.client.CreateObject("{ff48dba4-60ef-4201-aa87-54103eef594e}")
        root = uia.ElementFromHandle(hwnd)
        cond = uia.CreatePropertyCondition(30003, 50000) # Button
        btns = root.FindAll(4, cond)
        print(f"Total buttons found in WhatsApp UI: {btns.Length}")
        for i in range(btns.Length):
            b = btns.GetElement(i)
            name = b.CurrentName or ""
            aid = b.CurrentAutomationId or ""
            if "call" in name.lower() or "voice" in name.lower() or "audio" in name.lower():
                print(f"🎯 FOUND CALL BUTTON: Name='{name}', AutoId='{aid}', Rect={b.CurrentBoundingRectangle.left},{b.CurrentBoundingRectangle.top}")
    except Exception as e:
        print("UIAutomation error:", e)
