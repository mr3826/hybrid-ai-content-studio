# Backup Script for Fresh Local AI Content Studio (PowerShell)
$ErrorActionPreference = "Stop"

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupDir = "data/backups/backup-$Timestamp"

Write-Host "Creating backup snapshot at $BackupDir..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

# 1. Backup SQLite DB with SQLite online backup or copy if WAL is flushed
if (Test-Path "data/db/studio.sqlite") {
    Write-Host "Backing up studio.sqlite..." -ForegroundColor Yellow
    Copy-Item "data/db/studio.sqlite*" -Destination $BackupDir -Force
}

# 2. Backup configs
if (Test-Path "config") {
    Write-Host "Backing up configs..." -ForegroundColor Yellow
    Copy-Item -Recurse "config" -Destination "$BackupDir/config"
}

Write-Host "Backup completed successfully at $BackupDir" -ForegroundColor Green
