# Saurus Remote - validacao estatica e compilacao de preflight do Inno Setup.
[CmdletBinding()]
param(
    [string]$InstallerScript = (Join-Path $PSScriptRoot "SaurusRemote.iss"),
    [string]$ProductVersion = "1.4.9-saurus.3.1.4.2",
    [switch]$StaticOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-ExactlyOne {
    param([string]$Content, [string]$Pattern, [string]$Description)
    $count = [Regex]::Matches($Content, $Pattern, [System.Text.RegularExpressions.RegexOptions]::Multiline).Count
    if ($count -ne 1) {
        throw "${Description}: era esperada exatamente 1 ocorrencia e foram encontradas $count."
    }
}

function Find-Iscc {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
    )
    return $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}

$InstallerScript = [IO.Path]::GetFullPath($InstallerScript)
if (-not (Test-Path -LiteralPath $InstallerScript -PathType Leaf)) {
    throw "SaurusRemote.iss nao encontrado: $InstallerScript"
}
if ($ProductVersion -notmatch '^1\.4\.9-saurus\.[A-Za-z0-9._-]+$') {
    throw "ProductVersion invalida para o preflight: $ProductVersion"
}

$content = [IO.File]::ReadAllText($InstallerScript)
# SAURUS_REMOTE_NORMALIZE_INSTALLER_LINE_ENDINGS_V2
# Normaliza CRLF, LF e CR antes das expressoes regulares de linha.
$content = $content.Replace("`r`n", "`n").Replace("`r", "`n")
Assert-ExactlyOne $content '(?m)^[ \t]*AppId[ \t]*=[^\r\n]*$' 'Diretiva AppId'
$appId = [Regex]::Match($content, '(?m)^[ \t]*AppId[ \t]*=[ \t]*([^\r\n]+)$').Groups[1].Value.Trim()
if ($appId -ne '{{1117CE17-506B-4122-A421-69233FCA9C12}') {
    throw "AppId invalido. Esperado: AppId={{1117CE17-506B-4122-A421-69233FCA9C12}; recebido: AppId=$appId"
}
if ($content -match '(?m)^[ \t]*AppId[ \t]*=[ \t]*\{#AppGuid\}') {
    throw "AppId ainda usa macro que gera uma chave literal sem escape."
}

foreach ($directive in @('VersionInfoVersion', 'VersionInfoProductVersion')) {
    Assert-ExactlyOne $content ("(?m)^[ \t]*" + [Regex]::Escape($directive) + "[ \t]*=[^\r\n]*$") $directive
    $value = [Regex]::Match($content, ("(?m)^[ \t]*" + [Regex]::Escape($directive) + "[ \t]*=[ \t]*([^\r\n]+)$")).Groups[1].Value.Trim()
    if ($value -notmatch '^\d+(\.\d+){0,3}$') {
        throw "$directive deve conter no maximo quatro grupos numericos. Valor recebido: $value"
    }
    foreach ($part in $value.Split('.')) {
        if ([int64]$part -gt 65535) { throw "$directive possui componente maior que 65535: $value" }
    }
}

Assert-ExactlyOne $content '(?m)^[ \t]*VersionInfoProductTextVersion[ \t]*=[ \t]*\{#ProductVersion\}[ \t]*$' 'VersionInfoProductTextVersion'

foreach ($required in @(
    '#ifndef SourceRoot',
    '#ifndef OutputDir',
    '#ifndef InstallerRoot',
    '#ifndef BrandingRoot',
    'PrivilegesRequired=admin',
    'ArchitecturesAllowed=x64compatible',
    'ArchitecturesInstallIn64BitMode=x64compatible',
    'OutputBaseFilename=SaurusRemote-{#ProductVersion}-Setup',
    'Configure-SaurusRemote.ps1',
    'Uninstall-SaurusRemote.ps1',
    'procedure CurStepChanged(CurStep: TSetupStep)',
    'if ResultCode <> 0 then'
)) {
    if (-not $content.Contains($required)) { throw "Contrato obrigatorio ausente no instalador: $required" }
}

Write-Host "[OK] Validacao estatica do SaurusRemote.iss concluida." -ForegroundColor Green
if ($StaticOnly) { return }

$iscc = Find-Iscc
if (-not $iscc) {
    Write-Warning "ISCC.exe nao encontrado. A validacao estatica passou, mas a compilacao de preflight foi ignorada."
    return
}

$installerRoot = Split-Path $InstallerScript -Parent
$brandingRoot = Join-Path (Split-Path $installerRoot -Parent) 'branding'
$requiredFiles = @(
    (Join-Path $installerRoot 'Configure-SaurusRemote.ps1'),
    (Join-Path $installerRoot 'Uninstall-SaurusRemote.ps1'),
    (Join-Path $installerRoot 'SaurusRemote_default.toml'),
    (Join-Path $brandingRoot 'app_icon.ico')
)
foreach ($file in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Arquivo exigido pelo instalador nao encontrado: $file" }
}

$tempRoot = Join-Path $env:TEMP ("SaurusRemote-InnoPreflight-" + [Guid]::NewGuid().ToString('N'))
$payload = Join-Path $tempRoot 'payload'
$output = Join-Path $tempRoot 'output'
New-Item -ItemType Directory -Path $payload, $output -Force | Out-Null

try {
    # O Inno apenas empacota o arquivo durante o preflight; um pequeno stub e suficiente para validar toda a sintaxe.
    [IO.File]::WriteAllBytes((Join-Path $payload 'SaurusRemote.exe'), [byte[]](0x4D, 0x5A, 0x90, 0x00))
    [IO.File]::WriteAllText((Join-Path $payload 'preflight.txt'), 'Saurus Remote installer preflight')

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        # O compilador pode escrever mensagens informativas no STDERR; valide pelo codigo real de saida.
        $ErrorActionPreference = "Continue"
        $raw = & $iscc `
            "/DSourceRoot=$payload" `
            "/DOutputDir=$output" `
            "/DProductVersion=$ProductVersion" `
            "/DInstallerRoot=$installerRoot" `
            "/DBrandingRoot=$brandingRoot" `
            $InstallerScript 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    foreach ($line in @($raw)) { Write-Host $line }
    if ($exitCode -ne 0) { throw "ISCC retornou codigo $exitCode durante o preflight do instalador." }

    $setup = Get-ChildItem -LiteralPath $output -Filter 'SaurusRemote-*-Setup.exe' -File | Select-Object -First 1
    if (-not $setup) { throw "O preflight compilou sem erro, mas nao gerou o executavel de instalacao esperado." }
    Write-Host "[OK] Compilacao real de preflight do Inno Setup concluida: $($setup.Name)" -ForegroundColor Green
}
finally {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}