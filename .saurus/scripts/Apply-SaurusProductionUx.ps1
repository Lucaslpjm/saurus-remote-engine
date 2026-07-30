# SAURUS_REMOTE_PRODUCTION_UX_PIPELINE_V1
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
$HomePage = Join-Path $Root "flutter\lib\desktop\pages\desktop_home_page.dart"
$ManifestPath = Join-Path $Root "SAURUS_PRODUCTION_UI.json"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Find-Python {
    foreach ($name in @("python.exe", "python3.exe", "python", "python3")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) {
            try {
                & $cmd.Source --version *> $null
                if ($LASTEXITCODE -eq 0) { return $cmd.Source }
            } catch {}
        }
    }
    throw "Python real nao encontrado para aplicar a UX de producao."
}

function Invoke-UxTool {
    param([string]$Python, [string]$Tool, [string]$Description)
    if (-not (Test-Path -LiteralPath $Tool -PathType Leaf)) {
        throw "$Description nao encontrado: $Tool"
    }

    & $Python $Tool --source-root $Root
    if ($LASTEXITCODE -eq 0) { return }

    Write-Warning "$Description nao aceitou --source-root. Tentando caminho posicional."
    & $Python $Tool $Root
    if ($LASTEXITCODE -ne 0) {
        throw "$Description falhou nas duas formas de chamada."
    }
}

$python = Find-Python
if (-not $VerifyOnly) {
    Invoke-UxTool -Python $python -Tool $ApplyTool -Description "Aplicador da UX responsiva"
}
Invoke-UxTool -Python $python -Tool $VerifyTool -Description "Verificador da UX responsiva"

if (-not (Test-Path -LiteralPath $HomePage -PathType Leaf)) {
    throw "desktop_home_page.dart nao encontrado depois da UX."
}
$content = [IO.File]::ReadAllText($HomePage)
$forbidden = @(
    "Diagnostico rapido",
    "Diagnóstico rápido",
    "Configuracoes de rede",
    "Configurações de rede",
    "Conectar e acessar sessoes recentes",
    "Conectar e acessar sessões recentes"
)
foreach ($item in $forbidden) {
    if ($content.Contains($item)) {
        throw "A interface antiga ainda esta presente: '$item'."
    }
}
foreach ($required in @("Este dispositivo", "Hist", "Conectar")) {
    if (-not $content.Contains($required)) {
        throw "Marcador esperado da interface de producao nao encontrado: '$required'."
    }
}

$marker = "// SAURUS_REMOTE_PRODUCTION_UI_2026_07"
if (-not $content.Contains($marker)) {
    $classPattern = '(?m)^class DesktopHomePage\b'
    $matches = [regex]::Matches($content, $classPattern)
    if ($matches.Count -eq 1) {
        $classRegex = New-Object System.Text.RegularExpressions.Regex($classPattern, [System.Text.RegularExpressions.RegexOptions]::Multiline)
        $content = $classRegex.Replace($content, $marker + "`r`nclass DesktopHomePage", 1)
        [IO.File]::WriteAllText($HomePage, $content, $Utf8NoBom)
    } else {
        throw "Nao foi possivel inserir o marcador da UI de producao."
    }
}

$manifest = [ordered]@{
    schemaVersion = 1
    revision = "production-ui-2026.07"
    uxSourceCommit = "371f19d5ab488f95720172c66e006bb481dc3b6f"
    dashboard = "responsive-device-connect-history"
    quickDiagnosticsRemoved = $true
    networkShortcutRemoved = $true
    loginRemoved = $true
    mapRemoved = $true
    verifiedAtUtc = [DateTime]::UtcNow.ToString("o")
}
[IO.File]::WriteAllText($ManifestPath, ($manifest | ConvertTo-Json -Depth 5), $Utf8NoBom)
Write-Host "[OK] UX final de producao aplicada e verificada." -ForegroundColor Green