[CmdletBinding()]
param(
    [string]$EnginePath = "$env:ProgramFiles\Saurus Software\Saurus Remote\SaurusRemote.exe",
    [string]$Password = "ophd0202"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Execute este script em um PowerShell elevado ou delegue ao helper elevado do launcher.'
}
if (-not (Test-Path -LiteralPath $EnginePath -PathType Leaf)) {
    throw "Motor nao encontrado: $EnginePath"
}
if ($Password -ne 'ophd0202') {
    throw 'A política operacional do Saurus Remote permite somente a senha padrão definida.'
}

$psi = New-Object Diagnostics.ProcessStartInfo
$psi.FileName = $EnginePath
$psi.Arguments = '--password-stdin'
$psi.WorkingDirectory = Split-Path -Parent $EnginePath
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true

$process = New-Object Diagnostics.Process
$process.StartInfo = $psi
if (-not $process.Start()) { throw 'Nao foi possivel iniciar o motor.' }
$process.StandardInput.WriteLine($Password)
$process.StandardInput.Close()
if (-not $process.WaitForExit(15000)) {
    try { $process.Kill() } catch {}
    throw 'Timeout ao provisionar senha.'
}
$output = ($process.StandardOutput.ReadToEnd() + "`n" + $process.StandardError.ReadToEnd()).Trim()
if ($process.ExitCode -ne 0 -or $output -notmatch 'Done!') {
    throw "Motor recusou a senha. Saida: $output"
}

Write-Output ([pscustomobject]@{
    Password = $Password
    Provisioned = $true
    Engine = $EnginePath
})
