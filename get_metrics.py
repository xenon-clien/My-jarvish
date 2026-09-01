import ctypes
user32 = ctypes.windll.user32
sw = user32.GetSystemMetrics(0)
sh = user32.GetSystemMetrics(1)
print(f"Screen Metrics: {sw}x{sh}")
