@echo off
echo Starting S&P Global x CRISIL Platform...
start "Backend API Server" cmd /k "python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload"
cd frontend
start "Frontend UI Console" cmd /k "npm run dev -- --host"
echo Services launched!
echo Backend Swagger Docs: http://localhost:8000/docs
echo Frontend Dashboard:   http://localhost:5173
