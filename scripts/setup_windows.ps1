# One-time setup for running WITHOUT Docker. Run from the project root in PowerShell.
$ErrorActionPreference = "Stop"
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
Push-Location frontend; npm install; Pop-Location
Write-Host "Setup complete. Start everything with: .\scripts\start_local.ps1"
