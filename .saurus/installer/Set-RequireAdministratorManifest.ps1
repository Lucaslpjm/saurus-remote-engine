# SAURUS_REMOTE_AS_INVOKER_MANIFEST_V1
# Nome legado preservado para compatibilidade com o workflow e o build local.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Executable,
    [Parameter(Mandatory = $true)][string]$Manifest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$exe = [IO.Path]::GetFullPath($Executable)
$manifestPath = [IO.Path]::GetFullPath($Manifest)
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Executavel nao encontrado: $exe" }
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Manifesto nao encontrado: $manifestPath" }

$manifestText = [IO.File]::ReadAllText($manifestPath)
if (-not $manifestText.Contains('level="asInvoker"')) {
    throw "O manifesto do aplicativo deve usar asInvoker."
}
if ($manifestText.Contains('level="requireAdministrator"')) {
    throw "O manifesto do aplicativo ainda exige administrador."
}

$mt = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin" -Recurse -Filter mt.exe -File |
    Where-Object { $_.FullName -match '\\x64\\mt\.exe$' } |
    Sort-Object FullName -Descending |
    Select-Object -First 1
if (-not $mt) { throw "mt.exe do Windows SDK nao encontrado." }

& $mt.FullName -nologo -manifest $manifestPath "-outputresource:$exe;#1"
if ($LASTEXITCODE -ne 0) { throw "Falha ao incorporar manifesto asInvoker em $exe" }
Write-Host "[OK] Manifesto asInvoker aplicado: $exe"
