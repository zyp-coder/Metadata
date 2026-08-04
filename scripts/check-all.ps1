# check-all.ps1 - Run all checks (backend + frontend)
# Usage: .\scripts\check-all.ps1 from project root
# Exit code: 0 = all pass, 1 = some failed

$ErrorActionPreference = "Continue"
$script:failed = 0
$script:passed = 0
$script:skipped = 0

function Run-Check {
    param([string]$name, [scriptblock]$block)
    Write-Host ""
    Write-Host "--- $name ---"
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        & $block
        if ($LASTEXITCODE -eq 0) {
            $sw.Stop()
            $secs = [math]::Round($sw.Elapsed.TotalSeconds, 1)
            Write-Host "  PASS (${secs}s)" -ForegroundColor Green
            $script:passed++
        } else {
            $sw.Stop()
            $secs = [math]::Round($sw.Elapsed.TotalSeconds, 1)
            Write-Host "  FAIL (${secs}s)" -ForegroundColor Red
            $script:failed++
        }
    } catch {
        $sw.Stop()
        Write-Host "  ERROR: $_" -ForegroundColor Red
        $script:failed++
    }
}

Write-Host "========================================"
Write-Host "  MetaData002 Full Check"
Write-Host "========================================"
Write-Host ""

$root = Split-Path -Parent $PSScriptRoot

# Backend checks
$python = Join-Path $root "backend\venv\Scripts\python.exe"
$managePy = Join-Path $root "backend\manage.py"

if (-not (Test-Path $python)) {
    Write-Host "SKIP: backend venv not found" -ForegroundColor DarkYellow
    $script:skipped++
} else {
    Run-Check "Backend: Django check" {
        & $python $managePy check
    }

    Run-Check "Backend: Run tests" {
        Push-Location (Join-Path $root "backend")
        try { & $python $managePy test apps.modeling apps.archive --verbosity 2 } finally { Pop-Location }
    }
}

# Frontend checks
$frontendDir = Join-Path $root "frontend"

if (-not (Test-Path (Join-Path $frontendDir "package.json"))) {
    Write-Host "SKIP: frontend dir not found" -ForegroundColor DarkYellow
    $script:skipped++
} else {
    Run-Check "Frontend: TypeScript check" {
        Push-Location $frontendDir
        try { & npx vue-tsc --noEmit } finally { Pop-Location }
    }

    Run-Check "Frontend: Build check" {
        Push-Location $frontendDir
        try { & npx vite build --mode production 2>&1 | Select-Object -Last 5 } finally { Pop-Location }
    }
}

# Summary
Write-Host ""
Write-Host "========================================"
$summary = "  Result: $($script:passed) passed, $($script:failed) failed, $($script:skipped) skipped"
if ($script:failed -gt 0) {
    Write-Host $summary -ForegroundColor Red
} else {
    Write-Host $summary -ForegroundColor Green
}
Write-Host "========================================"

if ($script:failed -gt 0) { exit 1 } else { exit 0 }
