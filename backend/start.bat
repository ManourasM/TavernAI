@echo off
echo 🚀 Starting Tavern Backend Server...
echo.

REM Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo ❌ Virtual environment not found!
    echo Please run setup.bat first to create the virtual environment.
    echo.
    pause
    exit /b 1
)

echo 🔁 Using virtual environment...
echo 🌐 Starting server on 0.0.0.0:8000 (accessible from network)
echo.

REM Start the server with host 0.0.0.0 to allow network access
venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

