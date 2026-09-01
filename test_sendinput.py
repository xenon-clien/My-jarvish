import ctypes
import time

user32 = ctypes.windll.user32

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class INPUT_I(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("ii", INPUT_I),
    ]

def send_hardware_click(x, y):
    user32.SetCursorPos(x, y)
    time.sleep(0.05)
    
    # MOUSEEVENTF_LEFTDOWN = 0x0002, MOUSEEVENTF_LEFTUP = 0x0004
    inp_down = INPUT(type=0, ii=INPUT_I(mi=MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=0x0002, time=0, dwExtraInfo=None)))
    inp_up = INPUT(type=0, ii=INPUT_I(mi=MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=0x0004, time=0, dwExtraInfo=None)))
    
    user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
    time.sleep(0.04)
    user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
    time.sleep(0.05)
    user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
    time.sleep(0.04)
    user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
    print(f"Sent hardware click to ({x}, {y})")

send_hardware_click(500, 500)
