[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Executable,
    [Parameter(Mandatory = $true)]
    [string]$Manifest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$exe = [IO.Path]::GetFullPath($Executable)
$manifestPath = [IO.Path]::GetFullPath($Manifest)
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Executavel nao encontrado: $exe" }
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Manifesto nao encontrado: $manifestPath" }

$mt = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin" -Recurse -Filter mt.exe -File |
    Where-Object { $_.FullName -match '\\x64\\mt\.exe$' } |
    Sort-Object FullName -Descending |
    Select-Object -First 1
if (-not $mt) { throw "mt.exe do Windows SDK nao encontrado." }

& $mt.FullName -nologo -manifest $manifestPath "-outputresource:$exe;#1"
if ($LASTEXITCODE -ne 0) { throw "Falha ao incorporar manifesto requireAdministrator em $exe" }
Write-Host "[OK] Manifesto requireAdministrator aplicado: $exe"
