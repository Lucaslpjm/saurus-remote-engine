[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,
    [string]$OutputRoot = "",
    [string]$BuildLabel = "saurus.3.1.0",
    [switch]$ApplyCustomization,
    [switch]$WithoutHwCodec,
    [switch]$WithoutVram,
    [switch]$SkipPortable,
    [string]$SigningCertificateThumbprint = "",
    [string]$TimestampUrl = "http://timestamp.digicert.com"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = [IO.Path]::GetFullPath($SourceRoot)
if (-not $OutputRoot) { $OutputRoot = Join-Path $Root "dist-saurus" }
$OutputRoot = [IO.Path]::GetFullPath($OutputRoot)

if ($BuildLabel -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$') {
    throw "BuildLabel invalido. Use apenas letras, numeros, ponto, sublinhado e hifen (maximo 40 caracteres)."
}
$ProductVersion = "1.4.9-$BuildLabel"

function Require-Command {
    param([string]$Name)
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) { throw "Dependencia nao encontrada no PATH: $Name" }
    return $command.Source
}

function Find-Python {
    foreach ($candidate in @("python3", "python")) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) { return $command.Source }
    }
    throw "Python 3 nao encontrado no PATH."
}

function Find-SignTool {
    $direct = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($direct) { return $direct.Source }
    $kits = "${env:ProgramFiles(x86)}\Windows Kits\10\bin"
    if (Test-Path -LiteralPath $kits) {
        $tool = Get-ChildItem $kits -Recurse -Filter signtool.exe -File |
            Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($tool) { return $tool.FullName }
    }
    throw "signtool.exe nao encontrado. Instale o Windows SDK."
}

function Sign-Files {
    param([string]$Directory, [string]$Thumbprint)
    if ([string]::IsNullOrWhiteSpace($Thumbprint)) { return }
    $signTool = Find-SignTool
    Get-ChildItem -LiteralPath $Directory -Recurse -File |
        Where-Object { $_.Extension -in '.exe', '.dll' } |
        ForEach-Object {
            & $signTool sign /sha1 $Thumbprint /fd SHA256 /tr $TimestampUrl /td SHA256 $_.FullName
            if ($LASTEXITCODE -ne 0) { throw "Falha ao assinar $($_.FullName)." }
        }
}

Require-Command "git" | Out-Null
$python = Find-Python
Require-Command "rustc" | Out-Null
Require-Command "cargo" | Out-Null
Require-Command "flutter" | Out-Null

if (-not $env:VCPKG_ROOT -or -not (Test-Path -LiteralPath $env:VCPKG_ROOT -PathType Container)) {
    throw "VCPKG_ROOT nao esta definido ou nao aponta para uma instalacao valida. O workflow GitHub Actions e o caminho recomendado."
}

