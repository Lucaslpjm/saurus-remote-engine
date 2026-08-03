# SAURUS_REMOTE_HEADLESS_POSTINSTALL_V4
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$InstallDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Product = "Saurus Remote"
$ServiceName = "SaurusRemote"
$ServiceAccount = "NT AUTHORITY\LocalService"
$ServicePassword = ""
$RendezvousServer = "20.195.216.23:443"
$PublicKey = "OJ7QiUrqNu0wM13vDSp4nmAlDu6hy3n8hTI5Wksl2Tc="
$InstallDir = [IO.Path]::GetFullPath($InstallDir)
$Exe = Join-Path $InstallDir "SaurusRemote.exe"
$ProgramDataDir = Join-Path $env:ProgramData "Saurus Software\Saurus Remote"
$LogPath = Join-Path $ProgramDataDir "install-config.log"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$ScExe = Join-Path $env:SystemRoot "System32\sc.exe"

New-Item -ItemType Directory -Path $ProgramDataDir -Force | Out-Null

function Rotate-InstallLog {
    if (-not (Test-Path -LiteralPath $LogPath -PathType Leaf)) { return }
    try {
        $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $archive = Join-Path $ProgramDataDir "install-config-$timestamp.log"
        Move-Item -LiteralPath $LogPath -Destination $archive -Force
    }
    catch {
        [IO.File]::WriteAllText($LogPath, "", $Utf8NoBom)
    }
}

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

function Get-WmiManagedService {
    return Get-WmiObject `
        -Namespace "root\cimv2" `
        -Class "Win32_Service" `
        -Filter "Name='$ServiceName'" `
        -ErrorAction SilentlyContinue
}

function Get-WmiReturnDescription([int]$Code) {
    $descriptions = @{
        0 = "Success"
        1 = "Not Supported"
        2 = "Access Denied"
        3 = "Dependent Services Running"
        4 = "Invalid Service Control"
        5 = "Service Cannot Accept Control"
        6 = "Service Not Active"
        7 = "Service Request Timeout"
        8 = "Unknown Failure"
        9 = "Path Not Found"
        10 = "Service Already Running"
        11 = "Service Database Locked"
        12 = "Service Dependency Deleted"
        13 = "Service Dependency Failure"
        14 = "Service Disabled"
        15 = "Service Logon Failure"
        16 = "Service Marked For Deletion"
        17 = "Service No Thread"
        18 = "Status Circular Dependency"
        19 = "Status Duplicate Name"
        20 = "Status Invalid Name"
        21 = "Status Invalid Parameter"
        22 = "Status Invalid Service Account"
        23 = "Status Service Exists"
        24 = "Service Already Paused"
    }
    if ($descriptions.ContainsKey($Code)) { return $descriptions[$Code] }
    return "Codigo WMI desconhecido"
}

function Assert-WmiSuccess {
    param(
        [Parameter(Mandatory = $true)][AllowNull()]$Result,
        [Parameter(Mandatory = $true)][string]$Operation
    )

    if ($null -eq $Result -or $null -eq $Result.ReturnValue) {
        throw "$Operation nao retornou um codigo WMI valido."
    }

    $code = [int]$Result.ReturnValue
    Log "$Operation => ReturnValue=$code ($(Get-WmiReturnDescription $code))"
    if ($code -ne 0) {
        throw "$Operation falhou com codigo WMI $code ($(Get-WmiReturnDescription $code))."
    }
}

function Stop-ManagedService {
    $controller = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($null -eq $controller) { return }

    try {
        if ($controller.Status -ne [System.ServiceProcess.ServiceControllerStatus]::Stopped) {
            Stop-Service -Name $ServiceName -Force -ErrorAction Stop
            $controller.Refresh()
            $controller.WaitForStatus(
                [System.ServiceProcess.ServiceControllerStatus]::Stopped,
                [TimeSpan]::FromSeconds(30)
            )
        }
    }
    finally {
        try { $controller.Dispose() } catch {}
    }
}

