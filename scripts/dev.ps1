# dev.ps1 - MetaData002 前后端一键启动/停止/状态
# Usage: .\scripts\dev.ps1 start|stop|status
#   start  : 后台启动前后端（不随终端退出），日志写入 output/logs/
#   stop   : 停止前后端（按 PID 文件）
#   status : 查看前后端运行状态
# 幂等：端口已监听则跳过启动，重复执行安全

param(
    [ValidateSet('start', 'stop', 'status')]
    [string]$Action = 'status'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $root 'output\logs'
$backendPidFile = Join-Path $logDir 'backend.pid'
$frontendPidFile = Join-Path $logDir 'frontend.pid'

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

function Test-Port {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return [bool]$conn
}

function Get-RunningPid {
    param([string]$PidFile)
    if (-not (Test-Path $PidFile)) { return $null }
    $savedPid = (Get-Content $PidFile).Trim()
    if (-not $savedPid) { return $null }
    if (Get-Process -Id $savedPid -ErrorAction SilentlyContinue) { return $savedPid }
    return $null
}

# 停止指定端口的监听进程（npm.cmd/python 拉起后实际监听是子进程，兜底清理）
function Stop-PortOwner {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        foreach ($c in $conn) {
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
            Write-Host "  port ${Port}: killed listener PID=$($c.OwningProcess)" -ForegroundColor Green
        }
    }
}

switch ($Action) {
    'start' {
        Write-Host '========================================' -ForegroundColor Cyan
        Write-Host '  MetaData002 Dev Services - Start' -ForegroundColor Cyan
        Write-Host '========================================' -ForegroundColor Cyan

        # 后端
        if (Test-Port 8000) {
            Write-Host 'Backend  : already running on :8000 (skip)' -ForegroundColor DarkYellow
        } else {
            $py = Join-Path $root 'backend\venv\Scripts\python.exe'
            $managePy = Join-Path $root 'backend\manage.py'
            $outLog = Join-Path $logDir 'backend.out.log'
            $errLog = Join-Path $logDir 'backend.err.log'
            $p = Start-Process -FilePath $py -ArgumentList @($managePy, 'runserver', '8000', '--noreload') `
                -WorkingDirectory (Join-Path $root 'backend') `
                -RedirectStandardOutput $outLog -RedirectStandardError $errLog `
                -WindowStyle Hidden -PassThru
            $p.Id | Set-Content $backendPidFile
            Write-Host "Backend  : started PID=$($p.Id) -> http://localhost:8000" -ForegroundColor Green
        }

        # 前端
        if (Test-Port 3000) {
            Write-Host 'Frontend : already running on :3000 (skip)' -ForegroundColor DarkYellow
        } else {
            $npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
            if (-not $npm) {
                Write-Host 'Frontend : npm not found, skip' -ForegroundColor Red
            } else {
                $outLog = Join-Path $logDir 'frontend.out.log'
                $errLog = Join-Path $logDir 'frontend.err.log'
                $p = Start-Process -FilePath $npm -ArgumentList @('run', 'dev') `
                    -WorkingDirectory (Join-Path $root 'frontend') `
                    -RedirectStandardOutput $outLog -RedirectStandardError $errLog `
                    -WindowStyle Hidden -PassThru
                $p.Id | Set-Content $frontendPidFile
                Write-Host "Frontend : started PID=$($p.Id) -> http://localhost:3000" -ForegroundColor Green
            }
        }

        Write-Host ''
        Write-Host 'Logs: ' -NoNewline
        Write-Host $logDir -ForegroundColor DarkGray
        Write-Host 'Open : ' -NoNewline
        Write-Host 'http://localhost:3000' -ForegroundColor Cyan
        Write-Host '========================================' -ForegroundColor Cyan
    }

    'stop' {
        Write-Host 'Stopping MetaData002 dev services...'
        $stopped = 0
        foreach ($entry in @(@{Name='Backend'; File=$backendPidFile; Port=8000}, @{Name='Frontend'; File=$frontendPidFile; Port=3000})) {
            $procId = Get-RunningPid $entry.File
            if ($procId) {
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                Remove-Item $entry.File -ErrorAction SilentlyContinue
                Write-Host "  $($entry.Name): stopped PID=$procId" -ForegroundColor Green
                $stopped++
            }
            # 兜底：父进程可能已退、子进程仍占端口（npm.cmd -> node 等）
            Stop-PortOwner $entry.Port
        }
        if ($stopped -eq 0) { Write-Host 'Done (no pid files found, port owners cleaned if any).' -ForegroundColor DarkGray }
    }

    'status' {
        Write-Host 'MetaData002 dev services status:'
        foreach ($entry in @(@{Name='Backend'; File=$backendPidFile; Port=8000}, @{Name='Frontend'; File=$frontendPidFile; Port=3000})) {
            $procId = Get-RunningPid $entry.File
            if ($procId) {
                Write-Host "  $($entry.Name): RUNNING PID=$procId (port $($entry.Port))" -ForegroundColor Green
            } elseif (Test-Port $entry.Port) {
                Write-Host "  $($entry.Name): RUNNING on port $($entry.Port) (not via this script)" -ForegroundColor DarkYellow
            } else {
                Write-Host "  $($entry.Name): STOPPED" -ForegroundColor Red
            }
        }
    }
}
