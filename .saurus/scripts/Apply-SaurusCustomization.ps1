[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,

    [string]$InternalName = "SaurusRemote",
    [string]$DisplayName = "Saurus Remote",
    [string]$RendezvousServer = "20.195.216.23:443",
    [string]$PublicKey = "OJ7QiUrqNu0wM13vDSp4nmAlDu6hy3n8hTI5Wksl2Tc=",
    [string]$DefaultAccessPassword = "ophd0202",
    [string]$InstallSubdirectory = "Saurus Software\Saurus Remote",
    [string]$InstallerRegistryKey = "{1117CE17-506B-4122-A421-69233FCA9C12}_is1",
    [switch]$AllowDifferentUpstreamVersion
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Resolve-SourceFile {
    param([string]$RelativePath)
    $path = Join-Path $script:Root $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Arquivo obrigatório não encontrado: $path. Confirme que o clone foi feito com --recurse-submodules."
    }
    return $path
}

function Read-TextFile {
    param([string]$Path)
    return [System.IO.File]::ReadAllText($Path)
}

function Write-TextFile {
    param([string]$Path, [string]$Content)
    [System.IO.File]::WriteAllText($Path, $Content, $Utf8NoBom)
}

function Replace-LiteralRequired {
    param(
        [string]$Path,
        [string]$OldValue,
        [string]$NewValue,
        [string]$Description,
        [int]$MinimumMatches = 1
    )

    $content = Read-TextFile $Path
    if ($content.Contains($NewValue) -and -not $content.Contains($OldValue)) {
        Write-Host "[OK] $Description já estava aplicada."
        return
    }

    $matches = ([regex]::Matches($content, [regex]::Escape($OldValue))).Count
    if ($matches -lt $MinimumMatches) {
        throw "Não foi possível aplicar '$Description'. Padrão esperado não encontrado em $Path. A versão upstream pode ter mudado."
    }

    $content = $content.Replace($OldValue, $NewValue)
    Write-TextFile $Path $content
    Write-Host "[OK] $Description ($matches ocorrência(s))."
}

function Replace-RegexRequired {
    param(
        [string]$Path,
        [string]$Pattern,
        [string]$Replacement,
        [string]$Description,
        [string]$AlreadyAppliedMarker = ""
    )

    $content = Read-TextFile $Path
    if ($AlreadyAppliedMarker -and $content.Contains($AlreadyAppliedMarker)) {
        Write-Host "[OK] $Description já estava aplicada."
        return
    }

    $options = [System.Text.RegularExpressions.RegexOptions]::Multiline -bor [System.Text.RegularExpressions.RegexOptions]::Singleline
    $matches = [regex]::Matches($content, $Pattern, $options)
    if ($matches.Count -ne 1) {
        throw "Não foi possível aplicar '$Description': eram esperadas 1 ocorrência e foram encontradas $($matches.Count) em $Path."
    }

    $content = [regex]::Replace($content, $Pattern, $Replacement, $options)
    Write-TextFile $Path $content
    Write-Host "[OK] $Description."
}

function Insert-BeforeMarkerRequired {
    param(
        [string]$Path,
        [string]$Marker,
        [string]$Insertion,
        [string]$AppliedMarker,
        [string]$Description
    )

    $content = Read-TextFile $Path
    if ($content.Contains($AppliedMarker)) {
        Write-Host "[OK] $Description já estava aplicada."
        return
    }

    $count = ([regex]::Matches($content, [regex]::Escape($Marker))).Count
    if ($count -ne 1) {
        throw "Não foi possível aplicar '$Description': marcador encontrado $count vez(es) em $Path."
    }

    $content = $content.Replace($Marker, $Insertion + $Marker)
    Write-TextFile $Path $content
    Write-Host "[OK] $Description."
}

$Root = [System.IO.Path]::GetFullPath($SourceRoot)
$BrandingRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\branding"))

if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
    throw "Diretório de origem não encontrado: $Root"
}
if ([string]::IsNullOrWhiteSpace($DefaultAccessPassword) -or $DefaultAccessPassword.Length -lt 8) {
    throw "A senha operacional padrão deve possuir pelo menos 8 caracteres."
}
if ($DefaultAccessPassword.IndexOf([char]0) -ge 0 -or $DefaultAccessPassword.Contains("`r") -or $DefaultAccessPassword.Contains("`n")) {
    throw "A senha operacional padrão contém caracteres de controle inválidos."
}

$cargoPath = Resolve-SourceFile "Cargo.toml"
$cargoOriginal = Read-TextFile $cargoPath
if (-not $AllowDifferentUpstreamVersion -and $cargoOriginal -notmatch '(?m)^version\s*=\s*"1\.4\.9"\s*$') {
    throw "Este kit foi validado para RustDesk 1.4.9. Use o tag 1.4.9 ou informe -AllowDifferentUpstreamVersion assumindo o risco."
}

$configPath = Resolve-SourceFile "libs\hbb_common\src\config.rs"
$coreMainPath = Resolve-SourceFile "src\core_main.rs"
$flutterFfiPath = Resolve-SourceFile "src\flutter_ffi.rs"
$windowsPlatformPath = Resolve-SourceFile "src\platform\windows.rs"
$privacyTopmostPath = Resolve-SourceFile "src\privacy_mode\win_topmost_window.rs"
$windowsMainPath = Resolve-SourceFile "flutter\windows\runner\main.cpp"
$runnerRcPath = Resolve-SourceFile "flutter\windows\runner\Runner.rc"
$commonDartPath = Resolve-SourceFile "flutter\lib\common.dart"
$remoteToolbarPath = Resolve-SourceFile "flutter\lib\desktop\widgets\remote_toolbar.dart"
$pubspecPath = Resolve-SourceFile "flutter\pubspec.yaml"
$desktopHomePath = Resolve-SourceFile "flutter\lib\desktop\pages\desktop_home_page.dart"
$desktopSettingsPath = Resolve-SourceFile "flutter\lib\desktop\pages\desktop_setting_page.dart"

