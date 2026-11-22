@echo off
rem Start the workbench. Open http://127.0.0.1:8760 in a browser.
cd /d "%~dp0"
if not defined WORKBENCH_ROOTS set WORKBENCH_ROOTS=%~dp0..
.venv\Scripts\python.exe -m workbench serve
pause
