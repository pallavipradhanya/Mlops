# Starts MLflow UI (5000), the API (8000) and the dashboard (3000), each in its own window.
$root = (Resolve-Path "$PSScriptRoot\..").Path
$py = Join-Path $root ".venv\Scripts\python.exe"
New-Item -ItemType Directory -Force "$root\artifacts" | Out-Null
$db = ($root -replace '\\','/') + "/artifacts/mlflow.db"

Start-Process powershell -ArgumentList "-NoExit","-Command","& '$py' -m mlflow ui --backend-store-uri sqlite:///$db --port 5000" -WorkingDirectory $root
Start-Process powershell -ArgumentList "-NoExit","-Command","& '$py' -m uvicorn app.main:app --port 8000" -WorkingDirectory "$root\backend"
Start-Process powershell -ArgumentList "-NoExit","-Command","npm run dev" -WorkingDirectory "$root\frontend"
Write-Host "Dashboard: http://localhost:3000   API docs: http://localhost:8000/docs   MLflow: http://localhost:5000"
