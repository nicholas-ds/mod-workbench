@echo off
rem Start the detached workbench server. Open http://127.0.0.1:8760 in a browser.
cd /d "%~dp0"
if not defined WORKBENCH_ROOTS set WORKBENCH_ROOTS=%~dp0..
rem Run "python -m workbench serve" by hand for a foreground server.
.venv\Scripts\python.exe -m workbench server start
