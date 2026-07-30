#!/usr/bin/env python3
"""Validacao estatica do kit de customizacao Saurus Remote.

Nao compila o RustDesk. Confere estrutura, politica de segredos, workflow,
branding e marcadores fundamentais antes de o kit ser instalado no fork.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []
WARNINGS: list[str] = []


def error(message: str) -> None:
    ERRORS.append(message)


def warn(message: str) -> None:
    WARNINGS.append(message)


def require(path: str) -> Path:
    target = ROOT / path
    if not target.is_file():
        error(f"Arquivo obrigatorio ausente: {path}")
    return target


def text(path: str) -> str:
    target = require(path)
    return target.read_text(encoding="utf-8-sig", errors="strict") if target.is_file() else ""

def path_is_hashable(path: Path) -> bool:
    return path.name not in {"VALIDATION-REPORT.txt", "kit-manifest.json"} and path.suffix.lower() != ".zip"

REQUIRED = [
    "README.md",
    "CHANGELOG.md",
    "branding/app_icon.ico",
    "branding/app_icon.png",
    "branding/logo_transparent.png",
    "scripts/Apply-SaurusCustomization.ps1",
    "scripts/Verify-SaurusCustomization.ps1",
    "scripts/Build-SaurusRemote.ps1",
    "scripts/Install-KitIntoRustDeskFork.ps1",
    "scripts/Get-SaurusRemoteDiagnostics.ps1",
    "scripts/Test-InstalledCoexistence.ps1",
    "tools/check_upstream_149.py",
    "github/build-saurus-remote-windows.yml",
    "samples/SaurusRemoteEngineClient.cs",
    "samples/Install-Engine.ps1",
    "samples/Provisionar-Senha.ps1",
    "installer/SaurusRemote.iss",
    "installer/Test-SaurusRemoteInstaller.ps1",
    "installer/Configure-SaurusRemote.ps1",
    "installer/Uninstall-SaurusRemote.ps1",
    "installer/Set-RequireAdministratorManifest.ps1",
    "installer/SaurusRemote.requireAdministrator.manifest",
    "installer/SaurusRemote_default.toml",
    "docs/REVISAO-CODIGO-LEGADO.md",
    "docs/ARQUITETURA.md",
    "docs/INTEGRACAO-LAUNCHER.md",
    "docs/BUILD-GITHUB-ACTIONS.md",
    "docs/INSTALADOR-DEFINITIVO.md",
    "docs/SEGURANCA-E-LICENCA.md",
    "docs/VALIDACAO-UPSTREAM-1.4.9.md",
    "LICENSES/RustDesk-AGPL-3.0-NOTICE.txt",
]
for item in REQUIRED:
    require(item)

for unexpected in ROOT.rglob("*"):
    if unexpected.is_file() and (unexpected.suffix.lower() in {".bak", ".tmp"} or unexpected.name.endswith("~")):
        error(f"Arquivo temporario nao deve ser distribuido: {unexpected.relative_to(ROOT)}")

# A senha fixa é uma decisão operacional explícita e deve estar nos componentes controlados.
fixed_password = "ophd0202"
for required_secret_file in [
    "scripts/Apply-SaurusCustomization.ps1",
    "samples/SaurusRemoteEngineClient.cs",
    "samples/Provisionar-Senha.ps1",
]:
    if fixed_password not in text(required_secret_file):
        error(f"Senha operacional padrão ausente em: {required_secret_file}")

apply_script = text("scripts/Apply-SaurusCustomization.ps1")

# Regressao: em PowerShell, aspas dentro de string interpolada usam crase + aspas.
# A forma crase + barra invertida + aspas causa ParserError antes de o patch iniciar.
if 'L`\\"$displayNameCpp`\\"' in apply_script:
    error("Escape invalido de aspas na insercao C++ (ParserError do PowerShell).")
if 'app_name = L`"$displayNameCpp`";' not in apply_script:
    error("Insercao C++ corrigida para o nome visual nao foi encontrada.")

# Regressao: PROD_RENDEZVOUS_SERVER fica dentro de lazy_static! com quatro espacos.
# Remover a indentacao tiraria a declaracao do bloco Rust; exigir ^ sem espacos causa falso negativo.
prod_original = '    pub static ref PROD_RENDEZVOUS_SERVER: RwLock<String> = RwLock::new("".to_owned());'
if prod_original not in apply_script:
    error("Contrato upstream indentado de PROD_RENDEZVOUS_SERVER ausente.")
if '$prodServerOriginal' not in apply_script or 'Replace-LiteralRequired $configPath' not in apply_script:
    error("Substituicao literal segura de PROD_RENDEZVOUS_SERVER ausente.")
if "(?m)^pub static ref PROD_RENDEZVOUS_SERVER" in apply_script:
    error("Regex antigo de PROD_RENDEZVOUS_SERVER ainda ignora a indentacao do lazy_static.")

# Regressao: em checkout Windows, pubspec.yaml pode usar CRLF. Um regex terminado em `$`
# falha antes do `\r`. A descricao da tag 1.4.9 deve ser trocada literalmente.
if "(?m)^description:[^\\r\\n]*$" in apply_script:
    error("Regex antigo de descricao Flutter ainda e sensivel a CRLF.")
if "'description: Your Remote Desktop Software'" not in apply_script:
    error("Contrato literal upstream da descricao Flutter ausente.")
if 'Replace-LiteralRequired $pubspecPath' not in apply_script:
    error("Substituicao literal da descricao Flutter ausente.")

# Regressao: a chave de escala no RustDesk 1.4.9 e keys::OPTION_VIEW_STYLE,
# nao o texto literal "view_style" no match de UserDefaultConfig::get.
adaptive_original = '            keys::OPTION_VIEW_STYLE => self.get_string(key, "original", vec!["adaptive"]),'
adaptive_replacement = '            keys::OPTION_VIEW_STYLE => self.get_string(key, "adaptive", vec!["original"]), // SAURUS_REMOTE_DEFAULT_ADAPTIVE_VIEW'
if adaptive_original not in apply_script:
    error("Contrato literal upstream da escala desktop ausente.")
if adaptive_replacement not in apply_script:
    error("Substituicao literal para escala adaptavel ausente.")
if 'Replace-LiteralRequired $configPath' not in apply_script or '$adaptiveViewOriginal' not in apply_script:
    error("Aplicacao literal da escala adaptavel ausente.")
if r'"view_style"\s*=>\s*self\.get_string' in apply_script:
    error("Regex antigo de escala procura uma chave inexistente no RustDesk 1.4.9.")
verify_script = text("scripts/Verify-SaurusCustomization.ps1")
workflow = text("github/build-saurus-remote-windows.yml")
client = text("samples/SaurusRemoteEngineClient.cs")
local_build = text("scripts/Build-SaurusRemote.ps1")

for marker in [
    "SAURUS_REMOTE_WINDOW_DISPATCH",
    "SAURUS_REMOTE_PASSWORD_STDIN",
    "SAURUS_REMOTE_MANAGED_UPDATE",
    "SAURUS_REMOTE_INSTALLER_REGISTRY",
    "SAURUS_REMOTE_CUSTOM_CLIENT_STAGING",
    "SAURUS_REMOTE_TEMP_UPDATE_PREFIX",
    "SAURUS_REMOTE_OUTPUT_CAPTION",
    "RuntimeBroker_{0}.exe",
    "SaurusRemotePrivacyWindowClass",
    "Saurus Remote Service",
    "Saurus Software\\Saurus Remote",
    "toolbarItems.add(const _SaurusBrand());",
    "permanentPasswordEmbedded = $true",
    "SAURUS_REMOTE_FIXED_ACCESS_PASSWORD",
    "SAURUS_REMOTE_ENFORCE_DEFAULT_PASSWORD",
    "SAURUS_REMOTE_FIXED_PASSWORD_CLI",
    "SAURUS_REMOTE_FIXED_LIGHT_THEME",
    "Widget _buildSaurusShell(BuildContext context)",
    "SAURUS_REMOTE_NO_ACCOUNT",
    "SAURUS_REMOTE_NO_LOGIN_DEPENDENT_OPTIONS",
    "SAURUS_REMOTE_DEFAULT_ADAPTIVE_VIEW",
    "SAURUS_REMOTE_DEFAULT_DISABLE_AUDIO",
    "SAURUS_REMOTE_NORMAL_START_PASSWORD_ENFORCEMENT",
]:
    if marker not in apply_script:
        error(f"Marcador de customizacao ausente: {marker}")

for marker in [
    'Check-FileContains "Cargo.toml" \'version = "1.4.9"\'',
    "Política de senha fixa encontrada",
    "Saurus Remote Service",
    "SAURUS_REMOTE_INSTALLER_REGISTRY",
    "SaurusRemoteCustomClientStaging",
    "RuntimeBroker_saurusremote.exe",
    "O servico e as pastas do RustDesk original nao serao reutilizados.",
]:
    if marker not in verify_script:
        error(f"Verificacao obrigatoria ausente: {marker}")

for forbidden in [
    r"net\s+stop\s+rustdesk",
    r"sc\s+delete\s+rustdesk",
    r"rmdir[^\r\n]*Program Files\\RustDesk",
    r"GetProcessesByName\(\s*[\"']rustdesk[\"']\s*\)",
]:
    executable_lines = "\n".join(
        line for line in apply_script.splitlines() if not line.lstrip().startswith("#")
    )
    if re.search(forbidden, executable_lines, flags=re.IGNORECASE):
        error(f"Operacao destrutiva contra RustDesk original encontrada: {forbidden}")

expected_versions = {
    'RUST_VERSION: "1.75"',
    'LLVM_VERSION: "15.0.6"',
    'FLUTTER_VERSION: "3.24.5"',
    'VCPKG_COMMIT_ID: "120deac3062162151622ca4860575a33844ba10b"',
    'UPSTREAM_VERSION: "1.4.9"',
}
for value in expected_versions:
    if value not in workflow:
        error(f"Versao/pino ausente no workflow: {value}")

# Regressao: o SDK Flutter modificado nao pode ser salvo no cache, e o patch deve ser idempotente.
if "cache: true" in workflow:
    error("O cache do SDK Flutter nao deve ser habilitado quando o SDK e alterado por patch.")
for marker in [
    "git apply --check",
    "git apply --reverse --check",
    "Patch Flutter ja estava aplicado",
    "bool _enableFilter = false;",
]:
    if marker not in workflow:
        error(f"Protecao idempotente do patch Flutter ausente: {marker}")

for marker in [
    "check_upstream_149.py",
    "include_remote_printer",
    "default: false",
    "Apply-SaurusCustomization.ps1",
    "Verify-SaurusCustomization.ps1",
    "SaurusRemote.exe",
    "SAURUS_CODESIGN_PFX_BASE64",
    "SAURUS_FLUTTER_ENGINE_SHA256",
    "SAURUS_USBMMIDD_SHA256",
    "engine-manifest.json",
    "SHA256SUMS.txt",
    "Build definitive Saurus Remote installer",
    "SaurusRemote.iss",
    "requiresAdministrator = $true",
    "definitiveInstallerIncluded = $true",
    "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
]:
    if marker not in workflow:
        error(f"Etapa obrigatoria ausente no workflow: {marker}")


for marker in [
    'git submodule update --init --recursive',
    'check_upstream_149.py',
    'Apply-SaurusCustomization.ps1',
    'Verify-SaurusCustomization.ps1',
    'Set-RequireAdministratorManifest.ps1',
    'SaurusRemote.iss',
    'SaurusRemote-$ProductVersion-Setup.exe',
]:
    if marker not in local_build:
        error(f"Etapa obrigatoria ausente no build local: {marker}")

submodule_index = local_build.find('git submodule update --init --recursive')
preflight_index = local_build.find('check_upstream_149.py')
apply_index = local_build.find('Apply-SaurusCustomization.ps1')
if not (0 <= submodule_index < preflight_index < apply_index):
    error("Build local deve atualizar submodulos, executar preflight e somente depois aplicar a customizacao.")

# Actions externas devem estar fixadas por commit; workflows locais usam ./.
for line_number, line in enumerate(workflow.splitlines(), start=1):
    match = re.search(r"\buses:\s*([^\s#]+)", line)
    if not match:
        continue
    reference = match.group(1)
    if reference.startswith("./"):
        continue
    if "@" not in reference or not re.search(r"@[0-9a-fA-F]{40}$", reference):
        error(f"Action sem SHA de 40 caracteres na linha {line_number}: {reference}")

coexistence = text("scripts/Test-InstalledCoexistence.ps1")
for marker in [
    "SaurusInstallerKey",
    "RustDeskInstallerKey",
    "SaurusRemoteCustomClientStaging",
    "RuntimeBroker_saurusremote",
    "SameInstallLocation",
]:
    if marker not in coexistence:
        error(f"Verificacao de coexistencia ausente: {marker}")

for marker in [
    "--password-stdin",
    'DefaultAccessPassword = "ophd0202"',
    "EnsureDefaultAccessPasswordAsync",
    "RedirectStandardInput = standardInput != null",
    "RemoteIdRegex",
    "CancellationToken",
    "TryKill(process)",
]:
    if marker not in client:
        error(f"Protecao ausente no cliente C#: {marker}")

installer_manifest = text("installer/SaurusRemote.requireAdministrator.manifest")
installer_config = text("installer/Configure-SaurusRemote.ps1")
installer_iss = text("installer/SaurusRemote.iss")
default_toml = text("installer/SaurusRemote_default.toml")
for marker in [
    'level="requireAdministrator"',
    'processorArchitecture="amd64"',
]:
    if marker not in installer_manifest:
        error(f"Manifesto administrativo incompleto: {marker}")
for marker in [
    '--password-stdin',
    'verification-method',
    'use-permanent-password',
    'allow-logon-screen-password',
    'disable-change-permanent-password',
    'SaurusRemote_default.toml',
    'Set-ServiceReliability',
    'Migrate-PeerDefaults',
    'view_style',
    'disable_audio',
    'Senha permanente confirmada pelo motor',
    'Senha e politica de autenticacao confirmadas apos reiniciar o servico',
    'sc.exe config $ServiceName start= auto',
]:
    if marker not in installer_config:
        error(f"Configurador do instalador incompleto: {marker}")
if "$confirmation -notmatch '(?i)\\bDone\\b|conclu[ií]d|success'" not in installer_config:
    error("Configurador aceita retorno vazio ao aplicar a senha; confirmacao estrita ausente.")
if "$updated = Set-TomlPreference $content \"view_style\" \"'adaptive'\"" not in installer_config:
    error("Migracao de escala adaptavel para pares existentes ausente.")
if "$updated = Set-TomlPreference $updated \"disable_audio\" \"true\"" not in installer_config:
    error("Migracao de audio desativado para pares existentes ausente.")

for marker in [
    'PrivilegesRequired=admin',
    'Configure-SaurusRemote.ps1',
    'Uninstall-SaurusRemote.ps1',
    'SaurusRemote-{#ProductVersion}-Setup',
    'procedure CurStepChanged(CurStep: TSetupStep)',
    'if ResultCode <> 0 then',
    'RaiseException',
]:
    if marker not in installer_iss:
        error(f"Script Inno Setup incompleto: {marker}")
for marker in ["view_style = 'adaptive'", "disable_audio = 'Y'"]:
    if marker not in default_toml:
        error(f"Preferencia operacional ausente: {marker}")

# SAURUS_REMOTE_INNO_PREFLIGHT_VALIDATION_V1
if "AppId={{1117CE17-506B-4122-A421-69233FCA9C12}" not in installer_iss:
    error("AppId do Inno Setup nao usa o escape literal correto para a chave GUID.")
if "AppId={#AppGuid}" in installer_iss:
    error("AppId antigo ainda expande para uma constante Inno invalida.")
for marker in [
    "VersionInfoVersion=1.4.9.0",
    "VersionInfoProductVersion=1.4.9.0",
    "VersionInfoProductTextVersion={#ProductVersion}",
]:
    if marker not in installer_iss:
        error(f"Diretiva segura de versao ausente no Inno Setup: {marker}")
installer_preflight = text("installer/Test-SaurusRemoteInstaller.ps1")
for marker in [
    "Compilacao real de preflight do Inno Setup concluida",
    "AppId={{1117CE17-506B-4122-A421-69233FCA9C12}",
    "VersionInfoProductTextVersion",
]:
    if marker not in installer_preflight:
        error(f"Protecao ausente no preflight do instalador: {marker}")
for marker in [
    "validate-installer:",
    "Compile installer preflight",
    "needs: [generate-bridge, build-topmost-window, validate-installer]",
]:
    if marker not in workflow:
        error(f"Preflight do instalador ausente no workflow: {marker}")
# Valida YAML quando PyYAML estiver disponivel; nao e dependencia do kit.
try:
    import yaml  # type: ignore

    parsed = yaml.safe_load(workflow)
    if not isinstance(parsed, dict) or "jobs" not in parsed:
        error("Workflow YAML nao contem o mapa jobs.")
except ImportError:
    warn("PyYAML indisponivel; validacao sintatica completa do YAML foi ignorada.")
except Exception as exc:  # pragma: no cover - diagnostico
    error(f"Workflow YAML invalido: {exc}")

# Confere imagens quando Pillow estiver disponivel.
try:
    from PIL import Image  # type: ignore

    expected_images = {
        "branding/app_icon.png": (500, 500),
        "branding/logo_transparent.png": (858, 1000),
        "branding/32x32.png": (32, 32),
        "branding/64x64.png": (64, 64),
        "branding/128x128.png": (128, 128),
        "branding/128x128@2x.png": (256, 256),
    }
    for relative, expected_size in expected_images.items():
        path = require(relative)
        if path.is_file():
            with Image.open(path) as image:
                if image.size != expected_size:
                    error(f"Dimensao incorreta em {relative}: {image.size}; esperado {expected_size}")
    ico_path = require("branding/app_icon.ico")
    if ico_path.is_file():
        with Image.open(ico_path) as icon:
            sizes = set(icon.info.get("sizes", []))
            for required_size in {(16, 16), (32, 32), (48, 48), (256, 256)}:
                if required_size not in sizes:
                    error(f"ICO nao contem o tamanho {required_size[0]}x{required_size[1]}")
except ImportError:
    warn("Pillow indisponivel; dimensoes de imagens nao foram verificadas.")
except Exception as exc:  # pragma: no cover - diagnostico
    error(f"Falha ao validar branding: {exc}")

# Garante que os JSON distribuidos sejam validos.
for json_file in ROOT.rglob("*.json"):
    try:
        json.loads(json_file.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        error(f"JSON invalido em {json_file.relative_to(ROOT)}: {exc}")

print("Saurus Remote customization kit - validacao estatica")
print(f"Raiz: {ROOT}")
print(f"Arquivos: {sum(1 for p in ROOT.rglob('*') if p.is_file())}")
if WARNINGS:
    print("Avisos:")
    for item in WARNINGS:
        print(f"  - {item}")
if ERRORS:
    print("Falhas:")
    for item in ERRORS:
        print(f"  - {item}")
    sys.exit(1)

# Hash curto do conteudo para facilitar comparacao do resultado de validacao.
digest = hashlib.sha256()
for path in sorted(p for p in ROOT.rglob("*") if p.is_file() and path_is_hashable(p)):
    digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
    digest.update(path.read_bytes())
print("Resultado: APROVADO")
print(f"Fingerprint do kit: {digest.hexdigest()}")


