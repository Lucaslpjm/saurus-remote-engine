# SAURUS_REMOTE_ALWAYS_ADMIN_MANIFEST_V1
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
if (-not $manifestText.Contains('level="requireAdministrator"')) {
    throw "O manifesto do aplicativo deve exigir administrador."
}
if ($manifestText.Contains('level="asInvoker"')) {
    throw "O manifesto do aplicativo ainda permite execucao sem elevacao."
}

$mt = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin" -Recurse -Filter mt.exe -File |
    Where-Object { $_.FullName -match '\\x64\\mt\.exe$' } |
    Sort-Object FullName -Descending |
    Select-Object -First 1
if (-not $mt) { throw "mt.exe do Windows SDK nao encontrado." }

& $mt.FullName -nologo -manifest $manifestPath "-outputresource:$exe;#1"
if ($LASTEXITCODE -ne 0) { throw "Falha ao incorporar manifesto requireAdministrator em $exe" }

# SAURUS_REMOTE_VERIFY_EMBEDDED_MANIFEST_V1
$embeddedManifest = Join-Path ([IO.Path]::GetTempPath()) ("SaurusRemote-manifest-{0}.xml" -f [Guid]::NewGuid().ToString("N"))
try {
    & $mt.FullName -nologo "-inputresource:$exe;#1" "-out:$embeddedManifest"
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $embeddedManifest -PathType Leaf)) {
        throw "Falha ao extrair o manifesto incorporado de $exe"
    }
    $embeddedText = [IO.File]::ReadAllText($embeddedManifest)
    if (-not $embeddedText.Contains('level="requireAdministrator"') -or $embeddedText.Contains('level="asInvoker"')) {
        throw "O executavel final nao contem o manifesto requireAdministrator esperado: $exe"
    }
}
finally {
    Remove-Item -LiteralPath $embeddedManifest -Force -ErrorAction SilentlyContinue
}

Write-Host "[OK] Manifesto requireAdministrator aplicado e verificado no executavel: $exe"
