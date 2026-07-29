[CmdletBinding()]
param(
    [string]$Destination = "C:\SaurusRemote",
    [string]$RepositoryUrl = "https://github.com/Lucaslpjm/saurus-remote-engine.git",
    [string]$Branch = "saurus/1.4.9",
    [switch]$ForceReclone
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    & git @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Git failed: git $($Arguments -join ' ')"
    }
}

function Assert-RequiredFile {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$RelativePath
    )
    $path = Join-Path $Root $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required file not found: $path"
    }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git was not found. Install Git for Windows or GitHub Desktop and run this script again."
}

$packageRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$destinationFull = [System.IO.Path]::GetFullPath($Destination)

if ([string]::Equals($packageRoot.TrimEnd('\'), $destinationFull.TrimEnd('\'), [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Extract the package to a staging folder, for example C:\SaurusRemote-Package, and keep Destination as C:\SaurusRemote."
}

if ($ForceReclone -and (Test-Path -LiteralPath $destinationFull)) {
    Write-Host "Removing existing destination: $destinationFull" -ForegroundColor Yellow
    Remove-Item -LiteralPath $destinationFull -Recurse -Force
}

if (-not (Test-Path -LiteralPath $destinationFull)) {
    $parent = Split-Path -Parent $destinationFull
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    Write-Host "Cloning repository and submodules..." -ForegroundColor Cyan
    Invoke-Git -Arguments @(
        "clone",
        "--branch", $Branch,
        "--single-branch",
        "--recurse-submodules",
        $RepositoryUrl,
        $destinationFull
    )
}
else {
    if (-not (Test-Path -LiteralPath (Join-Path $destinationFull ".git") -PathType Container)) {
        throw "Destination exists but is not a Git repository: $destinationFull. Use -ForceReclone to replace it."
    }

    Write-Host "Updating existing repository..." -ForegroundColor Cyan
    Invoke-Git -Arguments @("-C", $destinationFull, "fetch", "origin", $Branch)
    Invoke-Git -Arguments @("-C", $destinationFull, "checkout", $Branch)
    Invoke-Git -Arguments @("-C", $destinationFull, "pull", "--ff-only", "origin", $Branch)
    Invoke-Git -Arguments @("-C", $destinationFull, "submodule", "sync", "--recursive")
    Invoke-Git -Arguments @("-C", $destinationFull, "submodule", "update", "--init", "--recursive")
}

Write-Host "Applying the Saurus 3.1.2 project files..." -ForegroundColor Cyan
$excludedDirectories = @(
    (Join-Path $packageRoot ".git"),
    (Join-Path $packageRoot "libs\hbb_common"),
    (Join-Path $packageRoot "target"),
    (Join-Path $packageRoot "flutter\build")
)

$robocopyArgs = @(
    $packageRoot,
    $destinationFull,
    "/E",
    "/COPY:DAT",
    "/DCOPY:DAT",
    "/R:2",
    "/W:1",
    "/NFL",
    "/NDL",
    "/NP",
    "/XD"
) + $excludedDirectories

& robocopy @robocopyArgs | Out-Host
$robocopyExit = $LASTEXITCODE
if ($robocopyExit -ge 8) {
    throw "Robocopy failed with exit code $robocopyExit."
}

Invoke-Git -Arguments @("-C", $destinationFull, "submodule", "sync", "--recursive")
Invoke-Git -Arguments @("-C", $destinationFull, "submodule", "update", "--init", "--recursive")

$required = @(
    "Cargo.toml",
    "build.py",
    ".github\workflows\build-saurus-remote-windows.yml",
    ".saurus\scripts\Apply-SaurusCustomization.ps1",
    ".saurus\tools\apply_saurus_ux_refresh.py",
    ".saurus\tools\verify_saurus_ux_refresh.py",
    "libs\hbb_common\src\config.rs"
)
foreach ($item in $required) {
    Assert-RequiredFile -Root $destinationFull -RelativePath $item
}

Write-Host "" 
Write-Host "Project prepared successfully." -ForegroundColor Green
Write-Host "Location: $destinationFull" -ForegroundColor Green
Write-Host "" 
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Open $destinationFull in GitHub Desktop."
Write-Host "  2. Review the changed files, commit, and push branch $Branch."
Write-Host "  3. Run the workflow 'Build Saurus Remote Engine (Windows x64)'."
Write-Host "  4. Use build label: saurus.3.1.2"
Write-Host "" 
Write-Host "Git status:" -ForegroundColor Cyan
& git -C $destinationFull status --short
