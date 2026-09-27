# Local Test Runner for Fresh Local AI Content Studio (PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Running Content Studio Test Suite                     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Run Python pytest
Write-Host "[1/2] Running Backend, Engine & Worker unit tests with pytest..." -ForegroundColor Yellow
uv run pytest apps/api/tests apps/api/app/engines worker/tests -v

# 2. Run Next.js build validation
Write-Host "[2/2] Running Frontend build & TypeScript validation..." -ForegroundColor Yellow
npm --prefix apps/web run build

Write-Host "==========================================================" -ForegroundColor Green
Write-Host " All local tests and builds passed successfully!         " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
