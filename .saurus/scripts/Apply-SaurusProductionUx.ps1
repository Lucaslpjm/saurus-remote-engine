# SAURUS_REMOTE_PRODUCTION_UX_PIPELINE_V3
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
$HomePage = Join-Path $Root "flutter\lib\desktop\pages\desktop_home_page.dart"
$ManifestPath = Join-Path $Root "SAURUS_PRODUCTION_UI.json"
$Utf8NoBom = New-Object Text.UTF8Encoding($false)

function Find-Python {
    foreach ($name in @("python.exe", "python3.exe", "python", "python3")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $command) { continue }
        try {
            $previousPreference = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            & $command.Source --version *> $null
            $code = $LASTEXITCODE
            $ErrorActionPreference = $previousPreference
            if ($code -eq 0) { return $command.Source }
        }
        catch {
            $ErrorActionPreference = $previousPreference
        }
    }
    throw "Python real nao encontrado para aplicar a UX de producao."
}

function Invoke-UxTool {
    param(
        [Parameter(Mandatory = $true)][string]$Python,
        [Parameter(Mandatory = $true)][string]$Tool,
        [Parameter(Mandatory = $true)][string]$Description
    )

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

function Read-HomePage {
    if (-not (Test-Path -LiteralPath $HomePage -PathType Leaf)) {
        throw "desktop_home_page.dart nao encontrado: $HomePage"
    }
    return [IO.File]::ReadAllText($HomePage, [Text.Encoding]::UTF8)
}

function Write-HomePage {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Content)
    $normalized = $Content.Replace("`r`n", "`n").Replace("`r", "`n")
    [IO.File]::WriteAllText($HomePage, $normalized, $Utf8NoBom)
}

$python = Find-Python

if (-not $VerifyOnly) {
    Invoke-UxTool -Python $python -Tool $ApplyTool -Description "Aplicador da UX responsiva"

    if (-not (Test-Path -LiteralPath $RepairTool -PathType Leaf)) {
        throw "Reparador UTF-8 nao encontrado: $RepairTool"
    }
    & $python $RepairTool --source-root $Root
    if ($LASTEXITCODE -ne 0) {
        throw "A normalizacao UTF-8 da interface falhou."
    }

    $content = Read-HomePage

    # SAURUS_REMOTE_LEGACY_CONNECTION_TITLE_MIGRATION_V1
    $legacyTitles = [ordered]@{
        "Conectar e acessar sessoes recentes" = "Conectar a outro dispositivo"
        "Conectar e acessar sessÃµes recentes" = "Conectar a outro dispositivo"
    }
    $migrationCount = 0
    foreach ($legacyTitle in $legacyTitles.Keys) {
        if ($content.Contains($legacyTitle)) {
            $occurrences = [regex]::Matches($content, [regex]::Escape($legacyTitle)).Count
            $content = $content.Replace($legacyTitle, $legacyTitles[$legacyTitle])
            $migrationCount += $occurrences
        }
    }
    Write-HomePage -Content $content
    Write-Host "[OK] Titulos legados migrados: $migrationCount" -ForegroundColor Green
}

Invoke-UxTool -Python $python -Tool $VerifyTool -Description "Verificador da UX responsiva"
$content = Read-HomePage

foreach ($codePoint in @(0x251C, 0x252C, 0xFFFD)) {
    if ($content.IndexOf([char]$codePoint) -ge 0) {
        throw "A interface final contem texto corrompido por codificacao (U+$('{0:X4}' -f $codePoint))."
    }
}

$forbidden = @(
    "Diagnostico rapido",
    "DiagnÃ³stico rÃ¡pido",
    "Configuracoes de rede",
    "ConfiguraÃ§Ãµes de rede",
    "Conectar e acessar sessoes recentes",
    "Conectar e acessar sessÃµes recentes"
)
foreach ($item in $forbidden) {
    if ($content.Contains($item)) {
        throw "A interface antiga ainda esta presente depois da migracao: '$item'."
    }
}

$required = @(
    "Este dispositivo",
    "Conectar a outro dispositivo",
    "HistÃ³rico e sessÃµes recentes"
)
foreach ($item in $required) {
    if (-not $content.Contains($item)) {
        throw "Marcador esperado da interface de producao nao encontrado: '$item'."
    }
}

$productionMarker = "// SAURUS_REMOTE_PRODUCTION_UI_2026_07_V3"
if (-not $content.Contains($productionMarker)) {
    if ($VerifyOnly) {
        throw "Marcador da interface de producao V3 ausente."
    }

    $classPattern = '(?m)^class DesktopHomePage\b'
    $matches = [regex]::Matches($content, $classPattern)
    if ($matches.Count -ne 1) {
        throw "Nao foi possivel localizar de forma unica a classe DesktopHomePage. Encontradas: $($matches.Count)"
    }
    $content = [regex]::Replace($content, $classPattern, $productionMarker + "`nclass DesktopHomePage", 1)
    Write-HomePage -Content $content
}

if (-not $VerifyOnly) {
    $manifest = [ordered]@{
        schemaVersion = 2
        revision = "production-ui-2026.07-v3"
        dashboard = "responsive-device-connect-history"
        legacyConnectionTitleRemoved = $true
        quickDiagnosticsRemoved = $true
        networkShortcutRemoved = $true
        loginRemoved = $true
        mapRemoved = $true
        verifiedAtUtc = [DateTime]::UtcNow.ToString("o")
    }
    [IO.File]::WriteAllText($ManifestPath, ($manifest | ConvertTo-Json -Depth 5), $Utf8NoBom)
}
elseif (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "Manifesto da interface de producao nao encontrado: $ManifestPath"
}

Write-Host "[OK] UX final de producao V3 aplicada e verificada." -ForegroundColor Green
