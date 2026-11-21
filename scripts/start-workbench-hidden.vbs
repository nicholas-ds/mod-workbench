Set s = CreateObject("WScript.Shell")
s.CurrentDirectory = "E:\repos\mods\mod-workbench"
s.Environment("Process")("WORKBENCH_ROOTS") = "E:\repos\mods"
s.Run "E:\repos\mods\mod-workbench\.venv\Scripts\python.exe -m workbench serve", 0, False
