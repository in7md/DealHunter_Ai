@echo off
title DealHunter AI Launcher
echo ==========================================
echo       Starting DealHunter AI System
echo ==========================================

echo [1/2] Launching Backend on http://127.0.0.1:8000 ...
start "DealHunter Backend" cmd /k "cd /d %~dp0backend && .\venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] Launching Frontend on http://localhost:3000 ...
start "DealHunter Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ==========================================
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://localhost:3000
echo ==========================================
pause
