[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$PortableEngine,
    [string]$ExpectedSha256 = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$engine = [IO.Path]::GetFullPath($PortableEngine)
if (-not (Test-Path -LiteralPath $engine -PathType Leaf)) { throw "Arquivo ausente: $engine" }
if ($ExpectedSha256) {
    $actual = (Get-FileHash $engine -Algorithm SHA256).Hash
    if ($actual -ne $ExpectedSha256) { throw 'SHA-256 divergente.' }
}

$signature = Get-AuthenticodeSignature $engine
if ($signature.Status -ne 'Valid') { throw "Assinatura Authenticode invalida: $($signature.Status)" }

$process = Start-Process -FilePath $engine -ArgumentList '--silent-install' -Verb RunAs -PassThru -Wait
if ($process.ExitCode -ne 0) { throw "Instalacao retornou codigo $($process.ExitCode)." }

$deadline = [DateTime]::UtcNow.AddSeconds(30)
do {
    $service = Get-Service -Name SaurusRemote -ErrorAction SilentlyContinue
    if ($service -and $service.Status -eq 'Running') { break }
    Start-Sleep -Milliseconds 500
} while ([DateTime]::UtcNow -lt $deadline)
if (-not $service -or $service.Status -ne 'Running') { throw 'Servico SaurusRemote nao ficou pronto.' }

$svc = Get-CimInstance Win32_Service -Filter "Name='SaurusRemote'"
if ($svc.PathName -match '\\RustDesk\\') { throw 'Servico aponta para a instalacao RustDesk original.' }
$svc | Select-Object Name, DisplayName, State, PathName
