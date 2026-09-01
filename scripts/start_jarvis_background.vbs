Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "c:\Users\shivam\Downloads\chatbot"
WshShell.Run """C:\Python314\pythonw.exe"" ""c:\Users\shivam\Downloads\chatbot\scripts\clap_listener.py""", 0, False
