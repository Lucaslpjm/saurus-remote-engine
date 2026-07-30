# SAURUS_REMOTE_HEADLESS_UNINSTALL_V1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$InstallDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ServiceName = "SaurusRemote"
$ProductName = "Saurus Remote"
$ProgramDataDir = Join-Path $env:ProgramData "Saurus Software\Saurus Remote"
$LogPath = Join-Path $ProgramDataDir "uninstall.log"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$ScExe = Join-Path $env:SystemRoot "System32\sc.exe"
$NetshExe = Join-Path $env:SystemRoot "System32\netsh.exe"
New-Item -ItemType Directory -Path $ProgramDataDir -Force | Out-Null

function Log([string]$Message) {
    $line = "{0:yyyy-MM-dd HH:mm:ss.fff} {1}" -f (Get-Date), $Message
    [IO.File]::AppendAllText($LogPath, $line + [Environment]::NewLine, $Utf8NoBom)
}

function Invoke-ScBestEffort {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $previous = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = & $ScExe @Arguments 2>&1
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    Log "sc.exe $($Arguments -join ' ') => exit=$code; $((@($output) -join ' ').Trim())"
    return $code
}

try {
    Log "=== Inicio da desinstalacao headless ==="
    Get-Process -Name "SaurusRemote" -ErrorAction SilentlyContinue |
        Stop-Process -Force -ErrorAction SilentlyContinue

    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        [void](Invoke-ScBestEffort -Arguments @("stop", $ServiceName))
        try { $service.Dispose() } catch {}
        $service = $null
        Start-Sleep -Milliseconds 750
        $deleteCode = Invoke-ScBestEffort -Arguments @("delete", $ServiceName)
        if ($deleteCode -notin @(0, 1060, 1072)) {
            Log "Aviso: exclusao do servico retornou codigo $deleteCode."
        }
    }

    $limit = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $limit) {
        $remaining = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if (-not $remaining) { break }
        try { $remaining.Dispose() } catch {}
        Start-Sleep -Milliseconds 500
    }

    if (Test-Path -LiteralPath $NetshExe -PathType Leaf) {
        & $NetshExe advfirewall firewall delete rule name="$ProductName" | Out-Null
    }
    Log "=== Desinstalacao headless concluida ==="
    exit 0
} catch {
    Log "ERRO: $($_.Exception.Message)"
    # A remocao dos arquivos nao deve ficar bloqueada por uma limpeza secundaria.
    exit 0
}