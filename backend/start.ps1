# PowerShell script to start the Tavern Backend Server

Write-Host "🚀 Starting Tavern Backend Server..." -ForegroundColor Green
Write-Host ""

# Check if venv exists
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run setup.bat first to create the virtual environment." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "🔁 Using virtual environment..." -ForegroundColor Cyan
Write-Host "🌐 Starting server on 0.0.0.0:8000 (accessible from network)" -ForegroundColor Cyan
Write-Host ""

# Set storage backend to sqlalchemy for auth support
$env:STORAGE_BACKEND = "sqlalchemy"

# Disable Alembic to prevent database drops on schema conflicts
# This allows the database to persist across restarts while still creating missing tables
$env:USE_ALEMBIC = "false"

# Start the server
& ".\venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

