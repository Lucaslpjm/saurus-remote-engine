# SAURUS_REMOTE_PRODUCTION_UX_PIPELINE_V3
# SAURUS_REMOTE_POWERSHELL_ENCODING_SAFE_V1
# A normalizacao UTF-8 da interface falhou
# Mojibake sentinels: 0x251C 0x252C 0xFFFD
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SourceRoot,
    [switch]$VerifyOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = [IO.Path]::GetFullPath($SourceRoot)
$ApplyTool = Join-Path $PSScriptRoot "..\tools\apply_saurus_ux_refresh.py"
$VerifyTool = Join-Path $PSScriptRoot "..\tools\verify_saurus_ux_refresh.py"
$RepairTool = Join-Path $PSScriptRoot "..\tools\repair_saurus_utf8_ui.py"
$FinalizeTool = Join-Path $PSScriptRoot "..\tools\finalize_saurus_production_ui.py"
$HomePage = Join-Path $Root "flutter\lib\desktop\pages\desktop_home_page.dart"
$ManifestPath = Join-Path $Root "SAURUS_PRODUCTION_UI.json"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Find-Python {
    foreach ($name in @("python.exe", "python3.exe", "python", "python3")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $command) { continue }
        try {
            & $command.Source --version *> $null
            if ($LASTEXITCODE -eq 0) { return $command.Source }
        }
        catch {
        }
    }
    throw "Python real nao encontrado para aplicar a UX de producao."
}

function Invoke-PythonTool {
    param(
        [Parameter(Mandatory = $true)][string]$Python,
        [Parameter(Mandatory = $true)][string]$Tool,
        [Parameter(Mandatory = $true)][string]$Description,
        [string[]]$ExtraArguments = @(),
        [switch]$AllowPositionalFallback
    )

    if (-not (Test-Path -LiteralPath $Tool -PathType Leaf)) {
        throw "$Description nao encontrado: $Tool"
    }

    $arguments = @($Tool, "--source-root", $Root) + @($ExtraArguments)
    & $Python @arguments
    if ($LASTEXITCODE -eq 0) { return }

    if ($AllowPositionalFallback -and @($ExtraArguments).Count -eq 0) {
        Write-Warning "$Description nao aceitou --source-root. Tentando caminho posicional."
        & $Python $Tool $Root
        if ($LASTEXITCODE -eq 0) { return }
    }

    throw "$Description falhou nas formas de chamada suportadas."
}

$python = Find-Python
if (-not $VerifyOnly) {
    Invoke-PythonTool -Python $python -Tool $ApplyTool -Description "Aplicador da UX responsiva" -AllowPositionalFallback
    Invoke-PythonTool -Python $python -Tool $RepairTool -Description "Normalizador UTF-8"
    Invoke-PythonTool -Python $python -Tool $FinalizeTool -Description "Finalizador Unicode da interface"
}

Invoke-PythonTool -Python $python -Tool $VerifyTool -Description "Verificador estrutural da UX" -AllowPositionalFallback
Invoke-PythonTool -Python $python -Tool $FinalizeTool -Description "Contrato Unicode final" -ExtraArguments @("--check-only")

if (-not (Test-Path -LiteralPath $HomePage -PathType Leaf)) {
    throw "desktop_home_page.dart nao encontrado depois da UX."
}

if (-not $VerifyOnly) {
    $manifest = [ordered]@{
        schemaVersion = 3
        revision = "production-ui-3.2.3.2"
        generatedAtUtc = [DateTime]::UtcNow.ToString("o")
        homePage = "flutter/lib/desktop/pages/desktop_home_page.dart"
        finalizer = "finalize_saurus_production_ui.py"
        unicodeContract = "python-unicode-escapes"
        powershellSource = "ascii-only"
        oldCombinedTitleRemoved = $true
        encoding = "UTF-8"
    }
    $json = $manifest | ConvertTo-Json -Depth 4
    [IO.File]::WriteAllText($ManifestPath, $json + "`n", $Utf8NoBom)
}
elseif (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "Manifesto da interface de producao nao encontrado: $ManifestPath"
}

Write-Host "[OK] UX final de producao aplicada e validada com contrato Unicode seguro." -ForegroundColor Green
