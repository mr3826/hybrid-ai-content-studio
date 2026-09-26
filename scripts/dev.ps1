# Local Development Launcher for Fresh Local AI Content Studio (PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting Fresh Local AI Content Studio (Local-First)   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Setup Python Environment if not present
if (-not (Test-Path ".venv")) {
    Write-Host "[1/4] Creating Python virtual environment with uv..." -ForegroundColor Yellow
    uv venv .venv
}

# 2. Sync backend dependencies
Write-Host "[2/4] Syncing Python dependencies..." -ForegroundColor Yellow
& .venv/Scripts/python -m pip install -e .

# 3. Check Web dependencies
if (-not (Test-Path "apps/web/node_modules")) {
    Write-Host "[3/4] Installing web dependencies..." -ForegroundColor Yellow
    npm --prefix apps/web install
}

Write-Host "[4/4] Starting API, Worker, and Web Dev Servers..." -ForegroundColor Green
Write-Host "API:     http://localhost:8400" -ForegroundColor Cyan
Write-Host "Web:     http://localhost:3000" -ForegroundColor Cyan
Write-Host "Worker:  Background daemon polling SQLite" -ForegroundColor Cyan

# Start API in background job
$apiJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location $root
    & .venv/Scripts/uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8400 --reload
} -ArgumentList (Get-Location).Path

# Start Worker in background job
$workerJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location $root
    & .venv/Scripts/python worker/worker.py
} -ArgumentList (Get-Location).Path

# Start Next.js frontend in current process
try {
    npm --prefix apps/web run dev
} finally {
    Write-Host "Stopping background jobs..." -ForegroundColor Yellow
    Stop-Job $apiJob, $workerJob -ErrorAction SilentlyContinue
    Remove-Job $apiJob, $workerJob -ErrorAction SilentlyContinue
}
