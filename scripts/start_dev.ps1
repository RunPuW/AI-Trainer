param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CyberTrainer development environment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$rootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $rootDir

Write-Host "`n[1/4] Checking Python..." -ForegroundColor Yellow
python --version

Write-Host "`n[2/4] Checking Node.js..." -ForegroundColor Yellow
node --version

$nodeCanSpawn = $false
try {
    node -e "const cp=require('child_process'); const r=cp.spawnSync('cmd.exe',['/c','echo ok'],{encoding:'utf8'}); process.exit(r.error ? 1 : 0)"
    $nodeCanSpawn = ($LASTEXITCODE -eq 0)
} catch {
    $nodeCanSpawn = $false
}

if (-not $nodeCanSpawn) {
    Write-Host "Warning: Node child_process spawn is blocked in this Windows environment." -ForegroundColor Yellow
    Write-Host "Vite dev server will be skipped; FastAPI will serve frontend/dist instead." -ForegroundColor Yellow
}

Write-Host "`n[3/4] Initializing database..." -ForegroundColor Yellow
python scripts/init_db.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: database initialization returned a non-zero exit code." -ForegroundColor Yellow
}

Write-Host "`n[4/4] Starting services..." -ForegroundColor Yellow

Write-Host "Starting backend on http://localhost:$BackendPort ..." -ForegroundColor Green
$backendJob = Start-Job -ScriptBlock {
    param($RootDir, $Port)
    Set-Location $RootDir
    python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port $Port
} -ArgumentList $rootDir, $BackendPort

Start-Sleep -Seconds 3

if ($nodeCanSpawn) {
    Write-Host "Starting frontend dev server on http://localhost:$FrontendPort ..." -ForegroundColor Green
    $frontendJob = Start-Job -ScriptBlock {
        param($RootDir, $Port)
        Set-Location (Join-Path $RootDir "frontend")
        npm run dev -- --host 0.0.0.0 --port $Port
    } -ArgumentList $rootDir, $FrontendPort
} else {
    $frontendJob = $null
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Services started" -ForegroundColor Green
Write-Host "  Backend: http://localhost:$BackendPort" -ForegroundColor Green
if ($nodeCanSpawn) {
    Write-Host "  Frontend: http://localhost:$FrontendPort" -ForegroundColor Green
} else {
    Write-Host "  Frontend: http://localhost:$BackendPort (served from frontend/dist)" -ForegroundColor Green
}
Write-Host "  API docs: http://localhost:$BackendPort/docs" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nPress Ctrl+C to stop all services." -ForegroundColor Yellow

try {
    while ($true) {
        Start-Sleep -Seconds 1

        if ($backendJob.State -eq "Failed") {
            Write-Host "Backend service failed:" -ForegroundColor Red
            Receive-Job $backendJob
            break
        }

        if ($frontendJob -and $frontendJob.State -eq "Failed") {
            Write-Host "Frontend service failed:" -ForegroundColor Red
            Receive-Job $frontendJob
            break
        }
    }
}
finally {
    Write-Host "`nStopping services..." -ForegroundColor Yellow
    Stop-Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob -Force -ErrorAction SilentlyContinue
    if ($frontendJob) {
        Stop-Job $frontendJob -ErrorAction SilentlyContinue
        Remove-Job $frontendJob -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Services stopped." -ForegroundColor Green
}
