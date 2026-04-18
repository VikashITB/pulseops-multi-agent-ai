@echo off
title PulseOps AI Launcher
echo Starting PulseOps AI...

docker compose up -d

timeout /t 6 >nul

start http://localhost:3001

echo PulseOps AI started successfully.
pause