function Set-OrCreateManagedService {
    $binaryPath = '"' + $Exe + '" --service'
    $existing = Get-WmiManagedService

    if ($null -ne $existing) {
        Stop-ManagedService
        $existing = Get-WmiManagedService
        if ($null -eq $existing) {
            throw "O servico desapareceu durante a atualizacao."
        }

        $changeResult = $existing.Change(
            $Product,
            $binaryPath,
            [uint32]16,
            [uint32]1,
            "Automatic",
            $false,
            $ServiceAccount,
            $ServicePassword,
            $null,
            $null,
            $null
        )
        Assert-WmiSuccess -Result $changeResult -Operation "Win32_Service.Change"
        Log "Servico existente atualizado via Win32_Service.Change."
    }
    else {
        $serviceClass = [wmiclass]"\\.\root\cimv2:Win32_Service"
        $createResult = $serviceClass.Create(
            $ServiceName,
            $Product,
            $binaryPath,
            [uint32]16,
            [uint32]1,
            "Automatic",
            $false,
            $ServiceAccount,
            $ServicePassword,
            $null,
            $null,
            $null
        )
        Assert-WmiSuccess -Result $createResult -Operation "Win32_Service.Create"
        Log "Servico criado via Win32_Service.Create."
    }

    $serviceKey = "HKLM:\SYSTEM\CurrentControlSet\Services\$ServiceName"
    if (-not (Test-Path -LiteralPath $serviceKey -PathType Container)) {
        throw "A chave do servico nao foi criada: $serviceKey"
    }
    New-ItemProperty `
        -LiteralPath $serviceKey `
        -Name "Description" `
        -Value "Servico de acesso remoto Saurus Remote" `
        -PropertyType String `
        -Force | Out-Null
    New-ItemProperty `
        -LiteralPath $serviceKey `
        -Name "DelayedAutostart" `
        -Value 1 `
        -PropertyType DWord `
        -Force | Out-Null

    $verified = Get-WmiManagedService
    if ($null -eq $verified) {
        throw "O servico nao foi encontrado depois da criacao/atualizacao."
    }
    if (-not $verified.PathName.Contains($Exe) -or -not $verified.PathName.Contains("--service")) {
        throw "Caminho efetivo inesperado no servico: $($verified.PathName)"
    }
    if ($verified.StartName -notmatch '(?i)LocalService$') {
        throw "Conta efetiva inesperada no servico: $($verified.StartName)"
    }
    Log "Servico verificado: PathName=[$($verified.PathName)]; StartName=[$($verified.StartName)]; StartMode=[$($verified.StartMode)]."
}

function Invoke-ScReliability {
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [int[]]$AllowedExitCodes = @(0)
    )

    $previous = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = @(& $ScExe @Arguments 2>&1)
        $code = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previous
    }

    Log "sc.exe $($Arguments -join ' ') => exit=$code; $((@($output) -join ' ').Trim())"
    if ($AllowedExitCodes -notcontains $code) {
        throw "sc.exe falhou ao configurar recuperacao. Codigo ${code}: $($Arguments -join ' ')"
    }
}

function Wait-ServiceStable {
    param(
        [int]$TimeoutSeconds,
        [int]$StableSeconds = 8
    )

    $limit = (Get-Date).AddSeconds($TimeoutSeconds)
    $stableSince = $null
    do {
        $service = Get-WmiManagedService
        if ($null -ne $service -and
            $service.State -eq "Running" -and
            [uint32]$service.ProcessId -gt 0) {
            if ($null -eq $stableSince) {
                $stableSince = Get-Date
            }
            if (((Get-Date) - $stableSince).TotalSeconds -ge $StableSeconds) {
                Log "Servico permaneceu estavel por $StableSeconds segundos; PID=$($service.ProcessId)."
                return
            }
        }
        else {
            $stableSince = $null
            if ($null -ne $service -and $service.State -eq "Stopped") {
                Log "Servico parou durante a validacao; ExitCode=$($service.ExitCode); ServiceSpecificExitCode=$($service.ServiceSpecificExitCode)."
            }
        }
        Start-Sleep -Milliseconds 750
    } while ((Get-Date) -lt $limit)

    throw "O servico nao permaneceu em execucao de forma estavel dentro de $TimeoutSeconds segundos."
}

