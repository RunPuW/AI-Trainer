param(
    [int]$BackendPort = 8000
)

$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pidFile = Join-Path (Join-Path $rootDir ".runtime") "backend.pid"

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

$pids = @()
if (Test-Path $pidFile) {
    $savedPid = Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($savedPid) {
        $pids += [int]$savedPid
    }
}

$portPid = Get-PortPid -Port $BackendPort
if ($portPid) {
    $pids += $portPid
}

$pids = $pids | Select-Object -Unique
if (-not $pids -or $pids.Count -eq 0) {
    Write-Host "No backend process found on port $BackendPort." -ForegroundColor Yellow
    Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
    exit 0
}

foreach ($pid in $pids) {
    Write-Host "Stopping backend PID $pid" -ForegroundColor Yellow
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
}

Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
Write-Host "Backend stopped." -ForegroundColor Green
