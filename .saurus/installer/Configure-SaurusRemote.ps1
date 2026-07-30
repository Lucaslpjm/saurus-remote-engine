# SAURUS_REMOTE_HEADLESS_POSTINSTALL_V2
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$InstallDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Product = "Saurus Remote"
$ServiceName = "SaurusRemote"
$InstallDir = [IO.Path]::GetFullPath($InstallDir)
$Exe = Join-Path $InstallDir "SaurusRemote.exe"
$ProgramDataDir = Join-Path $env:ProgramData "Saurus Software\Saurus Remote"
$LogPath = Join-Path $ProgramDataDir "install-config.log"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$ScExe = Join-Path $env:SystemRoot "System32\sc.exe"

New-Item -ItemType Directory -Path $ProgramDataDir -Force | Out-Null

function Log([string]$Message) {
    $line = "{0:yyyy-MM-dd HH:mm:ss.fff} {1}" -f (Get-Date), $Message
    [IO.File]::AppendAllText($LogPath, $line + [Environment]::NewLine, $Utf8NoBom)
    Write-Host $line
}

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-Sc {
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [int[]]$AllowedExitCodes = @(0)
    )
    $previous = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = & $ScExe @Arguments 2>&1
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    Log "sc.exe $($Arguments -join ' ') => exit=$code; $((@($output) -join ' ').Trim())"
    if ($AllowedExitCodes -notcontains $code) {
        throw "sc.exe falhou com codigo ${code}: $($Arguments -join ' ')"
    }
}

function Wait-ServiceRunning([int]$TimeoutSeconds) {
    $limit = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if ($svc -and $svc.Status -eq 'Running') { return }
        Start-Sleep -Milliseconds 750
    } while ((Get-Date) -lt $limit)
    throw "Timeout aguardando o inicio do servico $ServiceName."
}

function Set-TomlPreference([string]$Content, [string]$Key, [string]$Value) {
    $pattern = "(?m)^\s*$([Regex]::Escape($Key))\s*=\s*.*$"
    $line = "$Key = $Value"
    if ([Regex]::IsMatch($Content, $pattern)) {
        $regex = New-Object System.Text.RegularExpressions.Regex($pattern, [System.Text.RegularExpressions.RegexOptions]::Multiline)
        return $regex.Replace($Content, $line, 1)
    }
    if ([string]::IsNullOrWhiteSpace($Content)) { return $line + "`r`n" }
    return $line + "`r`n" + $Content.TrimStart([char[]]@("`r", "`n"))
}

function Write-DefaultsAndMigrate([string]$ConfigRoot) {
    New-Item -ItemType Directory -Path $ConfigRoot -Force | Out-Null
    $defaultPath = Join-Path $ConfigRoot "SaurusRemote_default.toml"
    $defaultContent = "[options]`r`nview_style = 'adaptive'`r`ndisable_audio = 'Y'`r`n"
    [IO.File]::WriteAllText($defaultPath, $defaultContent, $Utf8NoBom)

    $peerRoot = Join-Path $ConfigRoot "peers"
    if (Test-Path -LiteralPath $peerRoot -PathType Container) {
        foreach ($file in Get-ChildItem -LiteralPath $peerRoot -Filter "*.toml" -File -Recurse -ErrorAction SilentlyContinue) {
            try {
                $content = [IO.File]::ReadAllText($file.FullName)
                $updated = Set-TomlPreference $content "view_style" "'adaptive'"
                $updated = Set-TomlPreference $updated "disable_audio" "true"
                if ($updated -ne $content) {
                    [IO.File]::WriteAllText($file.FullName, $updated, $Utf8NoBom)
                }
            } catch {
                Log "Aviso migrando $($file.FullName): $($_.Exception.Message)"
            }
        }
    }
}

function Get-ConfigRoots {
    $roots = New-Object System.Collections.Generic.List[string]
    $roots.Add((Join-Path $env:APPDATA "SaurusRemote\config"))
    $roots.Add((Join-Path $env:WINDIR "ServiceProfiles\LocalService\AppData\Roaming\SaurusRemote\config"))
    $roots.Add((Join-Path $env:WINDIR "System32\config\systemprofile\AppData\Roaming\SaurusRemote\config"))
    $roots.Add((Join-Path $env:SystemDrive "Users\Default\AppData\Roaming\SaurusRemote\config"))

    $usersRoot = Join-Path $env:SystemDrive "Users"
    if (Test-Path -LiteralPath $usersRoot -PathType Container) {
        foreach ($profile in Get-ChildItem -LiteralPath $usersRoot -Directory -ErrorAction SilentlyContinue) {
            $candidate = Join-Path $profile.FullName "AppData\Roaming\SaurusRemote\config"
            if (Test-Path -LiteralPath (Split-Path $candidate -Parent) -PathType Container) {
                $roots.Add($candidate)
            }
        }
    }
    return $roots | Select-Object -Unique
}

try {
    Log "=== Inicio da configuracao headless pos-instalacao ==="
    if (-not (Test-Administrator)) { throw "A configuracao requer privilegios administrativos." }
    if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) { throw "Executavel nao encontrado: $Exe" }

    Get-Process -Name "SaurusRemote" -ErrorAction SilentlyContinue |
        Stop-Process -Force -ErrorAction SilentlyContinue

    $binaryPath = '"' + $Exe + '" --service'
    $existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($existing) {
        Invoke-Sc -Arguments @("stop", $ServiceName) -AllowedExitCodes @(0, 1060, 1062)
        try { $existing.Dispose() } catch {}
        $existing = $null
        Invoke-Sc -Arguments @(
            "config", $ServiceName,
            "binPath=", $binaryPath,
            "start=", "auto",
            "obj=", "NT AUTHORITY\LocalService",
            "DisplayName=", $Product
        )
        Log "Servico existente atualizado sem exclusao/recriacao."
    } else {
        Invoke-Sc -Arguments @(
            "create", $ServiceName,
            "binPath=", $binaryPath,
            "start=", "auto",
            "obj=", "NT AUTHORITY\LocalService",
            "DisplayName=", $Product
        )
        Log "Servico criado."
    }
    Invoke-Sc -Arguments @("description", $ServiceName, "Servico de acesso remoto Saurus Remote")
    Invoke-Sc -Arguments @("failure", $ServiceName, "reset=", "86400", "actions=", "restart/5000/restart/15000/restart/60000")
    Invoke-Sc -Arguments @("failureflag", $ServiceName, "1")

    foreach ($root in Get-ConfigRoots) {
        Write-DefaultsAndMigrate $root
    }
    Log "Preferencias adaptativas e audio desativado aplicados."

    $netsh = Join-Path $env:SystemRoot "System32\netsh.exe"
    & $netsh advfirewall firewall delete rule name="$Product" | Out-Null
    & $netsh advfirewall firewall add rule name="$Product" dir=in action=allow program="$Exe" enable=yes profile=any | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Falha ao criar regra de firewall." }

    Invoke-Sc -Arguments @("start", $ServiceName)
    Wait-ServiceRunning 45

    # A senha ophd0202 e aplicada pelo motor customizado ao iniciar em modo normal,
    # servidor e servico. O instalador nao executa o binario grafico em modo CLI,
    # evitando abertura prematura da janela e travamento do Setup.
    Log "Servico iniciado. A senha fixa sera reforcada pelo motor customizado."
    Log "=== Configuracao headless concluida com sucesso ==="
    exit 0
} catch {
    Log "ERRO: $($_.Exception.Message)"
    Log $_.ScriptStackTrace
    exit 1
}