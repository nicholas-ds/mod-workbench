@echo off
rem Start the workbench. Open http://127.0.0.1:8760 in a browser.
cd /d "%~dp0"
set WORKBENCH_ROOTS=E:\repos\mods
.venv\Scripts\python.exe -m workbench serve
pause
