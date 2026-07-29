[CmdletBinding()]
param(
    [string]$RepoRoot = ".",
    [string]$Workflow = ""
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$root = (Resolve-Path -LiteralPath $RepoRoot).Path
$optimizer = Join-Path $root ".saurus\tools\Optimize-SaurusWorkflow.ps1"

if (-not (Test-Path -LiteralPath $optimizer -PathType Leaf)) {
    throw "Arquivo nao encontrado: $optimizer. Extraia novamente o kit na raiz do repositorio, preservando a pasta oculta .saurus."
}

try {
    & $optimizer -RepoRoot $root -Workflow $Workflow
}
catch {
    throw "Falha ao integrar o Saurus UX Refresh ao workflow. Detalhe: $($_.Exception.Message)"
}

Write-Host "Integracao concluida. Revise o diff, faca commit e execute o GitHub Actions." -ForegroundColor Green
