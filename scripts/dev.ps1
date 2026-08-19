# dev.ps1 - MetaData002 前后端一键启动/停止/状态/看护
# Usage: .\scripts\dev.ps1 start|stop|status|watch
#   start  : 后台启动前后端（不随终端退出），日志写入 output/logs/
#   stop   : 停止前后端（按端口监听进程兜底清理）
#   status : 查看前后端运行状态（含真实 PID + HTTP 健康检查）
#   watch  : 前台看护循环，进程掉线自动拉起（Ctrl+C 退出）
# 幂等：端口已监听则跳过启动，重复执行安全
#
# 2026-08-19 加固：
#   - PID 一律以「实际监听端口进程」为准（Get-NetTCPConnection 反查），不再信任 Start-Process 返回值
#   - status 对后端做 HTTP 探活（区分「在跑/挂起/已停」），前端做首页探活
#   - 新增 watch 看护，自动拉起掉线进程，避免再出现「无声掉线」

param(
    [ValidateSet('start', 'stop', 'status', 'watch')]
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

# 返回监听指定端口的真实 PID 列表（去重）
function Get-PortPids {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $conn) { return @() }
    return @($conn | Select-Object -ExpandProperty OwningProcess -Unique)
}

# HTTP 健康检查：能拿到 HTTP 响应（含 401 等状态码）即视为存活
function Test-Health {
    param([int]$Port, [string]$Path)
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:$Port$Path" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop | Out-Null
        return $true
    } catch {
        # 401/403 等 HTTP 错误仍证明服务在响应
        if ($_.Exception.Response) { return $true }
        return $false
    }
}

# 停止指定端口的监听进程
function Stop-PortOwner {
    param([int]$Port)
    $pids = Get-PortPids $Port
    foreach ($pid_ in $pids) {
        Stop-Process -Id $pid_ -Force -ErrorAction SilentlyContinue
        Write-Host "  port ${Port}: killed listener PID=$pid_" -ForegroundColor Green
    }
}

# 记录真实监听 PID 到 pid 文件（启动后轮询等待端口就绪）
function Save-RealPid {
    param([int]$Port, [string]$PidFile, [string]$Name)
    $pids = @()
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 500
        $pids = Get-PortPids $Port
        if ($pids.Count -gt 0) { break }
    }
    if ($pids.Count -gt 0) {
        $pids[0] | Set-Content $PidFile
        Write-Host "  $Name : listening on :$Port PID=$($pids[0])" -ForegroundColor Green
        return $true
    } else {
        if (Test-Path $PidFile) { Remove-Item $PidFile -ErrorAction SilentlyContinue }
        Write-Host "  $Name : FAILED to start on :$Port (check logs)" -ForegroundColor Red
        return $false
    }
}

function Write-HealthStatus {
    param([string]$Name, [int]$Port, [string]$HealthPath)
    $pids = Get-PortPids $Port
    if ($pids.Count -eq 0) {
        Write-Host "  $Name : STOPPED" -ForegroundColor Red
        return
    }
    $alive = Test-Health $Port $HealthPath
    $pidStr = ($pids -join ',')
    if ($alive) {
        Write-Host "  $Name : RUNNING  PID=$pidStr  health=OK  (port $Port)" -ForegroundColor Green
    } else {
        Write-Host "  $Name : LISTENING but NOT RESPONDING  PID=$pidStr  (port $Port)" -ForegroundColor Yellow
    }
}

