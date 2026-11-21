# Runbook: start the workbench server

URL: http://127.0.0.1:8760

1. Check if it runs: `curl http://127.0.0.1:8760/`. Code 200 means it runs. Stop here.
2. Start it hidden: `wscript //B scripts\start-workbench-hidden.vbs` (run it in the background).
3. Wait 5 seconds. Run the curl check again.
4. To restart: run `close-workbench-servers.ps1` first, then step 2.

Do not use `start-workbench.cmd`. It opens a window and ends in `pause`.
