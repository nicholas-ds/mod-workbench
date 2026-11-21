# Close every workbench server process ("python -m workbench serve"). Prints what it closed.
# Run by restart-workbench.cmd. Safe: matches only workbench serve, no other python.
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*workbench serve*' } |
  ForEach-Object { Write-Host "closing pid $($_.ProcessId)"; Stop-Process -Id $_.ProcessId -Force }
