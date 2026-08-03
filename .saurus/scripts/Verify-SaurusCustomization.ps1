[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,
    [string]$InternalName = "SaurusRemote",
    [string]$DisplayName = "Saurus Remote",
    [string]$RendezvousServer = "20.195.216.23:443",
    [string]$PublicKey = "OJ7QiUrqNu0wM13vDSp4nmAlDu6hy3n8hTI5Wksl2Tc=",
    [string]$InstallerRegistryKey = "{1117CE17-506B-4122-A421-69233FCA9C12}_is1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = [System.IO.Path]::GetFullPath($SourceRoot)
$failures = New-Object System.Collections.Generic.List[string]

function Check-FileContains {
    param([string]$RelativePath, [string]$Expected, [string]$Description)
    $path = Join-Path $Root $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $failures.Add("Arquivo ausente: $RelativePath")
        return
    }
    $content = [System.IO.File]::ReadAllText($path)
    if (-not $content.Contains($Expected)) {
        $failures.Add("$Description nao encontrada em $RelativePath")
    } else {
        Write-Host "[OK] $Description"
    }
}

function Check-FileNotContains {
    param([string]$RelativePath, [string]$Forbidden, [string]$Description)
    $path = Join-Path $Root $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $failures.Add("Arquivo ausente: $RelativePath")
        return
    }
    $content = [System.IO.File]::ReadAllText($path)
    if ($content.Contains($Forbidden)) {
        $failures.Add("$Description ainda existe em $RelativePath")
    } else {
        Write-Host "[OK] $Description removida"
    }
}

function Check-JsonPropertyValue {
    param(
        [string]$RelativePath,
        [string[]]$PropertyPath,
        [object]$Expected,
        [string]$Description
    )

    $path = Join-Path $Root $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $failures.Add("Arquivo ausente: $RelativePath")
        return
    }

    try {
        $value = [System.IO.File]::ReadAllText($path) | ConvertFrom-Json
        foreach ($propertyName in $PropertyPath) {
            $property = $value.PSObject.Properties[$propertyName]
            if ($null -eq $property) {
                throw "Propriedade ausente: $($PropertyPath -join '.')"
            }
            $value = $property.Value
        }
        if ($value -ne $Expected) {
            throw "Valor inesperado para $($PropertyPath -join '.')"
        }
        Write-Host "[OK] $Description"
    }
    catch {
        $failures.Add("$Description nao encontrada em $RelativePath")
    }
}