function Write-ServiceDiagnostics {
    try {
        $service = Get-WmiManagedService
        if ($null -eq $service) {
            Log "Diagnostico do servico: Win32_Service nao encontrado."
            return
        }
        Log "Diagnostico do servico: State=[$($service.State)]; Status=[$($service.Status)]; StartMode=[$($service.StartMode)]; StartName=[$($service.StartName)]; PathName=[$($service.PathName)]; ExitCode=[$($service.ExitCode)]; ServiceSpecificExitCode=[$($service.ServiceSpecificExitCode)]."
    }
    catch {
        Log "Falha ao coletar diagnostico do servico: $($_.Exception.Message)"
    }
}

function Set-TomlRootPreference([string]$Content, [string]$Key, [string]$Value) {
    $pattern = "(?m)^\s*$([Regex]::Escape($Key))\s*=\s*.*$"
    $line = "$Key = $Value"
    if ([Regex]::IsMatch($Content, $pattern)) {
        return [Regex]::Replace($Content, $pattern, $line, 1)
    }

    $sectionMatch = [Regex]::Match($Content, '(?m)^\s*\[[^\]]+\]\s*$')
    if ($sectionMatch.Success) {
        return $Content.Insert($sectionMatch.Index, $line + "`r`n")
    }
    if ([string]::IsNullOrWhiteSpace($Content)) { return $line + "`r`n" }
    return $line + "`r`n" + $Content.TrimStart([char[]]@("`r", "`n"))
}

function Set-TomlOptionPreference([string]$Content, [string]$Key, [string]$Value) {
    $pattern = "(?m)^\s*$([Regex]::Escape($Key))\s*=\s*.*$"
    $line = "$Key = $Value"
    if ([Regex]::IsMatch($Content, $pattern)) {
        return [Regex]::Replace($Content, $pattern, $line, 1)
    }

    $optionsPattern = '(?m)^\s*\[options\]\s*$'
    $optionsMatch = [Regex]::Match($Content, $optionsPattern)
    if ($optionsMatch.Success) {
        $insertAt = $optionsMatch.Index + $optionsMatch.Length
        return $Content.Insert($insertAt, "`r`n" + $line)
    }

    $trimmed = $Content.TrimEnd([char[]]@("`r", "`n"))
    if ($trimmed.Length -gt 0) { $trimmed += "`r`n`r`n" }
    return $trimmed + "[options]`r`n" + $line + "`r`n"
}

function Write-DefaultsAndMigrate([string]$ConfigRoot) {
    New-Item -ItemType Directory -Path $ConfigRoot -Force | Out-Null

    $defaultPath = Join-Path $ConfigRoot "SaurusRemote_default.toml"
    $defaultContent = "[options]`r`nview_style = 'adaptive'`r`ndisable_audio = 'Y'`r`n"
    [IO.File]::WriteAllText($defaultPath, $defaultContent, $Utf8NoBom)

    $networkPath = Join-Path $ConfigRoot "SaurusRemote2.toml"
    $networkContent = if (Test-Path -LiteralPath $networkPath -PathType Leaf) {
        [IO.File]::ReadAllText($networkPath)
    }
    else {
        ""
    }
    $networkContent = Set-TomlRootPreference $networkContent "rendezvous_server" ("'" + $RendezvousServer + "'")
    $networkContent = Set-TomlOptionPreference $networkContent "custom-rendezvous-server" ("'" + $RendezvousServer + "'")
    $networkContent = Set-TomlOptionPreference $networkContent "key" ("'" + $PublicKey + "'")
    $networkContent = Set-TomlOptionPreference $networkContent "relay-server" "''"
    $networkContent = Set-TomlOptionPreference $networkContent "api-server" "''"
    [IO.File]::WriteAllText($networkPath, $networkContent, $Utf8NoBom)

    $peerRoot = Join-Path $ConfigRoot "peers"
    if (Test-Path -LiteralPath $peerRoot -PathType Container) {
        foreach ($file in Get-ChildItem -LiteralPath $peerRoot -Filter "*.toml" -File -Recurse -ErrorAction SilentlyContinue) {
            try {
                $content = [IO.File]::ReadAllText($file.FullName)
                $updated = Set-TomlOptionPreference $content "view_style" "'adaptive'"
                $updated = Set-TomlOptionPreference $updated "disable_audio" "true"
                if ($updated -ne $content) {
                    [IO.File]::WriteAllText($file.FullName, $updated, $Utf8NoBom)
                }
            }
            catch {
                Log "Aviso migrando $($file.FullName): $($_.Exception.Message)"
            }
        }
    }

    Log "Configuracao de rede aplicada em $networkPath."
}

