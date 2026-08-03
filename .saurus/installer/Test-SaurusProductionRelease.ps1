# SAURUS_REMOTE_PRODUCTION_RELEASE_TEST_V4
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
$utf8Repair = Require-File ".saurus\tools\repair_saurus_utf8_ui.py"
$configure = Require-File ".saurus\installer\Configure-SaurusRemote.ps1"
$watchdog = Require-File ".saurus\installer\Run-SaurusRemotePostInstall.ps1"
$uninstall = Require-File ".saurus\installer\Uninstall-SaurusRemote.ps1"
$iss = Require-File ".saurus\installer\SaurusRemote.iss"
$appManifest = Require-File ".saurus\installer\SaurusRemote.requireAdministrator.manifest"
$manifestTool = Require-File ".saurus\installer\Set-RequireAdministratorManifest.ps1"
$launcherSource = Require-File ".saurus\installer\SaurusRemoteLauncher.cs"
$launcherBuild = Require-File ".saurus\installer\Build-SaurusRemoteLauncher.ps1"
$executionLevelTest = Require-File ".saurus\installer\Test-SaurusExecutionLevels.ps1"
$workflow = Require-File ".github\workflows\build-saurus-remote-windows.yml"
$localBuild = Require-File ".saurus\scripts\Build-SaurusRemote.ps1"

$applyText = [IO.File]::ReadAllText($apply)
foreach ($required in @(
    "SAURUS_REMOTE_PRODUCTION_UX_PIPELINE_BEGIN",
    "SAURUS_REMOTE_PRODUCTION_UX_PIPELINE_END",
    "SAURUS_REMOTE_ENFORCE_SERVER_CONFIG",
    '"custom-rendezvous-server".to_owned()',
    '"20.195.216.23:443".to_owned()',
    '"OJ7QiUrqNu0wM13vDSp4nmAlDu6hy3n8hTI5Wksl2Tc=".to_owned()'
)) {
    if (-not $applyText.Contains($required)) {
        throw "Contrato de inicializacao ausente: $required"
    }
}
if ([regex]::Matches($applyText, 'SAURUS_REMOTE_PRODUCTION_UX_PIPELINE_BEGIN').Count -ne 1 -or
    [regex]::Matches($applyText, 'SAURUS_REMOTE_PRODUCTION_UX_PIPELINE_END').Count -ne 1) {
    throw "O pipeline final de UX deve estar ligado exatamente uma vez."
}

$wrapperText = [IO.File]::ReadAllText($uxWrapper)
foreach ($required in @(
    "SAURUS_REMOTE_PRODUCTION_UX_PIPELINE_V3",
    "repair_saurus_utf8_ui.py",
    "A normalizacao UTF-8 da interface falhou",
    "0x251C",
    "0x252C",
    "0xFFFD"
)) {
    if (-not $wrapperText.Contains($required)) {
        throw "Contrato UTF-8 ausente no pipeline da UX: $required"
    }
}

$repairText = [IO.File]::ReadAllText($utf8Repair)
foreach ($required in @("cp850", "utf-8", "MOJIBAKE_MARKERS", "flutter_root.rglob")) {
    if (-not $repairText.Contains($required)) {
        throw "Reparador UTF-8 incompleto: $required"
    }
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
    'sc.exe config',
    'NT AUTHORITY\LocalService',
    'ServiceProfiles\LocalService'
)) {
    if ($configureText.Contains($forbidden)) {
        throw "O configurador ainda contem fluxo inseguro: $forbidden"
    }
}
foreach ($required in @(
    "SAURUS_REMOTE_HEADLESS_POSTINSTALL_V5",
    "Win32_Service.Create",
    "Win32_Service.Change",
    '$ServiceAccount = "LocalSystem"',
    '$ServicePassword = $null',
    "SAURUS_REMOTE_VERIFY_INTERACTIVE_SERVER_V1",
    "Wait-ManagedServerStable -TimeoutSeconds 45 -StableSeconds 5",
    "DelayedAutostart",
    "Wait-ServiceStable -TimeoutSeconds 45 -StableSeconds 8",
    "SaurusRemote2.toml",
    "custom-rendezvous-server",
    "20.195.216.23:443",
    "OJ7QiUrqNu0wM13vDSp4nmAlDu6hy3n8hTI5Wksl2Tc=",
    "New-NetFirewallRule",
    "Rotate-InstallLog"
)) {
    if (-not $configureText.Contains($required)) {
        throw "Contrato do configurador headless V5 ausente: $required"
    }
}