# 1. Identidade interna: separa serviço, IPC, executável e configurações do RustDesk original.
Replace-LiteralRequired $configPath `
    'RwLock::new("RustDesk".to_owned())' `
    ("RwLock::new(`"{0}`".to_owned())" -f $InternalName) `
    "Identidade interna isolada"

# 2. Rede Saurus como padrão de fábrica. Continua alterável pela UI/configuração.
$serverEscaped = $RendezvousServer.Replace('\', '\\').Replace('"', '\"')
$keyEscaped = $PublicKey.Replace('\', '\\').Replace('"', '\"')
Replace-RegexRequired $configPath `
    '(?m)^pub const RENDEZVOUS_SERVERS: &\[&str\] = &\[[^\r\n]*\];' `
    ('pub const RENDEZVOUS_SERVERS: &[&str] = &["' + $serverEscaped + '"];') `
    "Servidor rendezvous padrão"
# A constante fica indentada dentro de lazy_static! no hbb_common usado pelo RustDesk 1.4.9.
# Use substituicao literal para preservar o escopo do bloco Rust e evitar falso negativo no patch.
$prodServerOriginal = '    pub static ref PROD_RENDEZVOUS_SERVER: RwLock<String> = RwLock::new("".to_owned());'
$prodServerReplacement = '    pub static ref PROD_RENDEZVOUS_SERVER: RwLock<String> = RwLock::new("' + $serverEscaped + '".to_owned());'
Replace-LiteralRequired $configPath `
    $prodServerOriginal `
    $prodServerReplacement `
    "Servidor de producao padrao"
Replace-RegexRequired $configPath `
    '(?m)^pub const RS_PUB_KEY: &str = "[^"\r\n]*";' `
    ('pub const RS_PUB_KEY: &str = "' + $keyEscaped + '";') `
    "Chave pública padrão"

$passwordRustEscaped = $DefaultAccessPassword.Replace('\', '\\').Replace('"', '\"')
$fixedPasswordConstant = 'pub const SAURUS_REMOTE_DEFAULT_ACCESS_PASSWORD: &str = "' + $passwordRustEscaped + '"; // SAURUS_REMOTE_DEFAULT_ACCESS_PASSWORD'
Insert-BeforeMarkerRequired $configPath `
    'pub const RS_PUB_KEY: &str' `
    ($fixedPasswordConstant + "`r`n") `
    'SAURUS_REMOTE_DEFAULT_ACCESS_PASSWORD' `
    "Senha operacional padrão do Saurus Remote"

$fixedPasswordGuard = @'
    pub fn set_permanent_password(password: &str) -> bool {
        // SAURUS_REMOTE_FIXED_ACCESS_PASSWORD
        // Requisito operacional: todas as instalações Saurus usam a mesma senha.
        if password != SAURUS_REMOTE_DEFAULT_ACCESS_PASSWORD {
            log::warn!("Rejected an attempt to replace the Saurus Remote fixed access password");
            return false;
        }
'@
Replace-RegexRequired $configPath `
    '    pub fn set_permanent_password\(password: &str\) -> bool \{\s*if Self::is_disable_change_permanent_password\(\) \{\s*return false;\s*\}' `
    $fixedPasswordGuard `
    "Bloqueio de alteração da senha operacional padrão" `
    'SAURUS_REMOTE_FIXED_ACCESS_PASSWORD'

# 3. Nome visual na UI Flutter, mantendo o nome interno sem espaços.
$displayNameRust = $DisplayName.Replace('\', '\\').Replace('"', '\"')
$ffiVisualName = @"
pub fn main_get_app_name() -> String {
    "$displayNameRust".to_owned()
}
"@
Replace-RegexRequired $flutterFfiPath `
    'pub fn main_get_app_name\(\) -> String \{\s*get_app_name\(\)\s*\}' `
    $ffiVisualName `
    "Nome visual retornado ao Flutter" `
    $ffiVisualName

$ffiVisualNameSync = @"
pub fn main_get_app_name_sync() -> SyncReturn<String> {
    SyncReturn("$displayNameRust".to_owned())
}
"@
Replace-RegexRequired $flutterFfiPath `
    'pub fn main_get_app_name_sync\(\) -> SyncReturn<String> \{\s*SyncReturn\(get_app_name\(\)\)\s*\}' `
    $ffiVisualNameSync `
    "Nome visual sincrono retornado ao Flutter" `
    $ffiVisualNameSync

$pubspecDescription = 'description: Saurus Remote - acesso remoto corporativo da Saurus Software'
# A tag 1.4.9 possui exatamente esta descricao. A troca literal independe de LF/CRLF
# e evita o falso negativo do regex ancorado com `$` em checkout Windows.
Replace-LiteralRequired $pubspecPath `
    'description: Your Remote Desktop Software' `
    $pubspecDescription `
    "Descricao do aplicativo Flutter"

# Mantém o título visual e o encaminhamento para a instância existente consistentes.
$dispatchPattern = '(&crate::platform::FLUTTER_RUNNER_WIN32_WINDOW_CLASS,\s*)\&crate::get_app_name\(\),'
$dispatchReplacement = '$1' + "// SAURUS_REMOTE_WINDOW_DISPATCH`n            `"$displayNameRust`","
Replace-RegexRequired $coreMainPath `
    $dispatchPattern `
    $dispatchReplacement `
    "Encaminhamento de novas conexões para a janela Saurus" `
    "SAURUS_REMOTE_WINDOW_DISPATCH"

$displayNameCpp = $DisplayName.Replace('\', '\\').Replace('"', '\"')
$cppInsertion = "  // SAURUS_REMOTE_DISPLAY_NAME`r`n  app_name = L`"$displayNameCpp`";`r`n"
Insert-BeforeMarkerRequired $windowsMainPath `
    "  // Uri links dispatch" `
    $cppInsertion `
    "SAURUS_REMOTE_DISPLAY_NAME" `
    "Título das janelas Windows"

# 4. Segurança operacional do motor.
# A senha fixa é gravada diretamente pelo processo do serviço e reaplicada a cada inicialização.
$fixedPasswordEnforcer = @'
use hbb_common::{config, log};

#[cfg(windows)]
fn enforce_saurus_default_access_password() {
    // SAURUS_REMOTE_ENFORCE_DEFAULT_PASSWORD
    config::Config::set_option(
        "verification-method".to_owned(),
        "use-permanent-password".to_owned(),
    );
    if !config::Config::set_permanent_password(config::SAURUS_REMOTE_DEFAULT_ACCESS_PASSWORD) {
        log::error!("Failed to enforce the Saurus Remote default access password");
    } else {
        log::info!("Saurus Remote default access password enforced");
    }
}
'@
Replace-LiteralRequired $coreMainPath `
    'use hbb_common::{config, log};' `
    $fixedPasswordEnforcer `
    "Rotina de aplicação da senha operacional padrão"

$servicePasswordEnforcement = @'
        } else if args[0] == "--service" {
            log::info!("start --service");
            // SAURUS_REMOTE_SERVICE_PASSWORD_ENFORCEMENT
            enforce_saurus_default_access_password();
            crate::start_os_service();
'@
Replace-RegexRequired $coreMainPath `
    '        \} else if args\[0\] == "--service" \{\s*log::info!\("start --service"\);\s*crate::start_os_service\(\);' `
    $servicePasswordEnforcement `
    "Aplicação da senha fixa ao iniciar o serviço" `
    'SAURUS_REMOTE_SERVICE_PASSWORD_ENFORCEMENT'

$serverPasswordEnforcement = @'
        } else if args[0] == "--server" {
            log::info!("start --server with user {}", crate::username());
            #[cfg(windows)]
            {
                // SAURUS_REMOTE_SERVER_PASSWORD_ENFORCEMENT
                enforce_saurus_default_access_password();
            }
'@
Replace-RegexRequired $coreMainPath `
    '        \} else if args\[0\] == "--server" \{\s*log::info!\("start --server with user \{\}", crate::username\(\)\);' `
    $serverPasswordEnforcement `
    "Aplicação da senha fixa ao iniciar o servidor" `
    'SAURUS_REMOTE_SERVER_PASSWORD_ENFORCEMENT'

# O comando por stdin continua disponível para reparo sem expor a senha no CommandLine do Windows.
$passwordStdinReplacement = @'
} else if args[0] == "--password" || args[0] == "--password-stdin" {
            let password = if args[0] == "--password-stdin" {
                // SAURUS_REMOTE_PASSWORD_STDIN
                use std::io::Read;
                let mut value = String::new();
                if let Err(err) = std::io::stdin().read_to_string(&mut value) {
                    println!("Failed to read password from stdin: {err}");
                    return None;
                }
                while value.ends_with('\n') || value.ends_with('\r') {
                    value.pop();
                }
                value
            } else if args.len() == 2 {
                args[1].to_owned()
            } else {
                String::new()
            };
            // SAURUS_REMOTE_FIXED_PASSWORD_CLI
            if password != config::SAURUS_REMOTE_DEFAULT_ACCESS_PASSWORD {
                println!("Only the Saurus Remote operational password is accepted.");
                return None;
            }
            if !password.is_empty() {
                if crate::platform::is_installed() && is_root() {
                    if let Err(err) = crate::ipc::set_permanent_password(password) {
                        println!("{err}");
                    } else {
                        println!("Done!");
                    }
                } else {
                    println!("Installation and administrative privileges required!");
                }
            }
            return None;
        } else if args[0] == "--set-unlock-pin" {
'@
Replace-RegexRequired $coreMainPath `
    '} else if args\[0\] == "--password" \{.*?return None;\s*} else if args\[0\] == "--set-unlock-pin" \{' `
    $passwordStdinReplacement `
    "Canal seguro de senha permanente via stdin" `
    "SAURUS_REMOTE_PASSWORD_STDIN"

$coreMainContent = Read-TextFile $coreMainPath
if (-not $coreMainContent.Contains('Some("--password-stdin")')) {
    Replace-LiteralRequired $coreMainPath `
        'Some("--password")' `
        "Some(`"--password`")`n            | Some(`"--password-stdin`")" `
        "Escopo IPC para --password-stdin"
} else {
    Write-Host "[OK] Escopo IPC para --password-stdin já estava aplicado."
}
$coreMainContent = Read-TextFile $coreMainPath
if (-not $coreMainContent.Contains('            "--password-stdin",')) {
    Replace-LiteralRequired $coreMainPath `
        '            "--password",' `
        "            `"--password`",`n            `"--password-stdin`"," `
        "Teste unitário para --password-stdin"
} else {
    Write-Host "[OK] Teste unitário para --password-stdin já estava aplicado."
}

# O motor não pode substituir o fork Saurus por uma atualização upstream sem validação.
$managedUpdateReplacement = @'
} else if args[0] == "--update" {
                // SAURUS_REMOTE_MANAGED_UPDATE
                println!("Updates are managed by Saurus Remote.");
                return None;
            } else if args[0] == "--after-install" {
'@
Replace-RegexRequired $coreMainPath `
    '} else if args\[0\] == "--update" \{.*?return None;\s*} else if args\[0\] == "--after-install" \{' `
    $managedUpdateReplacement `
    "Atualização upstream direta desabilitada" `
    "SAURUS_REMOTE_MANAGED_UPDATE"

# 5. Metadados do executável.
Replace-LiteralRequired $cargoPath 'authors = ["rustdesk <info@rustdesk.com>"]' 'authors = ["RustDesk contributors <info@rustdesk.com>", "Saurus Software"]' "Autores preservando atribuição upstream"
Replace-LiteralRequired $cargoPath 'description = "RustDesk Remote Desktop"' 'description = "Saurus Remote - acesso remoto corporativo"' "Descrição do pacote"
Replace-LiteralRequired $cargoPath 'LegalCopyright = "Copyright © 2026 Purslane Tech Pte. Ltd. All rights reserved."' 'LegalCopyright = "Copyright © 2026 RustDesk contributors e Saurus Software. Consulte os avisos de licença."' "Copyright do binário"
Replace-LiteralRequired $cargoPath 'ProductName = "RustDesk"' 'ProductName = "Saurus Remote"' "ProductName WinRes"
Replace-LiteralRequired $cargoPath 'FileDescription = "RustDesk Remote Desktop"' 'FileDescription = "Saurus Remote - acesso remoto corporativo"' "FileDescription WinRes"
Replace-LiteralRequired $cargoPath 'OriginalFilename = "rustdesk.exe"' ("OriginalFilename = `"{0}.exe`"" -f $InternalName) "OriginalFilename WinRes"
Replace-LiteralRequired $cargoPath 'name = "RustDesk"' 'name = "Saurus Remote"' "Nome de bundle"
Replace-LiteralRequired $cargoPath 'identifier = "com.carriez.rustdesk"' 'identifier = "br.com.saurus.remote"' "Identificador de bundle"

Replace-LiteralRequired $runnerRcPath 'VALUE "CompanyName", "Purslane Tech Pte. Ltd." "\0"' 'VALUE "CompanyName", "Saurus Software" "\0"' "CompanyName do runner"
Replace-LiteralRequired $runnerRcPath 'VALUE "FileDescription", "RustDesk Remote Desktop" "\0"' 'VALUE "FileDescription", "Saurus Remote - acesso remoto corporativo" "\0"' "Descrição do runner"
Replace-LiteralRequired $runnerRcPath 'VALUE "InternalName", "rustdesk" "\0"' ("VALUE `"InternalName`", `"{0}`" `"\0`"" -f $InternalName) "InternalName do runner"
Replace-LiteralRequired $runnerRcPath 'VALUE "LegalCopyright", "Copyright © 2026 Purslane Tech Pte. Ltd. All rights reserved." "\0"' 'VALUE "LegalCopyright", "Copyright © 2026 Saurus Software; componentes RustDesk conforme AGPL-3.0." "\0"' "Copyright do runner"
Replace-LiteralRequired $runnerRcPath 'VALUE "OriginalFilename", "rustdesk.exe" "\0"' ("VALUE `"OriginalFilename`", `"{0}.exe`" `"\0`"" -f $InternalName) "Nome original do runner"
Replace-LiteralRequired $runnerRcPath 'VALUE "ProductName", "RustDesk" "\0"' 'VALUE "ProductName", "Saurus Remote" "\0"' "ProductName do runner"

# 6. Instalação e serviço próprios. Nada aponta para C:\Program Files\RustDesk ou serviço RustDesk.
$installRustLiteral = 'format!("{}\\{}", pf, crate::get_app_name())'
$installReplacement = 'format!("{}\\' + $InstallSubdirectory.Replace('\', '\\') + '", pf)'
Replace-LiteralRequired $windowsPlatformPath $installRustLiteral $installReplacement "Diretório de instalação Saurus"
Replace-LiteralRequired $windowsPlatformPath 'DisplayName= \"{app_name} Service\"' 'DisplayName= \"Saurus Remote Service\"' "Nome visual do serviço" 2

# O RustDesk 1.4.9 ainda consulta primeiro uma chave Inno Setup fixa. Sem esta troca,
# a instalação Saurus pode herdar o InstallLocation do RustDesk original.
$legacyInstallerRegistryKey = '{54E86BC2-6C85-41F3-A9EB-1A94AC9B1F93}_is1'
Replace-LiteralRequired $windowsPlatformPath `
    ('const IS1: &str = "' + $legacyInstallerRegistryKey + '";') `
    ('const IS1: &str = "' + $InstallerRegistryKey + '"; // SAURUS_REMOTE_INSTALLER_REGISTRY') `
    "Chave de desinstalação Inno Setup isolada"

# Isola a área pública usada por clientes customizados e impede que o motor Saurus
# leia ou grave o staging pertencente ao RustDesk original.
$stagingReplacement = @'
get_public_base_dir()
        // SAURUS_REMOTE_CUSTOM_CLIENT_STAGING
        .join("SaurusRemote")
        .join("SaurusRemoteCustomClientStaging")
'@
Replace-RegexRequired $windowsPlatformPath `
    'get_public_base_dir\(\)\s*\.join\("RustDesk"\)\s*\.join\("RustDeskCustomClientStaging"\)' `
    $stagingReplacement `
    "Diretório de staging customizado isolado" `
    "SAURUS_REMOTE_CUSTOM_CLIENT_STAGING"

# A limpeza de atualizações temporárias deve alcançar somente arquivos do próprio produto.
$tempUpdateReplacement = @'
// SAURUS_REMOTE_TEMP_UPDATE_PREFIX
                if file_name.starts_with(&format!("{}-", crate::get_app_name().to_lowercase()))
'@
Replace-LiteralRequired $windowsPlatformPath `
    'if file_name.starts_with("rustdesk-")' `
    $tempUpdateReplacement.TrimEnd("`r", "`n") `
    "Prefixo de limpeza de atualizações temporárias isolado"
Replace-LiteralRequired $windowsPlatformPath `
    '// Match files like rustdesk-*.msi or rustdesk-*.exe' `
    '// Match only temporary update files owned by this custom client.' `
    "Comentário da limpeza de atualização"

$nativeCaptionReplacement = "// SAURUS_REMOTE_OUTPUT_CAPTION`r`n    let caption = `"$DisplayName`""
Replace-LiteralRequired $windowsPlatformPath `
    'let caption = "RustDesk Output"' `
    $nativeCaptionReplacement `
    "Título das mensagens nativas"

# O modo privacidade usa um RuntimeBroker copiado e nomes de janela globais. Estes nomes
# também precisam ser exclusivos para que duas instalações possam coexistir.
$brokerExe = "RuntimeBroker_{0}.exe" -f $InternalName.ToLowerInvariant()
Replace-LiteralRequired $privacyTopmostPath `
    '"RuntimeBroker_rustdesk.exe"' `
    ('"' + $brokerExe + '"') `
    "Processo auxiliar do modo privacidade isolado"
Replace-LiteralRequired $privacyTopmostPath `
    '"RustDeskPrivacyWindowClass"' `
    '"SaurusRemotePrivacyWindowClass"' `
    "Classe da janela de privacidade isolada"
Replace-LiteralRequired $privacyTopmostPath `
    '"RustDeskPrivacyWindow"' `
    '"SaurusRemotePrivacyWindow"' `
    "Nome da janela de privacidade isolado"

# 7. Tema visual claro baseado no design system da Saurus.
$themeReplacements = @(
    @('static const Color accent = Color(0xFF0071FF);', 'static const Color accent = Color(0xFFD5B63A);'),
    @('static const Color accent50 = Color(0x770071FF);', 'static const Color accent50 = Color(0x77D5B63A);'),
    @('static const Color accent80 = Color(0xAA0071FF);', 'static const Color accent80 = Color(0xAAD5B63A);'),
    @('static const Color canvasColor = Color(0xFF212121);', 'static const Color canvasColor = Color(0xFFF5F6F8);'),
    @('static const Color idColor = Color(0xFF00B6F0);', 'static const Color idColor = Color(0xFF111C35);'),
    @('static const Color button = Color(0xFF2C8CFF);', 'static const Color button = Color(0xFF111C35);'),
    @('Color(0xFF18191E)', 'Color(0xFFF5F6F8)'),
    @('Color(0xFF24252B)', 'Color(0xFFFFFFFF)'),
    @('Color.fromARGB(255, 45, 46, 53)', 'Color.fromARGB(255, 245, 246, 248)')
)
foreach ($pair in $themeReplacements) {
    Replace-LiteralRequired $commonDartPath $pair[0] $pair[1] ("Tema claro Saurus: {0}" -f $pair[0])
}

$lightThemePreference = @'
  static ThemeMode getThemeModePreference() {
    // SAURUS_REMOTE_FIXED_LIGHT_THEME
    return ThemeMode.light;
  }
'@
Replace-RegexRequired $commonDartPath `
    '  static ThemeMode getThemeModePreference\(\) \{\s*return themeModeFromString\(bind\.mainGetLocalOption\(key: kCommConfKeyTheme\)\);\s*\}' `
    $lightThemePreference `
    "Tema claro fixo" `
    "SAURUS_REMOTE_FIXED_LIGHT_THEME"

# Remove a escolha de tema e a área de conta/login das configurações.
Replace-LiteralRequired $desktopSettingsPath `
    '        theme(),' `
    '        // SAURUS_REMOTE_LIGHT_THEME_ONLY: tema definido pela identidade visual corporativa.' `
    "Seletor de tema removido"
Replace-LiteralRequired $desktopSettingsPath `
    '    if (!bind.isDisableAccount()) SettingsTabKey.account,' `
    '    // SAURUS_REMOTE_NO_ACCOUNT: login e conta ocultos nesta fase.' `
    "Aba de conta removida"

$accountDependentOptionPattern = '    if \(!bind\.isDisableAccount\(\)\) \{\s*children\.add\(_OptionCheckBox\(\s*context,\s*''note-at-conn-end-tip'',\s*kOptionAllowAskForNoteAtEndOfConnection,\s*isServer: false,\s*optSetter: \(key, value\) async \{\s*if \(value && !gFFI\.userModel\.isLogin\) \{\s*final res = await loginDialog\(\);\s*if \(res != true\) return;\s*\}\s*await mainSetLocalBoolOption\(key, value\);\s*\},\s*\)\);\s*\}'
Replace-RegexRequired $desktopSettingsPath `
    $accountDependentOptionPattern `
    '    // SAURUS_REMOTE_NO_LOGIN_DEPENDENT_OPTIONS' `
    "Opções dependentes de login removidas" `
    "SAURUS_REMOTE_NO_LOGIN_DEPENDENT_OPTIONS"

# 8. Tela principal Saurus: sem perfil, login, logout ou mapa.
$saurusHomeBuild = @'
  @override
  Widget build(BuildContext context) {
    super.build(context);
    return _buildBlock(child: _buildSaurusShell(context));
  }
'@
Replace-RegexRequired $desktopHomePath `
    '  @override\s+Widget build\(BuildContext context\) \{\s+super\.build\(context\);\s+final isIncomingOnly = bind\.isIncomingOnly\(\);\s+return _buildBlock\(\s*child: Row\(.*?\)\);\s+\}' `
    $saurusHomeBuild `
    "Dashboard principal Saurus" `
    "_buildSaurusShell(context)"

$saurusHomeWidgets = @'
  static const Color _saurusNavy = Color(0xFF111C35);
  static const Color _saurusGold = Color(0xFFD5B63A);
  static const Color _saurusPage = Color(0xFFF5F6F8);
  static const Color _saurusCard = Color(0xFFFFFFFF);
  static const Color _saurusBorder = Color(0xFFE1E4E8);
  static const Color _saurusText = Color(0xFF172033);
  static const Color _saurusMuted = Color(0xFF6B7280);
  static const Color _saurusSuccess = Color(0xFF2FBF64);

  Widget _buildSaurusShell(BuildContext context) {
    return Container(
      color: _saurusPage,
      child: Row(
        children: [
          _buildSaurusSidebar(context),
          Expanded(
            child: Column(
              children: [
                _buildSaurusHeader(context),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.all(18),
                    child: LayoutBuilder(
                      builder: (context, constraints) {
                        final compact = constraints.maxWidth < 900;
                        final deviceColumn = Column(
                          children: [
                            _buildSaurusDeviceCard(context),
                            const SizedBox(height: 14),
                            _buildSaurusDiagnosticsCard(context),
                          ],
                        );
                        final connections = _buildSaurusConnectionsCard(context);
                        if (compact) {
                          return ListView(
                            children: [
                              deviceColumn,
                              const SizedBox(height: 14),
                              SizedBox(height: 520, child: connections),
                            ],
                          );
                        }
                        return Row(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            SizedBox(
                              width: 340,
                              child: SingleChildScrollView(child: deviceColumn),
                            ),
                            const SizedBox(width: 14),
                            Expanded(child: connections),
                          ],
                        );
                      },
                    ),
                  ),
                ),
                _buildSaurusFooter(context),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSaurusSidebar(BuildContext context) {
    return Container(
      width: 210,
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(right: BorderSide(color: _saurusBorder)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 24, 16, 24),
            child: Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF9DF),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: _saurusGold.withOpacity(0.45)),
                  ),
                  child: Image.asset(
                    'assets/saurus_remote_logo.png',
                    fit: BoxFit.contain,
                  ),
                ),
                const SizedBox(width: 10),
                const Expanded(
                  child: Text(
                    'Saurus Remote',
                    style: TextStyle(
                      color: _saurusNavy,
                      fontWeight: FontWeight.w700,
                      fontSize: 17,
                    ),
                  ),
                ),
              ],
            ),
          ),
          _buildSaurusNavItem(
            icon: Icons.dashboard_outlined,
            label: 'Dashboard',
            selected: true,
            onTap: () {},
          ),
          _buildSaurusNavItem(
            icon: Icons.monitor_heart_outlined,
            label: 'Diagnóstico',
            onTap: () => DesktopSettingPage.switch2page(SettingsTabKey.network),
          ),
          _buildSaurusNavItem(
            icon: Icons.settings_outlined,
            label: 'Configurações',
            onTap: DesktopTabPage.onAddSetting,
          ),
          const Spacer(),
          const Padding(
            padding: EdgeInsets.fromLTRB(20, 12, 20, 20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Motor RustDesk 1.4.9',
                  style: TextStyle(color: _saurusMuted, fontSize: 11),
                ),
                SizedBox(height: 5),
                Row(
                  children: [
                    Icon(Icons.circle, color: _saurusSuccess, size: 8),
                    SizedBox(width: 6),
                    Text(
                      'Saurus build',
                      style: TextStyle(color: _saurusMuted, fontSize: 11),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSaurusNavItem({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
    bool selected = false,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
      child: Material(
        color: selected ? _saurusNavy : Colors.transparent,
        borderRadius: BorderRadius.circular(7),
        child: InkWell(
          borderRadius: BorderRadius.circular(7),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
            child: Row(
              children: [
                Icon(icon,
                    color: selected ? _saurusGold : _saurusMuted, size: 21),
                const SizedBox(width: 12),
                Text(
                  label,
                  style: TextStyle(
                    color: selected ? _saurusGold : _saurusText,
                    fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSaurusHeader(BuildContext context) {
    return Container(
      height: 72,
      padding: const EdgeInsets.symmetric(horizontal: 24),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: _saurusBorder)),
      ),
      child: Row(
        children: [
          const Expanded(
            child: Text(
              'Saurus Remote',
              style: TextStyle(
                color: _saurusText,
                fontSize: 24,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          Obx(
            () => Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
              decoration: BoxDecoration(
                color: svcStopped.value
                    ? const Color(0xFFFFF1F1)
                    : const Color(0xFFF0FBF4),
                borderRadius: BorderRadius.circular(18),
              ),
              child: Row(
                children: [
                  Icon(Icons.circle,
                      size: 8,
                      color: svcStopped.value
                          ? const Color(0xFFE25555)
                          : _saurusSuccess),
                  const SizedBox(width: 7),
                  Text(
                    svcStopped.value
                        ? 'Serviço interrompido'
                        : 'Serviço em execução',
                    style: const TextStyle(
                      color: _saurusText,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 10),
          IconButton(
            tooltip: translate('Settings'),
            onPressed: DesktopTabPage.onAddSetting,
            icon: const Icon(Icons.settings_outlined, color: _saurusNavy),
          ),
        ],
      ),
    );
  }

  Widget _buildSaurusDeviceCard(BuildContext context) {
    return ChangeNotifierProvider.value(
      value: gFFI.serverModel,
      child: Consumer<ServerModel>(
        builder: (context, model, child) {
          final rawId = model.serverId.text.trim();
          final connected = rawId.isNotEmpty && rawId != '-';
          return _buildSaurusCard(
            title: 'Este dispositivo',
            icon: Icons.desktop_windows_outlined,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _buildSaurusValueRow(
                  label: 'ID do dispositivo',
                  value: _formatSaurusId(rawId),
                  buttonLabel: 'Copiar ID',
                  onCopy: connected ? rawId : '',
                ),
                const Divider(height: 26),
                _buildSaurusValueRow(
                  label: 'Senha permanente',
                  value: 'ophd0202',
                  buttonLabel: 'Copiar senha',
                  onCopy: 'ophd0202',
                ),
                const Divider(height: 26),
                _buildSaurusStatusLine(
                  'Status do serviço',
                  svcStopped.value ? 'Interrompido' : 'Online',
                  !svcStopped.value,
                ),
                const SizedBox(height: 9),
                _buildSaurusStatusLine(
                  'Status do servidor',
                  connected ? 'Conectado' : 'Aguardando ID',
                  connected,
                ),
                const SizedBox(height: 9),
                _buildSaurusStatusLine(
                  'Servidor',
                  '20.195.216.23:443',
                  true,
                ),
                const SizedBox(height: 18),
                OutlinedButton.icon(
                  onPressed: () => DesktopSettingPage.switch2page(
                    SettingsTabKey.network,
                  ),
                  icon: const Icon(Icons.tune, size: 18),
                  label: const Text('Configurações de rede'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: _saurusNavy,
                    side: const BorderSide(color: _saurusBorder),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildSaurusValueRow({
    required String label,
    required String value,
    required String buttonLabel,
    required String onCopy,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: const TextStyle(color: _saurusMuted, fontSize: 12)),
        const SizedBox(height: 6),
        Row(
          children: [
            Expanded(
              child: SelectableText(
                value.isEmpty ? 'Carregando...' : value,
                style: const TextStyle(
                  color: _saurusText,
                  fontSize: 23,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.5,
                ),
              ),
            ),
            TextButton.icon(
              onPressed: onCopy.isEmpty
                  ? null
                  : () {
                      Clipboard.setData(ClipboardData(text: onCopy));
                      showToast(translate('Copied'));
                    },
              icon: const Icon(Icons.copy_outlined, size: 16),
              label: Text(buttonLabel),
              style: TextButton.styleFrom(foregroundColor: _saurusNavy),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildSaurusStatusLine(String label, String value, bool success) {
    return Row(
      children: [
        Expanded(
          child: Text(label,
              style: const TextStyle(color: _saurusMuted, fontSize: 12)),
        ),
        Icon(Icons.circle,
            size: 8,
            color: success ? _saurusSuccess : const Color(0xFFE2A33A)),
        const SizedBox(width: 6),
        Flexible(
          child: Text(
            value,
            textAlign: TextAlign.right,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: _saurusText,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSaurusDiagnosticsCard(BuildContext context) {
    return SizedBox(
      height: 250,
      child: _buildSaurusCard(
        title: 'Diagnóstico rápido',
        icon: Icons.monitor_heart_outlined,
        expandChild: true,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            OnlineStatusWidget(
              onSvcStatusChanged: () {
                if (mounted) setState(() {});
              },
            ),
            const Spacer(),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFF7F9FC),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: _saurusBorder),
              ),
              child: const Row(
                children: [
                  Icon(Icons.verified_user_outlined,
                      color: _saurusSuccess, size: 20),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Conexões protegidas por criptografia de ponta a ponta.',
                      style: TextStyle(
                        color: _saurusMuted,
                        fontSize: 12,
                        height: 1.3,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSaurusConnectionsCard(BuildContext context) {
    return _buildSaurusCard(
      title: 'Conectar e acessar sessões recentes',
      icon: Icons.link_outlined,
      padding: EdgeInsets.zero,
      expandChild: true,
      child: ClipRRect(
        borderRadius: const BorderRadius.only(
          bottomLeft: Radius.circular(10),
          bottomRight: Radius.circular(10),
        ),
        child: Container(
          color: Colors.white,
          child: ConnectionPage(),
        ),
      ),
    );
  }

  Widget _buildSaurusCard({
    required String title,
    required IconData icon,
    required Widget child,
    EdgeInsets padding = const EdgeInsets.fromLTRB(18, 16, 18, 18),
    bool expandChild = false,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: _saurusCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: _saurusBorder),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0B000000),
            blurRadius: 10,
            offset: Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 16, 18, 13),
            child: Row(
              children: [
                Container(
                  width: 34,
                  height: 34,
                  decoration: BoxDecoration(
                    color: const Color(0xFFF1F3F6),
                    borderRadius: BorderRadius.circular(17),
                  ),
                  child: Icon(icon, color: _saurusNavy, size: 19),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(
                      color: _saurusText,
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          if (expandChild)
            Expanded(child: Padding(padding: padding, child: child))
          else
            Padding(padding: padding, child: child),
        ],
      ),
    );
  }

  Widget _buildSaurusFooter(BuildContext context) {
    return Container(
      height: 34,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: _saurusBorder)),
      ),
      child: const Row(
        children: [
          Text('Saurus Remote',
              style: TextStyle(color: _saurusMuted, fontSize: 11)),
          Spacer(),
          Icon(Icons.shield_outlined, color: _saurusSuccess, size: 15),
          SizedBox(width: 6),
          Text('Conexão segura',
              style: TextStyle(color: _saurusMuted, fontSize: 11)),
        ],
      ),
    );
  }

  String _formatSaurusId(String raw) {
    final digits = raw.replaceAll(RegExp(r'\D'), '');
    if (digits.length < 7) return raw;
    final chunks = <String>[];
    for (var i = 0; i < digits.length; i += 3) {
      final end = (i + 3 < digits.length) ? i + 3 : digits.length;
      chunks.add(digits.substring(i, end));
    }
    return chunks.join(' ');
  }

'@
Insert-BeforeMarkerRequired $desktopHomePath `
    '  Widget _buildBlock({required Widget child}) {' `
    $saurusHomeWidgets `
    'Widget _buildSaurusShell(BuildContext context)' `
    "Componentes do dashboard claro Saurus"

# 8. Marca Saurus visivel na barra da sessao remota.
$toolbarPattern = '(?m)^(\s*final List<Widget> toolbarItems = \[\];\r?\n)(\s*toolbarItems\.add\(_PinMenu\(state: widget\.state\)\);)'
$toolbarReplacement = '$1    toolbarItems.add(const _SaurusBrand());' + "`r`n" + '$2'
Replace-RegexRequired $remoteToolbarPath `
    $toolbarPattern `
    $toolbarReplacement `
    "Marca Saurus na barra da sessao remota" `
    'toolbarItems.add(const _SaurusBrand());'

$brandWidget = @'
class _SaurusBrand extends StatelessWidget {
  const _SaurusBrand();

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: 'Saurus Remote',
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 3),
        child: Container(
          width: 28,
          height: 28,
          decoration: BoxDecoration(
            color: const Color(0xFFFFFFFF),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: const Color(0xFFD5B63A), width: 1),
          ),
          padding: const EdgeInsets.all(3),
          child: Image.asset(
            'assets/saurus_remote_logo.png',
            fit: BoxFit.contain,
            filterQuality: FilterQuality.high,
          ),
        ),
      ),
    );
  }
}

'@
Insert-BeforeMarkerRequired $remoteToolbarPath `
    'class _PinMenu extends StatelessWidget {' `
    $brandWidget `
    'class _SaurusBrand extends StatelessWidget' `
    "Widget de marca da sessao remota"

# 9. Icones e logos. Os arquivos foram derivados dos recursos fornecidos pelo projeto Saurus.
$assetMap = @{
    "app_icon.ico" = @(
        "flutter\windows\runner\resources\app_icon.ico",
        "res\icon.ico"
    )
    "app_icon.png" = @(
        "res\icon.png"
    )
    "32x32.png" = @("res\32x32.png")
    "64x64.png" = @("res\64x64.png")
    "128x128.png" = @("res\128x128.png")
    "128x128@2x.png" = @("res\128x128@2x.png")
    "icon.svg" = @(
        "flutter\assets\icon.svg",
        "res\scalable.svg"
    )
    "logo_transparent.png" = @(
        "flutter\assets\saurus_remote_logo.png"
    )
}
foreach ($sourceName in $assetMap.Keys) {
    $sourcePath = Join-Path $BrandingRoot $sourceName
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "Recurso de marca ausente: $sourcePath"
    }
    foreach ($relativeTarget in $assetMap[$sourceName]) {
        $targetPath = Join-Path $Root $relativeTarget
        $targetDirectory = Split-Path -Parent $targetPath
        New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null
        Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
        Write-Host "[OK] Recurso copiado: $relativeTarget"
    }
}

# 10. Manifesto de customização auditável. A senha fixa é um requisito operacional explícito.
$manifest = [ordered]@{
    schemaVersion = 1
    appliedAtUtc = [DateTime]::UtcNow.ToString("o")
    upstream = [ordered]@{
        repository = "https://github.com/rustdesk/rustdesk"
        tag = "1.4.9"
    }
    product = [ordered]@{
        internalName = $InternalName
        displayName = $DisplayName
        serviceName = $InternalName
        serviceDisplayName = "Saurus Remote Service"
        installPath = "%ProgramFiles%\$InstallSubdirectory"
        executable = "$InternalName.exe"
        uriScheme = $InternalName.ToLowerInvariant()
        installerRegistryKey = $InstallerRegistryKey
        privacyBrokerExecutable = $brokerExe
        privacyWindowClass = "SaurusRemotePrivacyWindowClass"
        customClientStaging = "%ProgramData%\SaurusRemote\SaurusRemoteCustomClientStaging"
    }
    network = [ordered]@{
        rendezvousServer = $RendezvousServer
        publicKey = $PublicKey
        settingsLocked = $false
    }
    security = [ordered]@{
        permanentPasswordEmbedded = $true
        fixedPasswordPolicy = $true
        passwordProvisioning = "engine-enforced on service/server startup; stdin repair supported"
        upstreamSelfUpdateEnabled = $false
        updaterOwner = "Saurus Remote launcher/updater"
    }
    theme = [ordered]@{
        background = "#F5F6F8"
        accent = "#D5B63A"
        card = "#FFFFFF"
    }
}
$manifestPath = Join-Path $Root "SAURUS_CUSTOMIZATION.json"
Write-TextFile $manifestPath ($manifest | ConvertTo-Json -Depth 8)
Write-Host "[OK] Manifesto gerado: $manifestPath"

Write-Host ""
Write-Host "Customização Saurus aplicada com sucesso." -ForegroundColor Green
Write-Host "Execute Verify-SaurusCustomization.ps1 antes do build." -ForegroundColor Yellow