Push-Location $Root
try {
    git submodule update --init --recursive
    if ($LASTEXITCODE -ne 0) { throw "Falha ao atualizar submodulos." }

    if ($ApplyCustomization) {
        $preflight = Join-Path $PSScriptRoot "..\tools\check_upstream_149.py"
        & $python $preflight --source-root $Root
        if ($LASTEXITCODE -ne 0) { throw "O preflight do RustDesk 1.4.9 falhou." }

        & (Join-Path $PSScriptRoot "Apply-SaurusCustomization.ps1") -SourceRoot $Root
        if ($LASTEXITCODE -ne 0) { throw "Falha ao aplicar customizacao." }
    }
    & (Join-Path $PSScriptRoot "Verify-SaurusCustomization.ps1") -SourceRoot $Root
    if ($LASTEXITCODE -ne 0) { throw "A validacao da customizacao falhou." }

    $buildArgs = @(".\build.py", "--portable", "--flutter", "--skip-portable-pack")
    if (-not $WithoutHwCodec) { $buildArgs += "--hwcodec" }
    if (-not $WithoutVram) { $buildArgs += "--vram" }

    Write-Host "Executando: $python $($buildArgs -join ' ')"
    & $python @buildArgs
    if ($LASTEXITCODE -ne 0) { throw "build.py retornou codigo $LASTEXITCODE." }

    $releaseCandidates = @(
        (Join-Path $Root "flutter\build\windows\x64\runner\Release"),
        (Join-Path $Root "flutter\build\windows\runner\Release")
    )
    $releasePath = $releaseCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Container } | Select-Object -First 1
    if (-not $releasePath) { throw "Diretorio Release nao encontrado: $($releaseCandidates -join ', ')" }

    $stageRoot = Join-Path $OutputRoot "stage"
    $packagePath = Join-Path $stageRoot "SaurusRemote-Windows-x64"
    if (Test-Path -LiteralPath $stageRoot) { Remove-Item -LiteralPath $stageRoot -Recurse -Force }
    New-Item -ItemType Directory -Path $packagePath -Force | Out-Null
    Copy-Item -Path (Join-Path $releasePath "*") -Destination $packagePath -Recurse -Force

    $rustDeskExe = Join-Path $packagePath "rustdesk.exe"
    $saurusExe = Join-Path $packagePath "SaurusRemote.exe"
    if (Test-Path -LiteralPath $rustDeskExe -PathType Leaf) { Move-Item $rustDeskExe $saurusExe -Force }
    if (-not (Test-Path -LiteralPath $saurusExe -PathType Leaf)) { throw "SaurusRemote.exe nao encontrado no pacote final." }
    if (-not (Test-Path -LiteralPath (Join-Path $packagePath "librustdesk.dll") -PathType Leaf)) { throw "librustdesk.dll nao encontrada." }

    # O executavel principal sempre solicita elevacao, conforme requisito operacional.
    & (Join-Path $PSScriptRoot "..\installer\Set-RequireAdministratorManifest.ps1") `
        -Executable $saurusExe `
        -Manifest (Join-Path $PSScriptRoot "..\installer\SaurusRemote.requireAdministrator.manifest")
    if ($LASTEXITCODE -ne 0) { throw "Falha ao aplicar manifesto requireAdministrator." }

    $defaultsDir = Join-Path $packagePath "defaults"
    New-Item -ItemType Directory -Path $defaultsDir -Force | Out-Null
    Copy-Item `
        -LiteralPath (Join-Path $PSScriptRoot "..\installer\SaurusRemote_default.toml") `
        -Destination (Join-Path $defaultsDir "SaurusRemote_default.toml") `
        -Force

    Sign-Files -Directory $packagePath -Thumbprint $SigningCertificateThumbprint

    $manifest = [ordered]@{
        schemaVersion = 1
        product = "Saurus Remote Engine"
        displayName = "Saurus Remote"
        internalName = "SaurusRemote"
        upstreamVersion = "1.4.9"
        productVersion = $ProductVersion
        buildUtc = [DateTime]::UtcNow.ToString("o")
        architecture = "windows-x64"
        executable = "SaurusRemote.exe"
        serviceName = "SaurusRemote"
        installPath = "%ProgramFiles%\Saurus Software\Saurus Remote"
        userConfigPath = "%APPDATA%\SaurusRemote"
        serviceConfigPath = "%WINDIR%\ServiceProfiles\LocalService\AppData\Roaming\SaurusRemote"
        permanentPasswordEmbedded = $true
        fixedPasswordPolicy = $true
        passwordProvisioning = "normal/service/server enforcement plus installer stdin verification"
        defaultViewStyle = "adaptive"
        defaultDisableAudio = $true
        requiresAdministrator = $true
        definitiveInstallerIncluded = $true
        upstreamSelfUpdateEnabled = $false
        signed = -not [string]::IsNullOrWhiteSpace($SigningCertificateThumbprint)
    }
    $manifest | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $packagePath "engine-manifest.json") -Encoding UTF8

    New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
    $zipPath = Join-Path $OutputRoot "SaurusRemote-$ProductVersion-Windows-x64.zip"
    if (Test-Path -LiteralPath $zipPath) { Remove-Item $zipPath -Force }
    Compress-Archive -Path (Join-Path $packagePath "*") -DestinationPath $zipPath -CompressionLevel Optimal

    $portablePath = $null
    if (-not $SkipPortable) {
        $runnerRes = Get-ChildItem -Path $Root -Recurse -Filter Runner.res -File |
            Where-Object { $_.FullName -notmatch '\\libs\\portable\\Runner\.res$' } |
            Select-Object -First 1
        if (-not $runnerRes) { throw "Runner.res nao foi localizado para o empacotador portatil." }
        Copy-Item $runnerRes.FullName (Join-Path $Root "libs\portable\Runner.res") -Force

        $manifestPath = Join-Path $Root "res\manifest.xml"
        $manifestLines = Get-Content -LiteralPath $manifestPath
        $manifestLines | Where-Object { $_ -notmatch 'dpiAware' } | Set-Content $manifestPath -Encoding UTF8

        Push-Location (Join-Path $Root "libs\portable")
        try {
            & $python -m pip install -r requirements.txt
            if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependencias do portable packer." }
            & $python .\generate.py -f $packagePath -o . -e $saurusExe
            if ($LASTEXITCODE -ne 0) { throw "generate.py retornou codigo $LASTEXITCODE." }
        } finally { Pop-Location }

        $packer = Join-Path $Root "target\release\rustdesk-portable-packer.exe"
        if (-not (Test-Path -LiteralPath $packer -PathType Leaf)) { throw "Portable packer nao foi gerado." }
        $portablePath = Join-Path $OutputRoot "SaurusRemote-$ProductVersion-Windows-x64.exe"
        Move-Item $packer $portablePath -Force
        & (Join-Path $PSScriptRoot "..\installer\Set-RequireAdministratorManifest.ps1") `
            -Executable $portablePath `
            -Manifest (Join-Path $PSScriptRoot "..\installer\SaurusRemote.requireAdministrator.manifest")
        if ($LASTEXITCODE -ne 0) { throw "Falha ao aplicar manifesto ao portatil." }
        if ($SigningCertificateThumbprint) {
            $signTool = Find-SignTool
            & $signTool sign /sha1 $SigningCertificateThumbprint /fd SHA256 /tr $TimestampUrl /td SHA256 $portablePath
            if ($LASTEXITCODE -ne 0) { throw "Falha ao assinar o executavel portatil." }
        }
    }

    $setupPath = $null
    $isccCandidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
    )
    $iscc = $isccCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if ($iscc) {
        $installerRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\installer"))
        $brandingRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\branding"))
        & $iscc `
            "/DSourceRoot=$packagePath" `
            "/DOutputDir=$OutputRoot" `
            "/DProductVersion=$ProductVersion" `
            "/DInstallerRoot=$installerRoot" `
            "/DBrandingRoot=$brandingRoot" `
            (Join-Path $installerRoot "SaurusRemote.iss")
        if ($LASTEXITCODE -ne 0) { throw "Falha ao compilar o instalador definitivo." }
        $setupPath = Join-Path $OutputRoot "SaurusRemote-$ProductVersion-Setup.exe"
        if (-not (Test-Path -LiteralPath $setupPath -PathType Leaf)) { throw "Instalador final nao foi encontrado." }
        if ($SigningCertificateThumbprint) {
            $signTool = Find-SignTool
            & $signTool sign /sha1 $SigningCertificateThumbprint /fd SHA256 /tr $TimestampUrl /td SHA256 $setupPath
            if ($LASTEXITCODE -ne 0) { throw "Falha ao assinar o instalador definitivo." }
        }
    } else {
        Write-Warning "Inno Setup 6 nao encontrado. ZIP e portatil serao gerados, mas o instalador Setup nao sera criado localmente."
    }

    $hashFiles = @($zipPath)
    if ($portablePath) { $hashFiles += $portablePath }
    if ($setupPath) { $hashFiles += $setupPath }
    $hashFiles += (Join-Path $packagePath "engine-manifest.json")
    $hashLines = foreach ($file in $hashFiles) {
        $hash = (Get-FileHash $file -Algorithm SHA256).Hash.ToLowerInvariant()
        "$hash *$([IO.Path]::GetFileName($file))"
    }
    $hashLines | Set-Content (Join-Path $OutputRoot "SHA256SUMS.txt") -Encoding ASCII

    Write-Host ""
    Write-Host "Build concluido." -ForegroundColor Green
    Write-Host "Pasta: $packagePath"
    Write-Host "ZIP: $zipPath"
    if ($portablePath) { Write-Host "Portatil: $portablePath" }
    if ($setupPath) { Write-Host "Instalador: $setupPath" }
}
finally {
    Pop-Location
}
