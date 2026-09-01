import sys

for pkg in ["playwright", "sentry_sdk", "pytest", "fastapi", "httpx", "pydantic", "win32gui"]:
    try:
        mod = __import__(pkg)
        ver = getattr(mod, "__version__", "installed")
        print(f"✅ {pkg}: {ver}")
    except ImportError as e:
        print(f"❌ {pkg}: Not installed ({e})")