function Get-ConfigRoots {
    # SAURUS_REMOTE_SCOPED_CONFIG_ROOTS_V1
    # O instalador configura somente a identidade que executa a UI elevada e a conta
    # do serviço. Não cria nem altera arquivos dentro de perfis de outros usuários.
    $roots = New-Object System.Collections.Generic.List[string]
    $roots.Add((Join-Path $env:APPDATA "SaurusRemote\config"))
    $roots.Add((Join-Path $env:WINDIR "ServiceProfiles\LocalService\AppData\Roaming\SaurusRemote\config"))
    return $roots | Select-Object -Unique
}

function Set-FirewallRule {
    $newRule = Get-Command -Name "New-NetFirewallRule" -ErrorAction SilentlyContinue
    $removeRule = Get-Command -Name "Remove-NetFirewallRule" -ErrorAction SilentlyContinue
    $getRule = Get-Command -Name "Get-NetFirewallRule" -ErrorAction SilentlyContinue
    if ($null -eq $newRule -or $null -eq $removeRule -or $null -eq $getRule) {
        throw "Os cmdlets de firewall do Windows nao estao disponiveis."
    }

    Get-NetFirewallRule -DisplayName $Product -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule -ErrorAction SilentlyContinue

    New-NetFirewallRule `
        -DisplayName $Product `
        -Direction Inbound `
        -Action Allow `
        -Program $Exe `
        -Profile Domain,Private `
        -Enabled True `
        -ErrorAction Stop | Out-Null

    Log "Regra de firewall configurada somente para redes de Dominio e Privadas."
}

try {
    Rotate-InstallLog
    Log "=== Inicio da configuracao headless pos-instalacao V4 ==="
    if (-not (Test-Administrator)) { throw "A configuracao requer privilegios administrativos." }
    if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) { throw "Executavel nao encontrado: $Exe" }

    Stop-ManagedService
    Get-Process -Name "SaurusRemote" -ErrorAction SilentlyContinue |
        Stop-Process -Force -ErrorAction SilentlyContinue

    Set-OrCreateManagedService

    Invoke-ScReliability -Arguments @(
        "failure",
        $ServiceName,
        "reset=",
        "86400",
        "actions=",
        "restart/5000/restart/15000/restart/60000"
    )
    Invoke-ScReliability -Arguments @("failureflag", $ServiceName, "1")

    foreach ($root in Get-ConfigRoots) {
        Write-DefaultsAndMigrate $root
    }
    Log "Preferencias adaptativas, audio desativado e servidor Saurus aplicados."

    Set-FirewallRule

    Start-Service -Name $ServiceName -ErrorAction Stop
    Wait-ServiceStable -TimeoutSeconds 45 -StableSeconds 8

    Log "Servico iniciado. A senha fixa sera reforcada pelo motor customizado."
    Log "=== Configuracao headless V4 concluida com sucesso ==="
    exit 0
}
catch {
    Log "ERRO: $($_.Exception.Message)"
    Log $_.ScriptStackTrace
    Write-ServiceDiagnostics
    exit 1
}
