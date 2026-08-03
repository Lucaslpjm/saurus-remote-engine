param(
    [Parameter(Mandatory = $true)][string]$OutputExecutable,
    [Parameter(Mandatory = $true)][string]$Manifest,
    [Parameter(Mandatory = $true)][string]$Icon,
    [string]$NumericVersion = "1.4.9.0"
)

$ErrorActionPreference = "Stop"
# SAURUS_REMOTE_SPLIT_ELEVATION_LAUNCHER_V1

$source = Join-Path $PSScriptRoot "SaurusRemoteLauncher.cs"
foreach ($required in @($source, $Manifest, $Icon)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Arquivo necessario para o launcher nao encontrado: $required"
    }
}

if ($NumericVersion -notmatch '^\d+\.\d+\.\d+\.\d+$') {
    throw "NumericVersion deve conter quatro partes numericas: $NumericVersion"
}

$compilerCandidates = @(
    "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
    "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\csc.exe"
)
$compiler = $compilerCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $compiler) {
    throw "Compilador C# do .NET Framework nao encontrado."
}

$output = [IO.Path]::GetFullPath($OutputExecutable)
$outputDirectory = Split-Path -Parent $output
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

$assemblyInfo = Join-Path ([IO.Path]::GetTempPath()) ("SaurusRemoteLauncher-{0}.cs" -f [Guid]::NewGuid().ToString("N"))
try {
    @"
[assembly: System.Reflection.AssemblyVersion("$NumericVersion")]
[assembly: System.Reflection.AssemblyFileVersion("$NumericVersion")]
"@ | Set-Content -LiteralPath $assemblyInfo -Encoding UTF8

    & $compiler /nologo /target:winexe /optimize+ /platform:x64 `
        "/out:$output" `
        "/win32manifest:$([IO.Path]::GetFullPath($Manifest))" `
        "/win32icon:$([IO.Path]::GetFullPath($Icon))" `
        /reference:System.dll /reference:System.Windows.Forms.dll `
        $source $assemblyInfo
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $output -PathType Leaf)) {
        throw "Falha ao compilar o launcher administrativo do Saurus Remote."
    }
}
finally {
    Remove-Item -LiteralPath $assemblyInfo -Force -ErrorAction SilentlyContinue
}

Write-Host "[OK] Launcher administrativo gerado: $output"