Check-FileContains "Cargo.toml" 'version = "1.4.9"' "Versao upstream 1.4.9"
Check-FileContains "libs\hbb_common\src\config.rs" ("RwLock::new(`"{0}`".to_owned())" -f $InternalName) "Identidade interna Saurus"
Check-FileContains "libs\hbb_common\src\config.rs" ('pub const RENDEZVOUS_SERVERS: &[&str] = &["' + $RendezvousServer + '"];') "Servidor Saurus padrao"
Check-FileContains "libs\hbb_common\src\config.rs" ('pub static ref PROD_RENDEZVOUS_SERVER: RwLock<String> = RwLock::new("' + $RendezvousServer + '".to_owned());') "Servidor Saurus de producao"
Check-FileContains "libs\hbb_common\src\config.rs" ('pub const RS_PUB_KEY: &str = "' + $PublicKey + '";') "Chave publica Saurus"
Check-FileNotContains "libs\hbb_common\src\config.rs" 'RwLock::new("RustDesk".to_owned())' "Identidade interna RustDesk"
Check-FileContains "src\flutter_ffi.rs" ("SyncReturn(`"{0}`".to_owned())" -f $DisplayName) "Nome visual Flutter"
Check-FileContains "src\core_main.rs" "SAURUS_REMOTE_WINDOW_DISPATCH" "Encaminhamento de janela com nome visual"
Check-FileContains "libs\hbb_common\src\config.rs" 'pub const SAURUS_REMOTE_DEFAULT_ACCESS_PASSWORD: &str = "ophd0202";' "Senha operacional padrão"
Check-FileContains "libs\hbb_common\src\config.rs" "SAURUS_REMOTE_FIXED_ACCESS_PASSWORD" "Bloqueio de alteração da senha padrão"
Check-FileContains "libs\hbb_common\src\config.rs" "SAURUS_REMOTE_DEFAULT_ADAPTIVE_VIEW" "Escala adaptável padrão no núcleo"
Check-FileContains "libs\hbb_common\src\config.rs" "SAURUS_REMOTE_DEFAULT_DISABLE_AUDIO" "Som remoto desativado por padrão no núcleo"
Check-FileContains "src\core_main.rs" "SAURUS_REMOTE_ENFORCE_DEFAULT_PASSWORD" "Aplicação automática da senha padrão"
Check-FileContains "src\core_main.rs" "SAURUS_REMOTE_SERVICE_PASSWORD_ENFORCEMENT" "Aplicação da senha no serviço"
Check-FileContains "src\core_main.rs" "SAURUS_REMOTE_SERVER_PASSWORD_ENFORCEMENT" "Aplicação da senha no servidor"
Check-FileContains "src\core_main.rs" "SAURUS_REMOTE_NORMAL_START_PASSWORD_ENFORCEMENT" "Aplicação da senha no início normal e portátil"
Check-FileContains "src\core_main.rs" "SAURUS_REMOTE_PASSWORD_STDIN" "Senha segura via stdin"
Check-FileContains "src\core_main.rs" "SAURUS_REMOTE_FIXED_PASSWORD_CLI" "CLI restrita à senha operacional padrão"
Check-FileContains "src\core_main.rs" 'Some("--password-stdin")' "Escopo IPC de senha via stdin"
Check-FileContains "src\core_main.rs" "SAURUS_REMOTE_MANAGED_UPDATE" "Atualizacao controlada pela Saurus"
Check-FileContains "flutter\windows\runner\main.cpp" "SAURUS_REMOTE_DISPLAY_NAME" "Nome visual Windows"
Check-FileContains "src\platform\windows.rs" 'DisplayName= \"Saurus Remote Service\"' "Nome visual do servico"
Check-FileContains "src\platform\windows.rs" 'Saurus Software\\Saurus Remote' "Diretorio de instalacao isolado"
Check-FileContains "src\platform\windows.rs" ('const IS1: &str = "' + $InstallerRegistryKey + '"; // SAURUS_REMOTE_INSTALLER_REGISTRY') "Chave de desinstalacao isolada"
Check-FileNotContains "src\platform\windows.rs" '{54E86BC2-6C85-41F3-A9EB-1A94AC9B1F93}_is1' "Chave Inno Setup do RustDesk"
Check-FileContains "src\platform\windows.rs" 'SAURUS_REMOTE_CUSTOM_CLIENT_STAGING' "Staging de cliente customizado isolado"
Check-FileContains "src\platform\windows.rs" '.join("SaurusRemoteCustomClientStaging")' "Pasta de staging Saurus"
Check-FileNotContains "src\platform\windows.rs" '.join("RustDeskCustomClientStaging")' "Staging do RustDesk"
Check-FileContains "src\platform\windows.rs" 'SAURUS_REMOTE_TEMP_UPDATE_PREFIX' "Prefixo de atualizacao temporaria isolado"
Check-FileContains "src\platform\windows.rs" 'file_name.starts_with(&format!("{}-", crate::get_app_name().to_lowercase()))' "Limpeza de temporarios por nome interno"
Check-FileNotContains "src\platform\windows.rs" 'file_name.starts_with("rustdesk-")' "Limpeza de temporarios RustDesk"
Check-FileContains "src\platform\windows.rs" 'SAURUS_REMOTE_OUTPUT_CAPTION' "Titulo de dialogos nativos Saurus"
Check-FileContains "src\privacy_mode\win_topmost_window.rs" '"RuntimeBroker_saurusremote.exe"' "Broker de privacidade isolado"
Check-FileContains "src\privacy_mode\win_topmost_window.rs" '"SaurusRemotePrivacyWindowClass"' "Classe de privacidade isolada"
Check-FileContains "src\privacy_mode\win_topmost_window.rs" '"SaurusRemotePrivacyWindow"' "Janela de privacidade isolada"
Check-FileNotContains "src\privacy_mode\win_topmost_window.rs" '"RuntimeBroker_rustdesk.exe"' "Broker de privacidade RustDesk"
Check-FileNotContains "src\privacy_mode\win_topmost_window.rs" '"RustDeskPrivacyWindow"' "Janela de privacidade RustDesk"
Check-FileContains "flutter\windows\runner\Runner.rc" 'VALUE "ProductName", "Saurus Remote"' "Metadados do executavel"
Check-FileContains "flutter\pubspec.yaml" 'description: Saurus Remote - acesso remoto corporativo da Saurus Software' "Descricao Flutter Saurus"
Check-FileContains "flutter\lib\common.dart" 'static const Color accent = Color(0xFFD5B63A);' "Cor dourada Saurus"
Check-FileContains "flutter\lib\common.dart" 'static const Color canvasColor = Color(0xFFF5F6F8);' "Fundo claro Saurus"
Check-FileContains "flutter\lib\common.dart" 'SAURUS_REMOTE_FIXED_LIGHT_THEME' "Tema claro fixo"
Check-FileContains "flutter\lib\desktop\pages\desktop_home_page.dart" 'Widget _buildSaurusShell(BuildContext context)' "Dashboard claro Saurus"
Check-FileContains "flutter\lib\desktop\pages\desktop_home_page.dart" "SAURUS_REMOTE_PRODUCTION_UI_FINAL" "Marcador da UI final de producao"
Check-FileContains "flutter\lib\desktop\pages\desktop_home_page.dart" "Este dispositivo" "Painel deste dispositivo"
Check-FileContains "flutter\lib\desktop\pages\desktop_home_page.dart" "Conectar" "Painel de conexao"
Check-FileNotContains "flutter\lib\desktop\pages\desktop_home_page.dart" "Conectar e acessar sessoes recentes" "Painel antigo de conexoes"
Check-FileContains "flutter\lib\desktop\pages\desktop_setting_page.dart" 'SAURUS_REMOTE_NO_ACCOUNT' "Login e conta ocultos"
Check-FileContains "flutter\lib\desktop\pages\desktop_setting_page.dart" 'SAURUS_REMOTE_NO_LOGIN_DEPENDENT_OPTIONS' "Opções dependentes de login removidas"
Check-FileContains "flutter\lib\desktop\widgets\remote_toolbar.dart" 'toolbarItems.add(const _SaurusBrand());' "Marca Saurus na barra remota"
Check-FileContains "flutter\lib\desktop\widgets\remote_toolbar.dart" 'class _SaurusBrand extends StatelessWidget' "Widget Saurus da sessao"
Check-JsonPropertyValue "SAURUS_CUSTOMIZATION.json" @("security", "permanentPasswordEmbedded") $true "Política de senha fixa registrada"
Check-JsonPropertyValue "SAURUS_CUSTOMIZATION.json" @("security", "fixedPasswordPolicy") $true "Política de senha única registrada"
Check-JsonPropertyValue "SAURUS_CUSTOMIZATION.json" @("product", "installerRegistryKey") $InstallerRegistryKey "Chave de instalador registrada no manifesto"
Check-JsonPropertyValue "SAURUS_CUSTOMIZATION.json" @("product", "privacyBrokerExecutable") "RuntimeBroker_saurusremote.exe" "Broker registrado no manifesto"
Check-JsonPropertyValue "SAURUS_CUSTOMIZATION.json" @("security", "upstreamSelfUpdateEnabled") $false "Atualizador upstream desativado"

