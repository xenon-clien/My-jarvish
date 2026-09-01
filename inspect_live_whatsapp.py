import win32gui
import psutil

print("Scanning for WhatsApp processes & windows...")
wa_procs = []
for p in psutil.process_iter(['pid', 'name']):
    if "whatsapp" in p.info['name'].lower():
        wa_procs.append(p.info)

print(f"WhatsApp processes found: {wa_procs}")

wa_windows = []
def enum_cb(hwnd, extra):
    if win32gui.IsWindowVisible(hwnd):
        t = win32gui.GetWindowText(hwnd)
        c = win32gui.GetClassName(hwnd)
        if "whatsapp" in t.lower() or "whatsapp" in c.lower():
            extra.append((hwnd, t, c, win32gui.GetWindowRect(hwnd)))

win32gui.EnumWindows(enum_cb, wa_windows)
print(f"WhatsApp Windows visible on screen: {wa_windows}")
