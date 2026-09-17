@echo off
title Antigravity Quant AI Trading Terminal
echo ===================================================
echo   ANTIGRAVITY QUANT AI TRADING TERMINAL
echo   Light-Theme Institutional Dashboard
echo   Starting server at http://127.0.0.1:8500
echo ===================================================
echo.
py -m uvicorn server.main:app --host 127.0.0.1 --port 8500 --reload
pause
