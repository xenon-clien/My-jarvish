import ctypes
import time

user32 = ctypes.windll.user32

def test_hardware_key(vk_code):
    scan_code = user32.MapVirtualKeyW(vk_code, 0)
    print(f"VK 0x{vk_code:02X} -> ScanCode 0x{scan_code:02X}")
    return scan_code

print("Checking Hardware Scan Codes for YouTube shortcuts:")
test_hardware_key(0x4B)  # 'K'
test_hardware_key(0x4C)  # 'L'
test_hardware_key(0x4A)  # 'J'
test_hardware_key(0x20)  # Space
test_hardware_key(0x46)  # 'F' (Fullscreen)
test_hardware_key(0x54)  # 'T' (Theater)
test_hardware_key(0x43)  # 'C' (Captions)
test_hardware_key(0x4D)  # 'M' (Mute)
test_hardware_key(0x30)  # '0' (Replay)
test_hardware_key(0xB3)  # VK_MEDIA_PLAY_PAUSE
test_hardware_key(0x28)  # VK_DOWN
test_hardware_key(0x26)  # VK_UP