$manifestText = [IO.File]::ReadAllText($appManifest)
if (-not $manifestText.Contains('level="requireAdministrator"')) {
    throw "O launcher nao exige elevacao administrativa."
}
if ($manifestText.Contains('level="asInvoker"')) {
    throw "O manifesto do launcher ainda permite execucao sem elevacao."
}
$launcherBuildText = [IO.File]::ReadAllText($launcherBuild)
$executionLevelText = [IO.File]::ReadAllText($executionLevelTest)
if (-not $launcherBuildText.Contains("SAURUS_REMOTE_SPLIT_ELEVATION_LAUNCHER_V1") -or
    -not $executionLevelText.Contains("SAURUS_REMOTE_SPLIT_ELEVATION_VERIFY_V1")) {
    throw "Isolamento de elevacao entre launcher e motor ausente."
}
$manifestToolText = [IO.File]::ReadAllText($manifestTool)
if (-not $manifestToolText.Contains("SAURUS_REMOTE_ALWAYS_ADMIN_MANIFEST_V1")) {
    throw "Aplicador do manifesto requireAdministrator ausente."
}
if (-not $manifestToolText.Contains("SAURUS_REMOTE_VERIFY_EMBEDDED_MANIFEST_V1")) {
    throw "A verificacao do manifesto incorporado no executavel final esta ausente."
}
foreach ($metadataPath in @($workflow, $localBuild)) {
    $metadataText = [IO.File]::ReadAllText($metadataPath)
    if (-not $metadataText.Contains('requiresAdministrator = $true')) {
        throw "Metadado do executavel nao informa elevacao obrigatoria: $metadataPath"
    }
    if ($metadataText.Contains('requiresAdministrator = $false')) {
        throw "Metadado contraditorio sem elevacao encontrado: $metadataPath"
    }
}

if (-not $configureText.Contains("SAURUS_REMOTE_SCOPED_CONFIG_ROOTS_V1")) {
    throw "O instalador ainda nao limita a escrita aos perfis gerenciados."
}
if ($configureText.Contains("-Profile Any") -or -not $configureText.Contains("-Profile Domain,Private")) {
    throw "A regra de firewall nao esta limitada a redes de Dominio e Privadas."
}
$workflowText = [IO.File]::ReadAllText($workflow)
if (-not $workflowText.Contains("verify /pa /all")) {
    throw "O workflow nao valida as assinaturas Authenticode depois da assinatura."
}

$uninstallText = [IO.File]::ReadAllText($uninstall)
if (-not $uninstallText.Contains("SAURUS_REMOTE_HEADLESS_UNINSTALL_V1")) {
    throw "Marcador da desinstalacao headless ausente."
}
if ($uninstallText.Contains("--uninstall-service")) {
    throw "A desinstalacao ainda chama o executavel grafico."
}

$issText = [IO.File]::ReadAllText($iss).Replace("`r`n", "`n").Replace("`r", "`n")
foreach ($required in @(
    "Run-SaurusRemotePostInstall.ps1",
    "-TimeoutSeconds 120",
    "Flags: nowait postinstall skipifsilent runascurrentuser",
    "PrivilegesRequired=admin",
    "ArchitecturesAllowed=x64compatible"
)) {
    if (-not $issText.Contains($required)) {
        throw "Protecao esperada no instalador nao encontrada: $required"
    }
}
if ([regex]::Matches($issText, '(?m)^Filename: "\{app\}\\\{#AppLauncherName\}"').Count -ne 1) {
    throw "A abertura do Saurus Remote deve existir exatamente uma vez na secao [Run]."
}
if ($issText.Contains("runasoriginaluser")) {
    throw "A abertura final ainda reduz os privilegios para o usuario original."
}
foreach ($shortcut in @(
    'Name: "{autoprograms}\Saurus Remote"; Filename: "{app}\{#AppLauncherName}"; WorkingDir: "{app}"',
    'Name: "{autodesktop}\Saurus Remote"; Filename: "{app}\{#AppLauncherName}"; WorkingDir: "{app}"'
)) {
    if (-not $issText.Contains($shortcut)) {
        throw "Atalho administrativo esperado nao encontrado: $shortcut"
    }
}

Write-Host "[OK] Interface protegida contra corrupcao CP850/UTF-8."
Write-Host "[OK] Launcher e atalhos exigem administrador; motor preserva service/server/tray."
Write-Host "[OK] Servidor e chave Saurus sao reforcados no inicio e nos perfis instalados."
Write-Host "[OK] Servico precisa permanecer estavel antes da conclusao do instalador."
Write-Host "[OK] Abertura final preserva a elevacao administrativa do setup."
