$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

Write-Host "Starting S&P Global x CRISIL Platform..." -ForegroundColor Cyan

Start-Process powershell -WorkingDirectory $ProjectRoot -ArgumentList "-NoExit", "-Command", "python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload"
Start-Process powershell -WorkingDirectory (Join-Path $ProjectRoot "frontend") -ArgumentList "-NoExit", "-Command", "npm run dev -- --host"

Write-Host "Services launched successfully!" -ForegroundColor Green
Write-Host "Backend API:  http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "Frontend UI:  http://localhost:5173" -ForegroundColor Yellow