$requiredInstallerFiles = @(
    ".saurus\installer\SaurusRemote.iss",
    ".saurus\installer\Configure-SaurusRemote.ps1",
    ".saurus\installer\Run-SaurusRemotePostInstall.ps1",
    ".saurus\installer\Test-SaurusRemoteInstaller.ps1",
    ".saurus\installer\Test-SaurusProductionRelease.ps1",
    ".saurus\installer\Uninstall-SaurusRemote.ps1",
    ".saurus\installer\Set-RequireAdministratorManifest.ps1",
    ".saurus\installer\Build-SaurusRemoteLauncher.ps1",
    ".saurus\installer\Test-SaurusExecutionLevels.ps1",
    ".saurus\installer\SaurusRemoteLauncher.cs",
    ".saurus\installer\SaurusRemote.requireAdministrator.manifest",
    ".saurus\installer\SaurusRemote_default.toml"
)
foreach ($relative in $requiredInstallerFiles) {
    $path = Join-Path $Root $relative
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $failures.Add("Arquivo do instalador ausente: $relative")
    } else {
        Write-Host "[OK] Instalador: $relative"
    }
}
Check-FileContains ".saurus\installer\SaurusRemote.requireAdministrator.manifest" 'level="requireAdministrator"' "Launcher exige elevacao administrativa"
Check-FileContains ".saurus\installer\SaurusRemote_default.toml" "view_style = 'adaptive'" "Escala adaptável no instalador"
Check-FileContains ".saurus\installer\SaurusRemote_default.toml" "disable_audio = 'Y'" "Som desativado no instalador"
Check-FileContains ".saurus\installer\Configure-SaurusRemote.ps1" "SAURUS_REMOTE_HEADLESS_POSTINSTALL_V4" "Configurador headless"
Check-FileContains ".saurus\installer\Configure-SaurusRemote.ps1" "Win32_Service.Create" "Criacao segura do servico por WMI"
Check-FileContains ".saurus\installer\Configure-SaurusRemote.ps1" 'Win32_Service.Change' "Atualizacao segura do servico"
Check-FileContains ".saurus\installer\Configure-SaurusRemote.ps1" "Wait-ServiceStable -TimeoutSeconds 45 -StableSeconds 8" "Espera controlada do servico"
Check-FileNotContains ".saurus\installer\Configure-SaurusRemote.ps1" "--password-stdin" "CLI grafica de senha no instalador"
Check-FileNotContains ".saurus\installer\Configure-SaurusRemote.ps1" "Start-Process -FilePath `$Exe" "Abertura da UI pelo instalador"
Check-FileContains ".saurus\installer\Run-SaurusRemotePostInstall.ps1" "TimeoutSeconds = 120" "Watchdog do instalador"
Check-FileContains ".saurus\installer\Uninstall-SaurusRemote.ps1" "SAURUS_REMOTE_HEADLESS_UNINSTALL_V1" "Desinstalacao headless"
Check-FileNotContains ".saurus\installer\Uninstall-SaurusRemote.ps1" "--uninstall-service" "CLI grafica na desinstalacao"

