[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RustDeskForkRoot,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$fork = [IO.Path]::GetFullPath($RustDeskForkRoot)
$kitRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))

if (-not (Test-Path -LiteralPath $fork -PathType Container)) {
    throw "Diretorio do fork nao encontrado: $fork"
}

$cargoPath = Join-Path $fork "Cargo.toml"
if (-not (Test-Path -LiteralPath $cargoPath -PathType Leaf)) {
    throw "Cargo.toml nao encontrado. Selecione a raiz do fork RustDesk."
}
$cargo = [IO.File]::ReadAllText($cargoPath)
if ($cargo -notmatch '(?m)^version\s*=\s*"1\.4\.9"\s*$') {
    throw "O fork deve estar na tag/versao RustDesk 1.4.9."
}

$requiredUpstreamFiles = @(
    ".github\workflows\bridge.yml",
    ".github\workflows\third-party-RustDeskTempTopMostWindow.yml",
    ".github\patches\flutter_3.24.4_dropdown_menu_enableFilter.diff",
    "build.py",
    "libs\portable\generate.py"
)
foreach ($relative in $requiredUpstreamFiles) {
    $path = Join-Path $fork $relative
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Arquivo upstream obrigatorio ausente: $relative"
    }
}

$destination = Join-Path $fork ".saurus"
if ((Test-Path -LiteralPath $destination) -and -not $Force) {
    throw "A pasta .saurus ja existe. Use -Force para substitui-la."
}
if (Test-Path -LiteralPath $destination) {
    Remove-Item -LiteralPath $destination -Recurse -Force
}
New-Item -ItemType Directory -Path $destination -Force | Out-Null

foreach ($folder in @("branding", "scripts", "tools", "docs", "samples", "LICENSES")) {
    $source = Join-Path $kitRoot $folder
    if (Test-Path -LiteralPath $source -PathType Container) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $destination $folder) -Recurse -Force
    }
}
foreach ($file in @("README.md", "CHANGELOG.md")) {
    $source = Join-Path $kitRoot $file
    if (Test-Path -LiteralPath $source -PathType Leaf) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $destination $file) -Force
    }
}

$workflowSource = Join-Path $kitRoot "github\build-saurus-remote-windows.yml"
$workflowTarget = Join-Path $fork ".github\workflows\build-saurus-remote-windows.yml"
Copy-Item -LiteralPath $workflowSource -Destination $workflowTarget -Force

Write-Host ""
Write-Host "Kit instalado no fork RustDesk 1.4.9." -ForegroundColor Green
Write-Host "Customizacao: $destination"
Write-Host "Workflow: $workflowTarget"
Write-Host ""
Write-Host "Proximos passos:" -ForegroundColor Yellow
Write-Host "  1. Revise .saurus\README.md e os avisos de licenca."
Write-Host "  2. Commit e envie o fork para um repositorio privado da Saurus."
Write-Host "  3. No GitHub, execute Actions > Build Saurus Remote Engine (Windows x64)."
Write-Host "  4. Configure os secrets de assinatura antes da distribuicao em producao."
