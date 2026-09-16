@echo off
echo ========================================================
echo        Video-to-Clips AI - One-Click Installer
echo ========================================================
echo.

:: Check for Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo IMPORTANT: Make sure to check the box "Add Python to PATH" during installation.
    pause
    exit /b
)

:: Check for Node.js
node --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js is not installed or not in your PATH.
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b
)

echo [1/4] Setting up Python Virtual Environment...
cd backend
IF NOT EXIST "venv" (
    python -m venv venv
)
call venv\Scripts\activate.bat

echo [2/4] Installing Python Dependencies (This might take a minute the first time)...
pip install -r requirements.txt

echo [3/4] Installing Frontend Dependencies...
cd ../frontend
call npm install

echo [4/4] Starting Application Servers...
:: Go back to project root
cd ..

echo Clearing any stale python/node processes on ports 8000 and 5173...
powershell -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Where-Object { (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName -eq 'python' } | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1
powershell -Command "Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | Where-Object { (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName -eq 'node' } | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo Starting Backend AI Engine in a new window...
start "Video AI Backend" cmd /k "cd backend && call venv\Scripts\activate.bat && uvicorn main:app --host 127.0.0.1 --port 8000"

echo Starting Frontend User Interface in a new window...
start "Video AI Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================================
echo        SUCCESS! Application is booting up...
echo ========================================================
echo Opening Google Chrome to http://localhost:5173 ...
timeout /t 3 /nobreak >nul
start http://localhost:5173
echo.
echo ⚠️ IMPORTANT: Do not close the two black terminal windows that just opened!
echo They are keeping your application running.
echo.
echo Press any key to exit this installer screen...
pause >nul
