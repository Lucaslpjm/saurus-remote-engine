[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$InstallDir)
Set-StrictMode -Version Latest
$ErrorActionPreference = "SilentlyContinue"
$exe = Join-Path ([IO.Path]::GetFullPath($InstallDir)) "SaurusRemote.exe"
Get-Process -Name "SaurusRemote" | Stop-Process -Force
if (Test-Path -LiteralPath $exe) {
    & $exe --uninstall-service | Out-Null
}
& sc.exe stop SaurusRemote | Out-Null
& sc.exe delete SaurusRemote | Out-Null
& netsh advfirewall firewall delete rule name="Saurus Remote" | Out-Null
exit 0
