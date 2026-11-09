param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path -LiteralPath 'dashboard/frontend/dist/index.html')) {
    Push-Location -LiteralPath 'dashboard/frontend'
    try {
        if (-not (Test-Path -LiteralPath 'node_modules')) {
            & npm.cmd ci --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed' }
        }
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
    } finally { Pop-Location }
}

$bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
Write-Host "Open http://127.0.0.1:$Port — Ctrl+C stops collection."
if (Test-Path -LiteralPath $bundledPython) {
    & $bundledPython -m dashboard.server --port $Port
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m dashboard.server --port $Port
} else {
    & py -3 -m dashboard.server --port $Port
}
