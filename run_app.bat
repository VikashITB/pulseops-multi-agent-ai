@echo off
docker compose up -d
timeout /t 5 >nul
start http://localhost:3001
