import sys
import os
import time

out_file = r"c:\Users\shivam\Downloads\chatbot\call_test_report.txt"

with open(out_file, "w", encoding="utf-8") as f:
    f.write("Starting WhatsApp Call Diagnosis...\n")
    try:
        import win32gui
        windows = []
        def enum_cb(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                c = win32gui.GetClassName(hwnd)
                if "whatsapp" in t.lower() or "whatsapp" in c.lower():
                    extra.append((hwnd, t, c, win32gui.GetWindowRect(hwnd)))
        win32gui.EnumWindows(enum_cb, windows)
        f.write(f"Visible WhatsApp Windows: {len(windows)}\n")
        for w in windows:
            f.write(f"  Window: HWND={w[0]}, Title='{w[1]}', Class='{w[2]}', Rect={w[3]}\n")
            
        if not windows:
            f.write("⚠️ WhatsApp Desktop App is NOT open or visible on screen!\n")
            f.write("If WhatsApp is running inside Chrome (WhatsApp Web), Web version does NOT support Voice/Video calling API from desktop shortcuts.\n")
        else:
            f.write("✅ WhatsApp Desktop App window is OPEN and visible!\n")
    except Exception as e:
        f.write(f"Error during diagnosis: {e}\n")

print("Diagnosis finished.")
