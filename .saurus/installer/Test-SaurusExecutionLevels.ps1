param(
    [Parameter(Mandatory = $true)][string]$EngineExecutable,
    [Parameter(Mandatory = $true)][string]$LauncherExecutable
)

$ErrorActionPreference = "Stop"
# SAURUS_REMOTE_SPLIT_ELEVATION_VERIFY_V1

$mt = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin" -Recurse -Filter mt.exe -File |
    Where-Object { $_.FullName -match '\\x64\\mt\.exe$' } |
    Sort-Object FullName -Descending |
    Select-Object -First 1
if (-not $mt) { throw "mt.exe do Windows SDK nao encontrado." }

function Read-EmbeddedManifest {
    param([Parameter(Mandatory = $true)][string]$Executable)

    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        throw "Executavel nao encontrado: $Executable"
    }
    $manifestFile = Join-Path ([IO.Path]::GetTempPath()) ("SaurusRemote-manifest-{0}.xml" -f [Guid]::NewGuid().ToString("N"))
    try {
        & $mt.FullName -nologo "-inputresource:$([IO.Path]::GetFullPath($Executable));#1" "-out:$manifestFile"
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $manifestFile -PathType Leaf)) {
            throw "Nao foi possivel extrair o manifesto incorporado: $Executable"
        }
        return [IO.File]::ReadAllText($manifestFile)
    }
    finally {
        Remove-Item -LiteralPath $manifestFile -Force -ErrorAction SilentlyContinue
    }
}

$engineManifest = Read-EmbeddedManifest -Executable $EngineExecutable
if ($engineManifest.Contains('level="requireAdministrator"')) {
    throw "O motor nao pode exigir elevacao: isso impede os modos service/server/tray."
}

$launcherManifest = Read-EmbeddedManifest -Executable $LauncherExecutable
if (-not $launcherManifest.Contains('level="requireAdministrator"') -or $launcherManifest.Contains('level="asInvoker"')) {
    throw "O launcher nao possui o manifesto requireAdministrator esperado."
}

Write-Host "[OK] Elevacao isolada: launcher=requireAdministrator; engine=asInvoker/default"