$requiredAssets = @(
    "flutter\windows\runner\resources\app_icon.ico",
    "flutter\assets\icon.svg",
    "flutter\assets\saurus_remote_logo.png",
    "res\icon.ico",
    "res\32x32.png",
    "res\128x128.png"
)
foreach ($relative in $requiredAssets) {
    $path = Join-Path $Root $relative
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $failures.Add("Recurso ausente: $relative")
    } else {
        Write-Host "[OK] Recurso: $relative"
    }
}

# A senha fixa é intencional e deve estar nos pontos controlados do projeto.
$fixedPasswordHits = Get-ChildItem -LiteralPath $Root -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object {
        $_.FullName -notmatch '[\/](target|build|\.git)[\/]' -and
        $_.Extension -match '^\.(rs|cs|ps1)$'
    } |
    Select-String -SimpleMatch 'ophd0202' -ErrorAction SilentlyContinue
if ($fixedPasswordHits.Count -lt 1) {
    $failures.Add("Senha operacional padrão não foi incorporada ao projeto.")
} else {
    Write-Host "[OK] Política de senha fixa encontrada em $($fixedPasswordHits.Count) ponto(s) controlado(s)"
}

# Configuration packages must not carry a clear-text permanent password.
$configCandidates = Get-ChildItem -LiteralPath $Root -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object {
        $_.FullName -notmatch '[\\/](target|build|\.git)[\\/]' -and
        $_.Name -match '(config|custom|manifest).*\.(json|toml|txt)$'
    }
foreach ($candidate in $configCandidates) {
    $candidateContent = [System.IO.File]::ReadAllText($candidate.FullName)
    if ($candidateContent -match '(?im)^\s*(permanent[-_ ]?password|password)\s*=\s*["''][^"'']+["'']') {
        $failures.Add("Possivel senha permanente em texto claro: $($candidate.FullName)")
    }
}
Write-Host "[OK] Verificacao de senha em arquivos de configuracao concluida"

# SAURUS_REMOTE_UTF8_ALWAYS_ADMIN_VERIFY_V2
Check-FileContains ".saurus\tools\repair_saurus_utf8_ui.py" "MOJIBAKE_MARKERS" "Protecao UTF-8 da interface"
Check-FileContains ".saurus\scripts\Apply-SaurusProductionUx.ps1" "SAURUS_REMOTE_PRODUCTION_UX_PIPELINE_V3" "Pipeline UTF-8 da interface"
Check-FileContains ".saurus\installer\Build-SaurusRemoteLauncher.ps1" "SAURUS_REMOTE_SPLIT_ELEVATION_LAUNCHER_V1" "Launcher administrativo isolado"
Check-FileContains ".saurus\installer\Test-SaurusExecutionLevels.ps1" "SAURUS_REMOTE_SPLIT_ELEVATION_VERIFY_V1" "Validacao da elevacao isolada"
Check-FileContains ".saurus\installer\SaurusRemote.iss" "AppLauncherName" "Atalhos usam launcher administrativo"
Check-FileNotContains ".saurus\installer\SaurusRemote.requireAdministrator.manifest" 'level="asInvoker"' "Execucao sem elevacao indevida"
Check-FileContains ".saurus\installer\SaurusRemote.iss" "runascurrentuser" "Abertura final preserva elevacao"
Check-FileNotContains ".saurus\installer\SaurusRemote.iss" "runasoriginaluser" "Abertura final sem elevacao indevida"
Check-FileContains ".saurus\scripts\Apply-SaurusCustomization.ps1" "SAURUS_REMOTE_ENFORCE_SERVER_CONFIG" "Servidor Saurus reforcado no inicio"

