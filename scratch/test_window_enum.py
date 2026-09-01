import win32gui
import win32process
import win32con
import ctypes

user32 = ctypes.windll.user32

hwnds = []
def cb(h, _):
    hwnds.append(h)
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
user32.EnumWindows(WNDENUMPROC(cb), 0)

print(f"Total HWNDs found via ctypes: {len(hwnds)}")
for h in hwnds:
    length = user32.GetWindowTextLengthW(h)
    if length > 0:
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(h, buff, length + 1)
        title = buff.value
        cls_buff = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(h, cls_buff, 256)
        cls = cls_buff.value
        if user32.IsWindowVisible(h) and any(k in title.lower() or k in cls.lower() for k in ["chrome", "youtube", "edge", "cmd", "antigravity"]):
            print(f"  [Visible] HWND={h} | Class='{cls}' | Title='{title}'")
