@echo off
rem One click: close every old workbench server, then restart the detached one.
rem When the status says running, refresh the browser at http://127.0.0.1:8760
cd /d "%~dp0"
echo Closing old workbench servers...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0close-workbench-servers.ps1"
echo Restarting the workbench server...
.venv\Scripts\python.exe -m workbench server restart
.venv\Scripts\python.exe -m workbench server status
