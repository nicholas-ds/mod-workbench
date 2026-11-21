@echo off
rem One click: close every old workbench server, then start the one on 8760.
rem When the window says the server runs, refresh the browser at http://127.0.0.1:8760
cd /d "%~dp0"
echo Closing old workbench servers...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0close-workbench-servers.ps1"
echo Starting the workbench...
call "%~dp0start-workbench.cmd"
