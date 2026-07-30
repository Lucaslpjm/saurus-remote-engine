# SAURUS_REMOTE_POSTINSTALL_WATCHDOG_V1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$InstallDir,
    [int]$TimeoutSeconds = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ConfigureScript = Join-Path $InstallDir "tools\Configure-SaurusRemote.ps1"
$ProgramDataDir = Join-Path $env:ProgramData "Saurus Software\Saurus Remote"
$WatchdogLog = Join-Path $ProgramDataDir "install-watchdog.log"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
New-Item -ItemType Directory -Path $ProgramDataDir -Force | Out-Null

function Log([string]$Message) {
    $line = "{0:yyyy-MM-dd HH:mm:ss.fff} {1}" -f (Get-Date), $Message
    [IO.File]::AppendAllText($WatchdogLog, $line + [Environment]::NewLine, $Utf8NoBom)
}

try {
    if (-not (Test-Path -LiteralPath $ConfigureScript -PathType Leaf)) {
        throw "Configurador nao encontrado: $ConfigureScript"
    }

    $powerShellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    $arguments = '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' +
        $ConfigureScript + '" -InstallDir "' + $InstallDir + '"'

    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = $powerShellExe
    $psi.Arguments = $arguments
    $psi.WorkingDirectory = $InstallDir
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true

    $process = New-Object Diagnostics.Process
    $process.StartInfo = $psi
    [void]$process.Start()
    Log "Configurador iniciado. PID=$($process.Id); timeout=$TimeoutSeconds s."

    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        try { $process.Kill() } catch {}
        Log "Timeout. O configurador foi encerrado para liberar o instalador."
        exit 124
    }

    Log "Configurador encerrado com codigo $($process.ExitCode)."
    exit $process.ExitCode
} catch {
    Log "ERRO: $($_.Exception.Message)"
    exit 1
}