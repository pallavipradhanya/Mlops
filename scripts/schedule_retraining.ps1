# Registers a Windows Task Scheduler job that runs the retraining workflow daily at 02:00.
# (Alternative: set "Schedule hours" on the Settings page and let the API's built-in scheduler do it.)
param([string]$Time = "02:00", [string]$Trigger = "scheduled")
$root = (Resolve-Path "$PSScriptRoot\..").Path
$py = Join-Path $root ".venv\Scripts\python.exe"
$cmd = "`"$py`" `"$root\scripts\run_retraining.py`" --trigger $Trigger"
schtasks /Create /F /SC DAILY /ST $Time /TN "MLOps360-Retraining" /TR $cmd
Write-Host "Created task MLOps360-Retraining. Remove with: schtasks /Delete /TN MLOps360-Retraining /F"
