param(
    [int]$BackendPort = 8000,
    [int]$HealthTimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$runtimeDir = Join-Path $rootDir ".runtime"
$pidFile = Join-Path $runtimeDir "backend.pid"

function Get-PortPid {
    param([int]$Port)

    $line = netstat -ano | Select-String ":$Port" | Where-Object {
        $_ -match "LISTENING"
    } | Select-Object -First 1

    if (-not $line) {
        return $null
    }

    return [int](([string]$line).Trim() -split "\s+")[-1]
}

function Wait-Healthy {
    param(
        [int]$Port,
        [int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 2
        $health = ""
        $exitCode = 1
        try {
            $health = & curl.exe --silent --show-error --max-time 3 "http://localhost:$Port/api/health" 2>&1
            $exitCode = $LASTEXITCODE
        } catch {
            $health = $_.Exception.Message
            $exitCode = 1
        }
        if ($exitCode -eq 0 -and $health -match '"status"\s*:\s*"ok"') {
            Write-Host "Backend healthy: $health" -ForegroundColor Green
            return $true
        }
        Write-Host "Waiting for backend: $health" -ForegroundColor DarkYellow
    }

    return $false
}

New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
Set-Location $rootDir

Write-Host "CyberTrainer Web startup" -ForegroundColor Cyan
Write-Host "Root: $rootDir"

$existingPid = Get-PortPid -Port $BackendPort
if ($existingPid) {
    Write-Host "Stopping existing process on port ${BackendPort}: PID $existingPid" -ForegroundColor Yellow
    Stop-Process -Id $existingPid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 800
}

Write-Host "Starting backend on http://localhost:$BackendPort ..." -ForegroundColor Green
$process = Start-Process `
    -FilePath "python" `
    -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "$BackendPort") `
    -WorkingDirectory $rootDir `
    -WindowStyle Hidden `
    -PassThru

Set-Content -Path $pidFile -Value $process.Id -Encoding ASCII

if (-not (Wait-Healthy -Port $BackendPort -TimeoutSeconds $HealthTimeoutSeconds)) {
    Write-Host "Backend did not become healthy within $HealthTimeoutSeconds seconds. Stopping PID $($process.Id)." -ForegroundColor Red
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
    exit 1
}

Write-Host ""
Write-Host "Ready for review:" -ForegroundColor Cyan
Write-Host "  Web UI:   http://localhost:$BackendPort"
Write-Host "  API docs: http://localhost:$BackendPort/docs"
Write-Host "  PID file: $pidFile"
