# SAURUS_REMOTE_PRODUCTION_RELEASE_TEST_V3
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))

function Require-File {
    param([Parameter(Mandatory = $true)][string]$RelativePath)
    $path = Join-Path $Root $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Arquivo obrigatorio ausente: $RelativePath"
    }
    return $path
}

$apply = Require-File ".saurus\scripts\Apply-SaurusCustomization.ps1"
$uxWrapper = Require-File ".saurus\scripts\Apply-SaurusProductionUx.ps1"
$uxApply = Require-File ".saurus\tools\apply_saurus_ux_refresh.py"
$uxVerify = Require-File ".saurus\tools\verify_saurus_ux_refresh.py"
$configure = Require-File ".saurus\installer\Configure-SaurusRemote.ps1"
$watchdog = Require-File ".saurus\installer\Run-SaurusRemotePostInstall.ps1"
$uninstall = Require-File ".saurus\installer\Uninstall-SaurusRemote.ps1"
$iss = Require-File ".saurus\installer\SaurusRemote.iss"

$applyText = [IO.File]::ReadAllText($apply)
if ([regex]::Matches($applyText, 'SAURUS_REMOTE_PRODUCTION_UX_PIPELINE_BEGIN').Count -ne 1 -or
    [regex]::Matches($applyText, 'SAURUS_REMOTE_PRODUCTION_UX_PIPELINE_END').Count -ne 1) {
    throw "O pipeline final de UX deve estar ligado exatamente uma vez ao Apply-SaurusCustomization.ps1."
}

$configureText = [IO.File]::ReadAllText($configure)
foreach ($forbidden in @(
    "Run-Engine",
    "--password-stdin",
    "--install-service",
    "Start-Process -FilePath `$Exe",
    "Wait-ServiceMissing",
    'Invoke-Sc -Arguments @("create"',
    'Invoke-Sc -Arguments @("config"',
    'sc.exe create',
    'sc.exe config'
)) {
    if ($configureText.Contains($forbidden)) {
        throw "O configurador ainda contem fluxo inseguro ou sujeito a quebra de argumentos: $forbidden"
    }
}

foreach ($required in @(
    "SAURUS_REMOTE_HEADLESS_POSTINSTALL_V3",
    "Win32_Service.Create",
    "Win32_Service.Change",
    '$ServiceAccount = "NT AUTHORITY\LocalService"',
    '$ServicePassword = ""',
    "Servico criado via Win32_Service.Create.",
    "Servico existente atualizado via Win32_Service.Change.",
    "Wait-ServiceRunning 45",
    "New-NetFirewallRule",
    "Rotate-InstallLog",
    "Preferencias adaptativas e audio desativado aplicados"
)) {
    if (-not $configureText.Contains($required)) {
        throw "Contrato do configurador headless V3 ausente: $required"
    }
}

$uninstallText = [IO.File]::ReadAllText($uninstall)
if (-not $uninstallText.Contains("SAURUS_REMOTE_HEADLESS_UNINSTALL_V1")) {
    throw "Marcador da desinstalacao headless ausente."
}
foreach ($forbidden in @("--uninstall-service", "& `$exe")) {
    if ($uninstallText.Contains($forbidden)) {
        throw "A desinstalacao ainda pode abrir o executavel grafico: $forbidden"
    }
}

$issText = [IO.File]::ReadAllText($iss).Replace("`r`n", "`n").Replace("`r", "`n")
foreach ($required in @(
    "Run-SaurusRemotePostInstall.ps1",
    "-TimeoutSeconds 120",
    "Flags: nowait postinstall skipifsilent",
    "PrivilegesRequired=admin",
    "ArchitecturesAllowed=x64compatible"
)) {
    if (-not $issText.Contains($required)) {
        throw "Protecao esperada no instalador nao encontrada: $required"
    }
}
if ([regex]::Matches($issText, '(?m)^Filename: "\{app\}\\\{#AppExeName\}"').Count -ne 1) {
    throw "A abertura do Saurus Remote deve existir exatamente uma vez na secao [Run]."
}
if ([regex]::Matches($issText, '(?m)^\[Run\]\s*$').Count -ne 1 -or
    [regex]::Matches($issText, '(?m)^\[Code\]\s*$').Count -ne 1) {
    throw "As secoes [Run] e [Code] devem existir exatamente uma vez."
}

Write-Host "[OK] UX responsiva restaurada e ligada ao build."
Write-Host "[OK] Configuracao do servico usa Win32_Service sem sc.exe create/config."
Write-Host "[OK] Configuracao do instalador permanece totalmente headless."
Write-Host "[OK] Watchdog de 120 segundos configurado."
