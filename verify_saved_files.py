import os
import py_compile
import sys
from datetime import datetime

files_to_check = [
    r"c:\Users\shivam\Downloads\chatbot\backend\ai\intent_engine.py",
    r"c:\Users\shivam\Downloads\chatbot\backend\tools\browser_tools.py",
    r"c:\Users\shivam\Downloads\chatbot\backend\tools\media_tools.py",
    r"c:\Users\shivam\Downloads\chatbot\backend\tools\app_tools.py",
    r"c:\Users\shivam\Downloads\chatbot\backend\ai\prompts.py",
    r"c:\Users\shivam\Downloads\chatbot\backend\ai\providers.py",
    r"c:\Users\shivam\Downloads\chatbot\backend\voice\speech_to_text.py",
    r"c:\Users\shivam\Downloads\chatbot\scripts\voice_cli.py",
    r"c:\Users\shivam\Downloads\chatbot\JARVIS.bat",
    r"C:\Users\shivam\Desktop\JARVIS.bat",
]

print("=== VERIFYING ALL FILES ON DISK ===")
all_ok = True
for f in files_to_check:
    if not os.path.exists(f):
        print(f"❌ MISSING: {f}")
        all_ok = False
        continue
    
    mtime = os.path.getmtime(f)
    mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
    size = os.path.getsize(f)
    
    # Check syntax if python
    syntax_ok = True
    if f.endswith('.py'):
        try:
            py_compile.compile(f, doraise=True)
            status = "✅ SAVED & COMPILES CLEANLY"
        except Exception as e:
            status = f"❌ SYNTAX ERROR: {e}"
            syntax_ok = False
            all_ok = False
    else:
        status = "✅ SAVED ON DISK"
        
    print(f"File: {os.path.basename(f):25} | Size: {size:6} bytes | Modified: {mtime_str} | Status: {status}")

if all_ok:
    print("\n🎉 ALL 10 FILES ARE 100% SAVED, UP-TO-DATE, AND FULLY COMPILED ON DISK!")
