@echo off
echo.
echo ========================================
echo   KILLING ALL BACKEND PROCESSES
echo ========================================
echo.

REM Kill all Python processes
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM pythonw.exe /T 2>nul

REM Wait a bit
timeout /t 2 /nobreak >nul

REM Check if port 8000 is still in use
netstat -ano | findstr ":8000" | findstr "LISTENING"

echo.
echo Port 8000 should be free now.
echo If you still see output above, you may need to restart your computer.
echo.
pause
