# release.ps1 - MetaData002 本地一键发布
# Usage: .\scripts\release.ps1 [-m "commit message"]
#   1) 检查 git 有无变更（无变更直接退出）
#   2) 构建前端（vue-tsc + vite build，失败中止、不提交）
#   3) git add -A + commit（未传 -m 时交互输入）
#   4) git push origin master（push 前 pre-push hook 自动跑测试）
# 推送成功后，服务器上执行: bash /opt/metadata/deploy/sync.sh

param(
    [string]$Message = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

Write-Host '========================================' -ForegroundColor Cyan
Write-Host '  MetaData002 Release - Build + Commit + Push' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan

# 1. 检查 git 是否有变更
Push-Location $root
$changes = git status --porcelain
Pop-Location
if (-not $changes) {
    Write-Host 'No changes to commit. Done.' -ForegroundColor DarkYellow
    exit 0
}

# 2. 构建前端（失败中止，保证提交的代码可构建）
Write-Host 'Step 1/3 : Building frontend...' -ForegroundColor Cyan
Push-Location (Join-Path $root 'frontend')
& npm.cmd run build
$buildCode = $LASTEXITCODE
Pop-Location
if ($buildCode -ne 0) {
    Write-Host 'BUILD FAILED - aborted, nothing committed.' -ForegroundColor Red
    exit 1
}
Write-Host 'Build OK.' -ForegroundColor Green

# 3. 提交信息（未传 -m 则交互输入）
if (-not $Message) {
    $Message = Read-Host 'Commit message'
    if (-not $Message) {
        Write-Host 'Empty message, aborted.' -ForegroundColor Red
        exit 1
    }
}

# 4. add + commit + push
Write-Host 'Step 2/3 : git add + commit...' -ForegroundColor Cyan
Push-Location $root
git add -A
git commit -m $Message
Write-Host 'Step 3/3 : git push origin master...' -ForegroundColor Cyan
git push origin master
$pushCode = $LASTEXITCODE
Pop-Location

if ($pushCode -eq 0) {
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host 'Pushed OK.' -ForegroundColor Green
    Write-Host 'Next : 服务器上执行 bash /opt/MetaData002/deploy/sync.sh' -ForegroundColor Cyan
    Write-Host '========================================' -ForegroundColor Cyan
} else {
    Write-Host 'PUSH FAILED (pre-push 测试未过或网络问题，commit 已生成未推送)' -ForegroundColor Red
}
exit $pushCode