switch ($Action) {
    'start' {
        Write-Host '========================================' -ForegroundColor Cyan
        Write-Host '  MetaData002 Dev Services - Start' -ForegroundColor Cyan
        Write-Host '========================================' -ForegroundColor Cyan

        # 后端
        if (Test-Port 8000) {
            $pids = Get-PortPids 8000
            Write-Host "Backend  : already running on :8000 PID=$($pids -join ',') (skip)" -ForegroundColor DarkYellow
        } else {
            $py = Join-Path $root 'backend\venv\Scripts\python.exe'
            $managePy = Join-Path $root 'backend\manage.py'
            $outLog = Join-Path $logDir 'backend.out.log'
            $errLog = Join-Path $logDir 'backend.err.log'
            Start-Process -FilePath $py -ArgumentList @($managePy, 'runserver', '8000', '--noreload') `
                -WorkingDirectory (Join-Path $root 'backend') `
                -RedirectStandardOutput $outLog -RedirectStandardError $errLog `
                -WindowStyle Hidden
            Save-RealPid -Port 8000 -PidFile $backendPidFile -Name 'Backend'
        }

        # 前端
        if (Test-Port 3000) {
            $pids = Get-PortPids 3000
            Write-Host "Frontend : already running on :3000 PID=$($pids -join ',') (skip)" -ForegroundColor DarkYellow
        } else {
            $npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
            if (-not $npm) {
                Write-Host 'Frontend : npm not found, skip' -ForegroundColor Red
            } else {
                $outLog = Join-Path $logDir 'frontend.out.log'
                $errLog = Join-Path $logDir 'frontend.err.log'
                Start-Process -FilePath $npm -ArgumentList @('run', 'dev') `
                    -WorkingDirectory (Join-Path $root 'frontend') `
                    -RedirectStandardOutput $outLog -RedirectStandardError $errLog `
                    -WindowStyle Hidden
                Save-RealPid -Port 3000 -PidFile $frontendPidFile -Name 'Frontend'
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
        foreach ($entry in @(@{Name='Backend'; Port=8000; File=$backendPidFile}, @{Name='Frontend'; Port=3000; File=$frontendPidFile})) {
            if (Test-Path $entry.File) { Remove-Item $entry.File -ErrorAction SilentlyContinue }
            Stop-PortOwner $entry.Port
        }
        Write-Host 'Done.'
    }

    'status' {
        Write-Host 'MetaData002 dev services status:'
        Write-HealthStatus -Name 'Backend ' -Port 8000 -HealthPath '/api/domains/'
        Write-HealthStatus -Name 'Frontend' -Port 3000 -HealthPath '/'
    }

    'watch' {
        Write-Host '========================================' -ForegroundColor Cyan
        Write-Host '  Watchdog: 每 10 秒探活，掉线自动拉起' -ForegroundColor Cyan
        Write-Host '  按 Ctrl+C 退出' -ForegroundColor Cyan
        Write-Host '========================================' -ForegroundColor Cyan

        $py = Join-Path $root 'backend\venv\Scripts\python.exe'
        $managePy = Join-Path $root 'backend\manage.py'
        $npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
        $backendOut = Join-Path $logDir 'backend.out.log'
        $backendErr = Join-Path $logDir 'backend.err.log'
        $frontendOut = Join-Path $logDir 'frontend.out.log'
        $frontendErr = Join-Path $logDir 'frontend.err.log'

        function Start-Backend {
            Start-Process -FilePath $py -ArgumentList @($managePy, 'runserver', '8000', '--noreload') `
                -WorkingDirectory (Join-Path $root 'backend') `
                -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr -WindowStyle Hidden
            $ok = Save-RealPid -Port 8000 -PidFile $backendPidFile -Name 'Backend'
            Write-Host "  [$(Get-Date -Format HH:mm:ss)] backend auto-restarted" -ForegroundColor Green
        }
        function Start-Frontend {
            if (-not $npm) { Write-Host 'Frontend : npm not found' -ForegroundColor Red; return }
            Start-Process -FilePath $npm -ArgumentList @('run', 'dev') `
                -WorkingDirectory (Join-Path $root 'frontend') `
                -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr -WindowStyle Hidden
            $ok = Save-RealPid -Port 3000 -PidFile $frontendPidFile -Name 'Frontend'
            Write-Host "  [$(Get-Date -Format HH:mm:ss)] frontend auto-restarted" -ForegroundColor Green
        }

        try {
            while ($true) {
                if (-not (Test-Port 8000)) {
                    Write-Host "  [$(Get-Date -Format HH:mm:ss)] backend DOWN -> restarting" -ForegroundColor Yellow
                    Start-Backend
                } elseif (-not (Test-Health 8000 '/api/domains/')) {
                    Write-Host "  [$(Get-Date -Format HH:mm:ss)] backend not responding -> restarting" -ForegroundColor Yellow
                    Stop-PortOwner 8000
                    Start-Sleep -Seconds 1
                    Start-Backend
                }
                if (-not (Test-Port 3000)) {
                    Write-Host "  [$(Get-Date -Format HH:mm:ss)] frontend DOWN -> restarting" -ForegroundColor Yellow
                    Start-Frontend
                }
                Start-Sleep -Seconds 10
            }
        } finally {
            Write-Host ''
            Write-Host 'Watchdog stopped.' -ForegroundColor DarkGray
        }
    }
}