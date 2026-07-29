[CmdletBinding()]
param([string]$RepoRoot = ".")

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $RepoRoot).Path

$requiredFiles = @(
    "Cargo.toml",
    "build.py",
    ".gitmodules",
    ".github\workflows\build-saurus-remote-windows.yml",
    ".saurus\scripts\Apply-SaurusCustomization.ps1",
    ".saurus\tools\apply_saurus_ux_refresh.py",
    ".saurus\tools\verify_saurus_ux_refresh.py",
    ".saurus\tests\test_ux_refresh.py",
    "flutter\lib\desktop\pages\desktop_home_page.dart",
    "flutter\lib\desktop\pages\connection_page.dart",
    "libs\hbb_common\src\config.rs"
)

$missing = @()
foreach ($relative in $requiredFiles) {
    $full = Join-Path $root $relative
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
        $missing += $relative
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Project verification failed. Missing files:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    exit 1
}

$workflow = Get-Content -LiteralPath (Join-Path $root ".github\workflows\build-saurus-remote-windows.yml") -Raw
$markers = @(
    "Apply Saurus UX refresh",
    "Verify Saurus UX refresh",
    "Format refreshed Flutter sources",
    "pub-cache: true",
    "fetch-depth: 1",
    "cancel-in-progress: true"
)
foreach ($marker in $markers) {
    if (-not $workflow.Contains($marker)) {
        throw "Workflow marker not found: $marker"
    }
}

Write-Host "[OK] Project structure and workflow are ready." -ForegroundColor Green