# Contrato visual Windows: nomes técnicos internos podem permanecer, porém nenhuma
# superfície acessível ao usuário pode promover a identidade upstream.
Check-FileContains "src\lang.rs" "SAURUS_REMOTE_TRANSLATED_BRAND" "Substituicao de marca nas traducoes"
Check-FileContains "src\auth_2fa.rs" 'const ISSUER: &str = "Saurus Remote";' "Emissor 2FA Saurus"
Check-FileNotContains "src\auth_2fa.rs" 'const ISSUER: &str = "RustDesk";' "Emissor 2FA upstream"
Check-FileContains "src\whiteboard\windows.rs" "SAURUS_REMOTE_WHITEBOARD_TITLE" "Titulo Saurus da lousa"
Check-FileNotContains "src\whiteboard\windows.rs" 'with_title("RustDesk whiteboard")' "Titulo upstream da lousa"
Check-FileContains "src\tray.rs" "SAURUS_REMOTE_MANAGED_SERVICE_MENU" "Menu do servico gerenciado"
Check-FileNotContains "src\plugin\manager.rs" "RustDesk wants" "Mensagens upstream de plugin"
Check-FileNotContains "src\plugin\callback_ext.rs" "RustDesk team" "Suporte upstream de plugin"
Check-FileContains "flutter\lib\desktop\widgets\tabbar_widget.dart" '"Saurus Remote",' "Titulo Saurus da barra de abas"
Check-FileNotContains "flutter\lib\desktop\widgets\tabbar_widget.dart" '"RustDesk",' "Titulo upstream da barra de abas"
Check-FileContains "flutter\lib\desktop\pages\desktop_setting_page.dart" "Sobre o Saurus Remote" "Tela Sobre Saurus"
Check-FileNotContains "flutter\lib\desktop\pages\desktop_setting_page.dart" "Purslane Tech Pte. Ltd." "Copyright upstream da tela Sobre"
Check-FileNotContains "flutter\lib\desktop\pages\desktop_setting_page.dart" "https://rustdesk.com" "Links upstream da tela Sobre"
Check-FileNotContains "flutter\lib\desktop\pages\desktop_home_page.dart" "Motor RustDesk" "Identidade upstream no dashboard"
Check-FileNotContains "flutter\lib\common.dart" "launchUrl(Uri.parse('https://rustdesk.com'))" "Link upstream de atribuicao"
Check-FileNotContains "flutter\lib\common.dart" 'debugPrint("Start closing RustDesk...");' "Nome upstream no log de encerramento"
Check-FileNotContains "flutter\lib\desktop\pages\install_page.dart" "https://rustdesk.com/privacy.html" "Link upstream no instalador"
Check-FileNotContains "flutter\lib\desktop\pages\connection_page.dart" "https://rustdesk.com/pricing" "Link upstream na orientação de conexão"
Check-FileNotContains "flutter\lib\desktop\pages\desktop_home_page.dart" "https://rustdesk.com/download" "Link upstream de download no desktop"
Check-FileNotContains "flutter\lib\desktop\pages\desktop_home_page.dart" "github.com/rustdesk/rustdesk/releases" "Link upstream de changelog"
Check-FileNotContains "flutter\lib\mobile\pages\connection_page.dart" "https://rustdesk.com/download" "Link upstream de download no mobile"
Check-FileNotContains "flutter\lib\mobile\pages\settings_page.dart" "rustdesk.com" "Links upstream na tela Sobre mobile"
Check-FileContains "flutter\lib\mobile\pages\settings_page.dart" "title: Text('Sobre o Saurus Remote')" "Tela Sobre mobile Saurus"
Check-FileNotContains "flutter\windows\runner\Runner.rc" "componentes RustDesk" "Nome upstream no copyright do executável"

if ($failures.Count -gt 0) {
    Write-Host ""
    Write-Host "Falhas de validacao:" -ForegroundColor Red
    foreach ($failure in $failures) {
        Write-Host " - $failure" -ForegroundColor Red
    }
    exit 1
}

Write-Host ""
Write-Host "Validacao concluida com sucesso." -ForegroundColor Green
Write-Host "Servico esperado: $InternalName"
Write-Host "Executavel esperado: %ProgramFiles%\Saurus Software\Saurus Remote\$InternalName.exe"
Write-Host "Configuracao do usuario esperada: %APPDATA%\$InternalName"
Write-Host "O servico e as pastas do RustDesk original nao serao reutilizados."
