# Cleanup Script for Fresh Local AI Content Studio (PowerShell)
param(
    [switch]$DryRun = $false
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Studio Local Storage Retention Cleanup                   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$Targets = @(
    "data/tmp",
    "data/cache",
    ".pytest_cache",
    "apps/api/.pytest_cache"
)

foreach ($Target in $Targets) {
    if (Test-Path $Target) {
        $Items = Get-ChildItem -Path $Target -Recurse -File -ErrorAction SilentlyContinue
        $Count = ($Items | Measure-Object).Count
        $Size = ($Items | Measure-Object -Property Length -Sum).Sum

        $SizeMB = [math]::Round($Size / 1MB, 2)
        Write-Host "Found $Count files in $Target ($SizeMB MB)" -ForegroundColor Yellow

        if (-not $DryRun) {
            Remove-Item "$Target/*" -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "Cleaned $Target" -ForegroundColor Green
        } else {
            Write-Host "[DryRun] Would delete files in $Target" -ForegroundColor Gray
        }
    }
}

Write-Host "Retention check completed." -ForegroundColor Green
