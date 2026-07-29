[CmdletBinding()]
param(
    [string]$SaurusExe = "$env:ProgramFiles\Saurus Software\Saurus Remote\SaurusRemote.exe",
    [string]$ServerHost = "20.195.216.23",
    [int]$ServerPort = 443,
    [string]$SaurusInstallerKey = "{1117CE17-506B-4122-A421-69233FCA9C12}_is1",
    [string]$RustDeskInstallerKey = "{54E86BC2-6C85-41F3-A9EB-1A94AC9B1F93}_is1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-ServiceSnapshot {
    param([string]$Name)
    $service = Get-CimInstance Win32_Service -Filter "Name='$Name'" -ErrorAction SilentlyContinue
    if (-not $service) { return $null }
    return [ordered]@{
        Name = $service.Name
        DisplayName = $service.DisplayName
        State = $service.State
        StartMode = $service.StartMode
        PathName = $service.PathName
    }
}

function Get-UninstallSnapshot {
    param([string]$KeyName)
    foreach ($base in @(
        'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall',
        'HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall'
    )) {
        $path = Join-Path $base $KeyName
        $item = Get-ItemProperty -LiteralPath $path -ErrorAction SilentlyContinue
        if ($item) {
            return [ordered]@{
                RegistryPath = $path
                DisplayName = $item.DisplayName
                InstallLocation = $item.InstallLocation
                UninstallString = $item.UninstallString
            }
        }
    }
    return $null
}

$rustDesk = Get-ServiceSnapshot "RustDesk"
$saurus = Get-ServiceSnapshot "SaurusRemote"
$saurusUninstall = Get-UninstallSnapshot $SaurusInstallerKey
$rustDeskUninstall = Get-UninstallSnapshot $RustDeskInstallerKey
$saurusStaging = "$env:ProgramData\SaurusRemote\SaurusRemoteCustomClientStaging"
$rustDeskStaging = "$env:ProgramData\RustDesk\RustDeskCustomClientStaging"
$saurusBroker = Get-Process -Name 'RuntimeBroker_saurusremote' -ErrorAction SilentlyContinue
$rustDeskBroker = Get-Process -Name 'RuntimeBroker_rustdesk' -ErrorAction SilentlyContinue

$results = [ordered]@{
    Timestamp = (Get-Date).ToString("o")
    SaurusExecutableExists = Test-Path -LiteralPath $SaurusExe -PathType Leaf
    SaurusService = $saurus
    RustDeskIndependentService = $rustDesk
    SaurusUninstall = $saurusUninstall
    RustDeskIndependentUninstall = $rustDeskUninstall
    SaurusStagingExists = Test-Path -LiteralPath $saurusStaging
    RustDeskStagingExists = Test-Path -LiteralPath $rustDeskStaging
    SaurusPrivacyBrokerRunning = [bool]$saurusBroker
    RustDeskPrivacyBrokerRunning = [bool]$rustDeskBroker
    SameServicePath = $false
    SameInstallLocation = $false
    TcpServerReachable = $false
    Problems = @()
}

if ($saurus -and $rustDesk) {
    $results.SameServicePath = ($saurus.PathName -eq $rustDesk.PathName)
}
if ($saurusUninstall -and $rustDeskUninstall) {
    $results.SameInstallLocation = (
        -not [string]::IsNullOrWhiteSpace($saurusUninstall.InstallLocation) -and
        $saurusUninstall.InstallLocation -eq $rustDeskUninstall.InstallLocation
    )
}

if (-not $saurus) { $results.Problems += "Serviço SaurusRemote não encontrado." }
if ($saurus -and $saurus.PathName -match '\\RustDesk\\') { $results.Problems += "Serviço Saurus aponta para pasta do RustDesk original." }
if ($results.SameServicePath) { $results.Problems += "SaurusRemote e RustDesk usam o mesmo binário." }
if ($results.SameInstallLocation) { $results.Problems += "Saurus Remote e RustDesk usam o mesmo InstallLocation no Registro." }
if ($saurusUninstall -and $saurusUninstall.InstallLocation -match '\\RustDesk(?:\\|$)') {
    $results.Problems += "Chave de desinstalação Saurus aponta para a pasta RustDesk."
}
if (-not $results.SaurusExecutableExists) { $results.Problems += "Executável SaurusRemote.exe não encontrado no caminho esperado." }

try {
    $tnc = Test-NetConnection -ComputerName $ServerHost -Port $ServerPort -WarningAction SilentlyContinue
    $results.TcpServerReachable = [bool]$tnc.TcpTestSucceeded
    if (-not $results.TcpServerReachable) {
        $results.Problems += "Servidor Saurus não respondeu em TCP $ServerPort."
    }
} catch {
    $results.Problems += "Falha ao executar Test-NetConnection: $($_.Exception.Message)"
}

$results | ConvertTo-Json -Depth 10
if ($results.Problems.Count -gt 0) { exit 1 }
