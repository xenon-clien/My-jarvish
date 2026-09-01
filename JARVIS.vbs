Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "c:\Users\shivam\Downloads\chatbot"
WshShell.Run "pythonw.exe app.py", 0, False
