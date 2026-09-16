#!/bin/bash

echo "========================================================"
echo "       Video-to-Clips AI - One-Click Installer"
echo "========================================================"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 is not installed or not in your PATH."
    echo "Please install Python from https://www.python.org/downloads/"
    exit 1
fi

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js is not installed or not in your PATH."
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

echo "[1/4] Setting up Python Virtual Environment..."
cd backend || exit
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo "[2/4] Installing Python Dependencies (This might take a minute the first time)..."
pip install -r requirements.txt

echo "[3/4] Installing Frontend Dependencies..."
cd ../frontend || exit
npm install

echo "[4/4] Starting Application Servers..."
echo "Clearing any stale python/node processes on ports 8000 and 5173..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null

# Start backend in background
cd ../backend || exit
echo "Starting Backend Server..."
nohup uvicorn main:app --host 127.0.0.1 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!

# Start frontend in background
cd ../frontend || exit
echo "Starting Frontend Server..."
nohup npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!

echo ""
echo "========================================================"
echo "       SUCCESS! Application is running in the background."
echo "========================================================"
echo "Opening browser to http://localhost:5173..."
sleep 3

# Attempt to open browser automatically
if command -v open &> /dev/null; then
    open http://localhost:5173
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5173
else
    echo "Please open your browser and go to http://localhost:5173"
fi

echo ""
echo "⚠️  IMPORTANT: To stop the servers and exit the application,"
echo "simply close this terminal window or press Ctrl+C."
trap "kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT SIGTERM
wait
