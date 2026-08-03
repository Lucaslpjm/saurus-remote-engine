[CmdletBinding()]
param(
    [string]$OutputDirectory = "$env:USERPROFILE\Desktop\SaurusRemote-Diagnostico",
    [string]$ServerHost = "20.195.216.23",
    [int[]]$TcpPorts = @(443, 21115, 21116, 21117)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$services = Get-CimInstance Win32_Service | Where-Object { $_.Name -match 'SaurusRemote|RustDesk' } |
    Select-Object Name, DisplayName, State, StartMode, PathName
$processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match 'SaurusRemote|RustDesk' } |
    Select-Object Name, ProcessId, SessionId, ExecutablePath, CommandLine
$network = foreach ($port in $TcpPorts) {
    $test = Test-NetConnection -ComputerName $ServerHost -Port $port -WarningAction SilentlyContinue
    [pscustomobject]@{ Host = $ServerHost; Port = $port; TcpSucceeded = $test.TcpTestSucceeded; RemoteAddress = $test.RemoteAddress }
}

$configPaths = @(
    "$env:APPDATA\SaurusRemote",
    "$env:APPDATA\RustDesk",
    "$env:WINDIR\System32\config\systemprofile\AppData\Roaming\SaurusRemote",
    "$env:WINDIR\ServiceProfiles\LocalService\AppData\Roaming\SaurusRemote",
    "$env:WINDIR\ServiceProfiles\LocalService\AppData\Roaming\RustDesk"
)
$configSummary = foreach ($path in $configPaths) {
    [pscustomobject]@{ Path = $path; Exists = Test-Path -LiteralPath $path; LastWriteTime = (Get-Item -LiteralPath $path -ErrorAction SilentlyContinue).LastWriteTime }
}

$report = [ordered]@{
    GeneratedAt = (Get-Date).ToString('o')
    Computer = $env:COMPUTERNAME
    User = $env:USERNAME
    OS = (Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture, LastBootUpTime)
    Services = $services
    Processes = $processes
    Network = $network
    ConfigPaths = $configSummary
}
$reportPath = Join-Path $OutputDirectory 'diagnostico.json'
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportPath -Encoding UTF8

# Copia somente logs; arquivos TOML podem conter dados sensíveis e não são exportados automaticamente.
$logCandidates = @(
    "$env:APPDATA\SaurusRemote\log",
    "$env:WINDIR\System32\config\systemprofile\AppData\Roaming\SaurusRemote\log",
    "$env:WINDIR\ServiceProfiles\LocalService\AppData\Roaming\SaurusRemote\log"
)
foreach ($logDir in $logCandidates) {
    if (Test-Path -LiteralPath $logDir -PathType Container) {
        $dest = Join-Path $OutputDirectory ((Split-Path $logDir -Leaf) + '-' + [guid]::NewGuid().ToString('N').Substring(0, 6))
        Copy-Item -LiteralPath $logDir -Destination $dest -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Diagnóstico salvo em: $OutputDirectory"
Write-Host "Revise o conteúdo antes de encaminhar; senhas e arquivos TOML não foram incluídos."
