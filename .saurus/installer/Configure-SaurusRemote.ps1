[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InstallDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Product = "Saurus Remote"
$ServiceName = "SaurusRemote"
$Password = "ophd0202"
$InstallDir = [IO.Path]::GetFullPath($InstallDir)
$Exe = Join-Path $InstallDir "SaurusRemote.exe"
$ProgramDataDir = Join-Path $env:ProgramData "Saurus Software\Saurus Remote"
$LogPath = Join-Path $ProgramDataDir "install-config.log"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

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

function Run-Engine([string[]]$Arguments, [int]$TimeoutSeconds = 30) {
    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = $Exe
    $psi.WorkingDirectory = $InstallDir
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.Arguments = ($Arguments | ForEach-Object { if ($_ -match '\s') { '"' + $_.Replace('"','\"') + '"' } else { $_ } }) -join ' '
    $p = New-Object Diagnostics.Process
    $p.StartInfo = $psi
    [void]$p.Start()
    if (-not $p.WaitForExit($TimeoutSeconds * 1000)) {
        try { $p.Kill() } catch {}
        throw "Timeout executando: $Exe $($psi.Arguments)"
    }
    $stdout = $p.StandardOutput.ReadToEnd().Trim()
    $stderr = $p.StandardError.ReadToEnd().Trim()
    Log "CLI [$($psi.Arguments)] exit=$($p.ExitCode) stdout=[$stdout] stderr=[$stderr]"
    if ($p.ExitCode -ne 0) { throw "Comando do motor falhou: $($psi.Arguments)" }
    return ($stdout + "`n" + $stderr).Trim()
}

function Set-FixedPassword {
    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = $Exe
    $psi.Arguments = "--password-stdin"
    $psi.WorkingDirectory = $InstallDir
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $p = New-Object Diagnostics.Process
    $p.StartInfo = $psi
    [void]$p.Start()
    $p.StandardInput.WriteLine($Password)
    $p.StandardInput.Close()
    if (-not $p.WaitForExit(30000)) {
        try { $p.Kill() } catch {}
        throw "Timeout ao aplicar a senha permanente."
    }
    $stdout = $p.StandardOutput.ReadToEnd().Trim()
    $stderr = $p.StandardError.ReadToEnd().Trim()
    Log "Senha via stdin exit=$($p.ExitCode) stdout=[$stdout] stderr=[$stderr]"
    $confirmation = ($stdout + "`n" + $stderr).Trim()
    if ($p.ExitCode -ne 0 -or $confirmation -notmatch '(?i)\bDone\b|conclu[ií]d|success') {
        throw "O motor nao confirmou a aplicacao da senha permanente. Retorno: [$confirmation]"
    }
    Log "Senha permanente confirmada pelo motor."
}

function Set-ServiceReliability {
    & sc.exe config $ServiceName start= auto | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Falha ao configurar inicio automatico do servico." }

    & sc.exe failure $ServiceName reset= 86400 actions= restart/5000/restart/15000/restart/60000 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Falha ao configurar recuperacao do servico." }

    & sc.exe failureflag $ServiceName 1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Falha ao habilitar recuperacao em falhas sem encerramento." }
    Log "Servico configurado para inicio automatico e recuperacao em falhas."
}

function Set-TomlPreference([string]$Content, [string]$Key, [string]$Value) {
    $escapedKey = [Regex]::Escape($Key)
    $pattern = "(?m)^\s*$escapedKey\s*=\s*.*$"
    $line = "$Key = $Value"
    if ([Regex]::IsMatch($Content, $pattern)) {
        return [Regex]::Replace($Content, $pattern, $line, 1)
    }
    if ([string]::IsNullOrWhiteSpace($Content)) { return $line + "`r`n" }
    return $line + "`r`n" + $Content.TrimStart([char[]]@("`r", "`n"))
}

function Migrate-PeerDefaults([string]$ConfigRoot) {
    $peerDirectory = Join-Path $ConfigRoot "peers"
    if (-not (Test-Path -LiteralPath $peerDirectory -PathType Container)) { return 0 }

    $changed = 0
    foreach ($file in Get-ChildItem -LiteralPath $peerDirectory -Filter "*.toml" -File -Recurse -ErrorAction SilentlyContinue) {
        try {
            $content = [IO.File]::ReadAllText($file.FullName)
            $updated = Set-TomlPreference $content "view_style" "'adaptive'"
            $updated = Set-TomlPreference $updated "disable_audio" "true"
            if ($updated -ne $content) {
                [IO.File]::WriteAllText($file.FullName, $updated, $Utf8NoBom)
                $changed++
                Log "Preferencias de sessao migradas: $($file.FullName)"
            }
        } catch {
            Log "Aviso migrando preferencias em $($file.FullName): $($_.Exception.Message)"
        }
    }
    return $changed
}

function Get-ConfigRoots {
    $roots = New-Object System.Collections.Generic.List[string]
    $roots.Add((Join-Path $env:APPDATA "SaurusRemote\config"))
    $roots.Add((Join-Path $env:WINDIR "ServiceProfiles\LocalService\AppData\Roaming\SaurusRemote\config"))
    $roots.Add((Join-Path $env:SystemDrive "Users\Default\AppData\Roaming\SaurusRemote\config"))

    $usersRoot = Join-Path $env:SystemDrive "Users"
    if (Test-Path -LiteralPath $usersRoot -PathType Container) {
        foreach ($profile in Get-ChildItem -LiteralPath $usersRoot -Directory -ErrorAction SilentlyContinue) {
            $candidate = Join-Path $profile.FullName "AppData\Roaming\SaurusRemote\config"
            if (Test-Path -LiteralPath $candidate -PathType Container) { $roots.Add($candidate) }
        }
    }
    return $roots | Select-Object -Unique
}

function Write-DefaultConfig([string]$Directory) {
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null
    $path = Join-Path $Directory "SaurusRemote_default.toml"
    $content = "[options]`r`nview_style = 'adaptive'`r`ndisable_audio = 'Y'`r`n"
    [IO.File]::WriteAllText($path, $content, $Utf8NoBom)
    Log "Configuracao padrao gravada: $path"
}

try {
    Log "=== Inicio da configuracao pos-instalacao ==="
    if (-not (Test-Administrator)) { throw "A configuracao deve ser executada como administrador." }
    if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) { throw "Executavel nao encontrado: $Exe" }

    Get-Process -Name "SaurusRemote" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    $existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($existing) {
        try { Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue } catch {}
        try { Run-Engine @("--uninstall-service") 30 | Out-Null } catch { Log "Aviso removendo servico anterior: $($_.Exception.Message)" }
        for ($i = 0; $i -lt 20 -and (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue); $i++) { Start-Sleep -Milliseconds 500 }
    }

    Run-Engine @("--install-service") 45 | Out-Null
    for ($i = 0; $i -lt 30; $i++) {
        $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if ($svc -and $svc.Status -eq 'Running') { break }
        if ($svc) { try { Start-Service -Name $ServiceName -ErrorAction SilentlyContinue } catch {} }
        Start-Sleep -Seconds 1
    }
    $svc = Get-Service -Name $ServiceName -ErrorAction Stop
    if ($svc.Status -ne 'Running') { throw "O servico $ServiceName nao iniciou." }
    Log "Servico $ServiceName em execucao."
    Set-ServiceReliability

    # Configuracoes globais do lado controlado.
    Run-Engine @("--option", "verification-method", "use-permanent-password") | Out-Null
    Run-Engine @("--option", "approve-mode", "password") | Out-Null
    Run-Engine @("--option", "allow-logon-screen-password", "Y") | Out-Null
    Run-Engine @("--option", "allow-only-conn-window-open", "N") | Out-Null

    Set-FixedPassword

    # Bloqueia a troca depois de a senha correta ter sido persistida.
    Run-Engine @("--option", "disable-change-permanent-password", "Y") | Out-Null

    # Padroes de sessao para novos acessos e migracao das conexoes ja conhecidas.
    $migratedPeerFiles = 0
    foreach ($configRoot in Get-ConfigRoots) {
        Write-DefaultConfig $configRoot
        $migratedPeerFiles += Migrate-PeerDefaults $configRoot
    }
    Log "Migracao de preferencias concluida. Arquivos de pares alterados: $migratedPeerFiles"

    & netsh advfirewall firewall delete rule name="$Product" | Out-Null
    & netsh advfirewall firewall add rule name="$Product" dir=in action=allow program="$Exe" enable=yes profile=any | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Falha ao criar regra de firewall." }
    Log "Regra de firewall configurada."

    Restart-Service -Name $ServiceName -Force
    Start-Sleep -Seconds 3

    # Confirma novamente no IPC do servico reiniciado; nao basta a senha estar escrita na interface.
    Set-FixedPassword
    $verificationMethod = Run-Engine @("--option", "verification-method") 20
    if ($verificationMethod -notmatch '(?im)^\s*use-permanent-password\s*$') {
        throw "Metodo de verificacao efetivo nao foi confirmado: [$verificationMethod]"
    }
    $passwordLock = Run-Engine @("--option", "disable-change-permanent-password") 20
    if ($passwordLock -notmatch '(?im)^\s*(Y|true|1)\s*$') {
        throw "Bloqueio da senha permanente nao foi confirmado: [$passwordLock]"
    }
    Log "Senha e politica de autenticacao confirmadas apos reiniciar o servico."

    $id = Run-Engine @("--get-id") 20
    if ($id -notmatch '\d{6,}') { Log "Aviso: ID ainda nao disponivel: $id" } else { Log "ID confirmado: $id" }

    Log "=== Configuracao concluida com sucesso ==="
    exit 0
} catch {
    Log "ERRO: $($_.Exception.Message)"
    Log $_.ScriptStackTrace
    exit 1
}
