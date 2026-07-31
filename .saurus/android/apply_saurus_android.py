#!/usr/bin/env python3
"""Apply the Saurus Remote Android host customization to RustDesk 1.4.9.

The patch is intentionally strict and idempotent. It validates the exact
upstream contracts before changing them and refuses to continue if a file has
unexpectedly drifted.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Iterable

MARKER = "SAURUS_ANDROID_HOST_V1"


class PatchError(RuntimeError):
    pass


def read_text(path: Path) -> str:
    if not path.is_file():
        raise PatchError(f"Required file not found: {path}")
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")


def replace_exact(path: Path, old: str, new: str, *, expected: int = 1, marker: str | None = None) -> bool:
    content = read_text(path)
    if marker and marker in content:
        return False
    count = content.count(old)
    if count != expected:
        if new in content and count == 0:
            return False
        raise PatchError(f"{path}: expected {expected} occurrence(s), found {count}: {old[:100]!r}")
    write_text(path, content.replace(old, new))
    return True


def replace_regex(
    path: Path,
    pattern: str,
    replacement: str,
    *,
    expected: int = 1,
    marker: str | None = None,
    flags: int = 0,
) -> bool:
    content = read_text(path)
    if marker and marker in content:
        return False
    updated, count = re.subn(pattern, replacement, content, flags=flags)
    if count != expected:
        raise PatchError(f"{path}: expected {expected} regex replacement(s), found {count}: {pattern}")
    write_text(path, updated)
    return True


def insert_before(path: Path, anchor: str, insertion: str, marker: str) -> bool:
    content = read_text(path)
    if marker in content:
        return False
    count = content.count(anchor)
    if count != 1:
        raise PatchError(f"{path}: anchor expected once, found {count}: {anchor!r}")
    write_text(path, content.replace(anchor, insertion + anchor, 1))
    return True


def replace_tokens(path: Path, replacements: Iterable[tuple[str, str, int]]) -> None:
    for old, new, count in replacements:
        replace_exact(path, old, new, expected=count)


def patch_config(root: Path, cfg: dict[str, object]) -> None:
    path = root / "libs/hbb_common/src/config.rs"
    server = str(cfg["rendezvous_server"])
    key = str(cfg["public_key"])
    password = str(cfg["default_access_password"])
    internal_name = str(cfg["internal_name"])

    replace_exact(
        path,
        '    pub static ref APP_NAME: RwLock<String> = RwLock::new("RustDesk".to_owned());',
        f'    pub static ref APP_NAME: RwLock<String> = RwLock::new("{internal_name}".to_owned()); // {MARKER}_INTERNAL_NAME',
    )
    replace_regex(
        path,
        r'(?m)^pub const RENDEZVOUS_SERVERS: &\[&str\] = &\[[^\n]*\];$',
        f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{server}"]; // {MARKER}_RENDEZVOUS',
        marker=f'{MARKER}_RENDEZVOUS',
    )
    replace_exact(
        path,
        '    pub static ref PROD_RENDEZVOUS_SERVER: RwLock<String> = RwLock::new("".to_owned());',
        f'    pub static ref PROD_RENDEZVOUS_SERVER: RwLock<String> = RwLock::new("{server}".to_owned()); // {MARKER}_PROD_RENDEZVOUS',
    )
    replace_regex(
        path,
        r'(?m)^pub const RS_PUB_KEY: &str = "[^"\n]*";$',
        f'pub const RS_PUB_KEY: &str = "{key}"; // {MARKER}_PUBLIC_KEY',
        marker=f'{MARKER}_PUBLIC_KEY',
    )
    insert_before(
        path,
        'pub const RS_PUB_KEY: &str',
        f'pub const SAURUS_REMOTE_DEFAULT_ACCESS_PASSWORD: &str = "{password}"; // {MARKER}_PASSWORD\n',
        f'{MARKER}_PASSWORD',
    )
    guard = f'''    pub fn set_permanent_password(password: &str) -> bool {{
        // {MARKER}_FIXED_PASSWORD
        if password != SAURUS_REMOTE_DEFAULT_ACCESS_PASSWORD {{
            log::warn!("Rejected an attempt to replace the Saurus Remote Android fixed password");
            return false;
        }}'''
    replace_regex(
        path,
        r'    pub fn set_permanent_password\(password: &str\) -> bool \{\s*if Self::is_disable_change_permanent_password\(\) \{\s*return false;\s*\}',
        guard,
        marker=f'{MARKER}_FIXED_PASSWORD',
        flags=re.S,
    )


def patch_flutter_ffi(root: Path, cfg: dict[str, object]) -> None:
    path = root / "src/flutter_ffi.rs"
    name = str(cfg["product_name"])
    server = str(cfg["rendezvous_server"])
    key = str(cfg["public_key"])

    replace_regex(
        path,
        r'pub fn main_get_app_name\(\) -> String \{\s*get_app_name\(\)\s*\}',
        f'pub fn main_get_app_name() -> String {{\n    "{name}".to_owned() // {MARKER}_DISPLAY_NAME\n}}',
        marker=f'{MARKER}_DISPLAY_NAME',
        flags=re.S,
    )
    replace_regex(
        path,
        r'pub fn main_get_app_name_sync\(\) -> SyncReturn<String> \{\s*SyncReturn\(get_app_name\(\)\)\s*\}',
        f'pub fn main_get_app_name_sync() -> SyncReturn<String> {{\n    SyncReturn("{name}".to_owned()) // {MARKER}_DISPLAY_NAME_SYNC\n}}',
        marker=f'{MARKER}_DISPLAY_NAME_SYNC',
        flags=re.S,
    )

    old = '        std::thread::spawn(move || start_server(true));'
    new = f'''        // {MARKER}_SERVICE_DEFAULTS
        config::Config::set_option(
            "custom-rendezvous-server".to_owned(),
            "{server}".to_owned(),
        );
        config::Config::set_option("key".to_owned(), "{key}".to_owned());
        config::Config::set_option("api-server".to_owned(), "".to_owned());
        config::Config::set_option("relay-server".to_owned(), "".to_owned());
        config::Config::set_option(
            "verification-method".to_owned(),
            "use-permanent-password".to_owned(),
        );
        config::Config::set_option("approve-mode".to_owned(), "password".to_owned());
        if !config::Config::set_permanent_password(
            config::SAURUS_REMOTE_DEFAULT_ACCESS_PASSWORD,
        ) {{
            log::error!("Failed to enforce the Saurus Remote Android fixed password");
        }}
        std::thread::spawn(move || start_server(true));'''
    replace_exact(path, old, new, marker=f'{MARKER}_SERVICE_DEFAULTS')


def patch_mobile_home(root: Path) -> None:
    path = root / "flutter/lib/mobile/pages/home_page.dart"
    old = '''  void initPages() {
    _pages.clear();
    if (!bind.isIncomingOnly()) {
      _pages.add(ConnectionPage(
        appBarActions: [],
      ));
    }
    if (isAndroid && !bind.isOutgoingOnly()) {
      _chatPageTabIndex = _pages.length;
      _pages.addAll([ChatPage(type: ChatPageType.mobileMain), ServerPage()]);
    }
    _pages.add(SettingsPage());
  }'''
    new = f'''  void initPages() {{
    // {MARKER}_HOST_FIRST_NAVIGATION
    _pages.clear();
    _chatPageTabIndex = -1;
    if (isAndroid && !bind.isOutgoingOnly()) {{
      _pages.add(ServerPage());
      _chatPageTabIndex = _pages.length;
      _pages.add(ChatPage(type: ChatPageType.mobileMain));
    }}
    if (!bind.isIncomingOnly()) {{
      _pages.add(ConnectionPage(appBarActions: []));
    }}
    _pages.add(SettingsPage());
    if (_selectedIndex >= _pages.length) {{
      _selectedIndex = 0;
    }}
  }}'''
    replace_exact(path, old, new, marker=f'{MARKER}_HOST_FIRST_NAVIGATION')


def patch_server_page(root: Path) -> None:
    path = root / "flutter/lib/mobile/pages/server_page.dart"
    replace_exact(path, '  final title = translate("Share screen");', f'  final title = "Este dispositivo"; // {MARKER}_HOST_TITLE')
    replace_exact(path, '  final icon = const Icon(Icons.mobile_screen_share);', '  final icon = const Icon(Icons.phone_android);')
    old_actions = '''  final appBarActions = (!bind.isDisableSettings() &&
          bind.mainGetBuildinOption(key: kOptionHideSecuritySetting) != 'Y')
      ? [_DropDownAction()]
      : [];'''
    replace_exact(path, old_actions, f'  final appBarActions = <Widget>[]; // {MARKER}_LOCKED_SECURITY_UI')
    replace_exact(path, "    final showOneTime = serverModel.approveMode != 'click' &&\n        serverModel.verificationMethod != kUsePermanentPassword;", f'    final showOneTime = true; // {MARKER}_SHOW_FIXED_PASSWORD')
    replace_exact(path, "        title: translate('Your Device'),", "        title: 'Este dispositivo',")
    replace_exact(path, "                translate('One-time Password'),", "                'Senha de acesso',")
    refresh = '''                      IconButton(
                          visualDensity: VisualDensity.compact,
                          icon: const Icon(Icons.refresh),
                          onPressed: () => bind.mainUpdateTemporaryPassword()),'''
    replace_exact(path, refresh, f'                      const SizedBox(width: 40), // {MARKER}_NO_RANDOM_PASSWORD_REFRESH')
    replace_exact(
        path,
        '        title: translate("Service is not running"),',
        f'        title: "Serviço não iniciado", // {MARKER}_SERVICE_STATUS_TEXT',
    )
    replace_exact(
        path,
        '                label: Text(translate("Start service")))',
        '                label: const Text("Iniciar serviço"))',
    )

    scam_guard = '''                onPressed: () {
                  if (gFFI.userModel.userName.value.isEmpty &&
                      bind.mainGetLocalOption(key: "show-scam-warning") !=
                          "N") {
                    showScamWarning(context, serverModel);
                  } else {
                    serverModel.toggleService();
                  }
                },'''
    replace_exact(
        path,
        scam_guard,
        f'''                onPressed: () {{
                  serverModel.toggleService(); // {MARKER}_DIRECT_SERVICE_START
                }},''',
        marker=f'{MARKER}_DIRECT_SERVICE_START',
    )


def patch_server_model(root: Path, cfg: dict[str, object]) -> None:
    path = root / "flutter/lib/models/server_model.dart"
    password = str(cfg["default_access_password"])
    insert_before(
        path,
        'class ServerModel with ChangeNotifier {',
        f'const kSaurusAndroidAccessPassword = "{password}"; // {MARKER}_DISPLAY_PASSWORD\n',
        f'{MARKER}_DISPLAY_PASSWORD',
    )
    old = '''    if (stopped ||
        verificationMethod == kUsePermanentPassword ||
        _approveMode == 'click') {
      _serverPasswd.text = '-';
    } else {
      if (_serverPasswd.text != temporaryPassword &&
          temporaryPassword.isNotEmpty) {
        _serverPasswd.text = temporaryPassword;
      }
    }'''
    new = f'''    // {MARKER}_FIXED_PASSWORD_MODEL
    if (verificationMethod == kUsePermanentPassword && _approveMode != 'click') {{
      _serverPasswd.text = kSaurusAndroidAccessPassword;
    }} else if (stopped || _approveMode == 'click') {{
      _serverPasswd.text = '-';
    }} else if (_serverPasswd.text != temporaryPassword &&
        temporaryPassword.isNotEmpty) {{
      _serverPasswd.text = temporaryPassword;
    }}'''
    replace_exact(path, old, new, marker=f'{MARKER}_FIXED_PASSWORD_MODEL')


def patch_settings(root: Path) -> None:
    path = root / "flutter/lib/mobile/pages/settings_page.dart"
    content = read_text(path)
    if f'{MARKER}_LOCKED_SETTINGS' in content:
        return

    scan_action = '  final appBarActions = bind.isDisableSettings() ? [] : [ScanButton()];'
    if content.count(scan_action) != 1:
        raise PatchError(f"{path}: settings scan action contract not found")
    content = content.replace(
        scan_action,
        f'  final appBarActions = <Widget>[]; // {MARKER}_NO_SERVER_QR_SCAN',
    )
    # Force network/server/proxy visibility flags to true. This keeps general,
    # permission and start-on-boot settings available, while the Saurus server
    # cannot be changed through the mobile UI.
    replacements = [
        ("  var _hideServer = false;", "  var _hideServer = true;"),
        ("  var _hideProxy = false;", "  var _hideProxy = true;"),
        ("  var _hideNetwork = false;", "  var _hideNetwork = true;"),
        ("  var _hideWebSocket = false;", "  var _hideWebSocket = true;"),
    ]
    for old, new in replacements:
        if content.count(old) != 1:
            raise PatchError(f"{path}: expected one setting declaration: {old}")
        content = content.replace(old, new)
    # Prevent constructor values from un-hiding the protected network section.
    constructor_pattern = re.compile(
        r'''    _hideServer =\n        bind\.mainGetBuildinOption\(key: kOptionHideServerSetting\) == 'Y';\n'''
        r'''    _hideProxy = bind\.mainGetBuildinOption\(key: kOptionHideProxySetting\) == 'Y';\n'''
        r'''    _hideNetwork =\n        bind\.mainGetBuildinOption\(key: kOptionHideNetworkSetting\) == 'Y';\n'''
        r'''    _hideWebSocket =\n        bind\.mainGetBuildinOption\(key: kOptionHideWebSocketSetting\) == 'Y' \|\|\n            isWeb;'''
    )
    replacement = f'''    // {MARKER}_LOCKED_SETTINGS
    _hideServer = true;
    _hideProxy = true;
    _hideNetwork = true;
    _hideWebSocket = true;'''
    content, count = constructor_pattern.subn(replacement, content)
    if count != 1:
        raise PatchError(f"{path}: settings constructor contract not found")
    # Hide the two account-related entries and the deployment QR tool.
    if content.count('if (!bind.isDisableAccount())') != 2:
        raise PatchError(f"{path}: expected two account visibility guards")
    content = content.replace('if (!bind.isDisableAccount())', 'if (false) /* Saurus: account disabled */')
    content = content.replace('if (isAndroid && !bind.isOutgoingOnly())\n            SettingsTile(\n                title: Text(translate(\'Deploy\'))', 'if (false) /* Saurus: deployment settings hidden */\n            SettingsTile(\n                title: Text(translate(\'Deploy\'))')
    # Remove the remaining upstream public links from the mobile About section.
    about_replacements = [
        ("child: Text('rustdesk.com',", "child: Text('Saurus Remote',"),
        ('title: Text(translate("Privacy Statement")),', "title: const Text('Privacidade'),"),
        ("launchUrlString('https://rustdesk.com/privacy.html')", "launchUrlString('https://suporte.saurus.net.br/')"),
        ("title: Text(translate('About RustDesk'))", "title: const Text('Sobre o Saurus Remote')"),
        ("const url = 'https://rustdesk.com/';", "const url = 'https://suporte.saurus.net.br/';"),
    ]
    for old, new in about_replacements:
        if old in content:
            content = content.replace(old, new)
    content += "\n// SAURUS_ANDROID_HOST_V1_BRANDING_LINKS\n"

    # Hide the theme switch because the Android edition is fixed to the light Saurus theme.
    theme_tile = '''          SettingsTile(
            title: Text(translate(
                Theme.of(context).brightness == Brightness.light
                    ? 'Light Theme'
                    : 'Dark Theme')),
            leading: Icon(Theme.of(context).brightness == Brightness.light
                ? Icons.dark_mode
                : Icons.light_mode),
            onPressed: (context) {
              showThemeSettings(gFFI.dialogManager);
            },
          ),'''
    if content.count(theme_tile) != 1:
        raise PatchError(f"{path}: theme tile contract not found")
    content = content.replace(theme_tile, f'          // {MARKER}_FIXED_LIGHT_THEME: theme selector hidden')
    write_text(path, content)


def patch_theme(root: Path) -> None:
    path = root / "flutter/lib/common.dart"
    replacements = [
        ('  static const Color grayBg = Color(0xFFEFEFF2);', '  static const Color grayBg = Color(0xFFF4F5F7);'),
        ('  static const Color accent = Color(0xFF0071FF);', f'  static const Color accent = Color(0xFFD8B62A); // {MARKER}_GOLD'),
        ('  static const Color accent50 = Color(0x770071FF);', '  static const Color accent50 = Color(0x77D8B62A);'),
        ('  static const Color accent80 = Color(0xAA0071FF);', '  static const Color accent80 = Color(0xAAD8B62A);'),
        ('  static const Color canvasColor = Color(0xFF212121);', '  static const Color canvasColor = Color(0xFFF4F5F7);'),
        ('  static const Color idColor = Color(0xFF00B6F0);', '  static const Color idColor = Color(0xFF14213D);'),
        ('  static const Color dark = Colors.black87;', '  static const Color dark = Color(0xFF14213D);'),
        ('  static const Color button = Color(0xFF2C8CFF);', '  static const Color button = Color(0xFFD8B62A);'),
    ]
    content = read_text(path)
    if f'{MARKER}_GOLD' not in content:
        for old, new in replacements:
            if content.count(old) != 1:
                raise PatchError(f"{path}: theme contract not found exactly once: {old}")
            content = content.replace(old, new)
        write_text(path, content)
    replace_exact(
        path,
        '''  static ThemeMode getThemeModePreference() {
    return themeModeFromString(bind.mainGetLocalOption(key: kCommConfKeyTheme));
  }''',
        f'''  static ThemeMode getThemeModePreference() {{
    return ThemeMode.light; // {MARKER}_LIGHT_ONLY
  }}''',
        marker=f'{MARKER}_LIGHT_ONLY',
    )


def patch_android_project(root: Path, cfg: dict[str, object]) -> None:
    manifest = root / "flutter/android/app/src/main/AndroidManifest.xml"
    replace_tokens(
        manifest,
        [
            ('android:label="RustDesk"', 'android:label="Saurus Remote"', 1),
            ('android:label="RustDesk Input"', 'android:label="Saurus Remote - Controle de entrada"', 1),
            ('android:name="com.carriez.flutter_hbb.DEBUG_BOOT_COMPLETED"', 'android:name="br.com.saurus.remote.DEBUG_BOOT_COMPLETED"', 1),
            ('android:scheme="rustdesk"', 'android:scheme="saurusremote"', 1),
        ],
    )

    gradle = root / "flutter/android/app/build.gradle"
    replace_exact(gradle, '        applicationId "com.carriez.flutter_hbb"', f'        applicationId "{cfg["application_id"]}" // {MARKER}_APPLICATION_ID')
    replace_exact(
        gradle,
        '        minSdkVersion 22',
        f'        minSdkVersion {cfg["android_min_sdk"]} // {MARKER}_MIN_SDK_HOST',
    )

    main_service = root / "flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/MainService.kt"
    replace_tokens(
        main_service,
        [
            ('const val DEFAULT_NOTIFY_TITLE = "RustDesk"', f'const val DEFAULT_NOTIFY_TITLE = "Saurus Remote" // {MARKER}_NOTIFICATION', 1),
            ('const val DEFAULT_NOTIFY_TEXT = "Service is running"', 'const val DEFAULT_NOTIFY_TEXT = "Acesso remoto ativo"', 1),
            ('val channelId = "RustDesk"', 'val channelId = "SaurusRemote"', 1),
            ('val channelName = "RustDesk Service"', 'val channelName = "Saurus Remote"', 1),
            ('description = "RustDesk Service Channel"', 'description = "Saurus Remote - compartilhamento de tela"', 1),
        ],
    )

    boot_receiver = root / "flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/BootReceiver.kt"
    replace_tokens(
        boot_receiver,
        [
            ('const val DEBUG_BOOT_COMPLETED = "com.carriez.flutter_hbb.DEBUG_BOOT_COMPLETED"', f'const val DEBUG_BOOT_COMPLETED = "br.com.saurus.remote.DEBUG_BOOT_COMPLETED" // {MARKER}_BOOT_ACTION', 1),
            ('Toast.makeText(context, "RustDesk is Open", Toast.LENGTH_LONG).show()', 'Toast.makeText(context, "Saurus Remote iniciado", Toast.LENGTH_LONG).show()', 1),
        ],
    )

    pubspec = root / "flutter/pubspec.yaml"
    replace_exact(pubspec, 'description: Your Remote Desktop Software', 'description: Saurus Remote para acesso e suporte a dispositivos Android')


def copy_branding(root: Path, kit_root: Path) -> None:
    source = kit_root / "assets"
    mappings = {
        "mipmap-mdpi/ic_launcher.png": "flutter/android/app/src/main/res/mipmap-mdpi/ic_launcher.png",
        "mipmap-hdpi/ic_launcher.png": "flutter/android/app/src/main/res/mipmap-hdpi/ic_launcher.png",
        "mipmap-xhdpi/ic_launcher.png": "flutter/android/app/src/main/res/mipmap-xhdpi/ic_launcher.png",
        "mipmap-xxhdpi/ic_launcher.png": "flutter/android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png",
        "mipmap-xxxhdpi/ic_launcher.png": "flutter/android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png",
        "mipmap-mdpi/ic_stat_logo.png": "flutter/android/app/src/main/res/mipmap-mdpi/ic_stat_logo.png",
        "mipmap-hdpi/ic_stat_logo.png": "flutter/android/app/src/main/res/mipmap-hdpi/ic_stat_logo.png",
        "mipmap-xhdpi/ic_stat_logo.png": "flutter/android/app/src/main/res/mipmap-xhdpi/ic_stat_logo.png",
        "mipmap-xxhdpi/ic_stat_logo.png": "flutter/android/app/src/main/res/mipmap-xxhdpi/ic_stat_logo.png",
        "mipmap-xxxhdpi/ic_stat_logo.png": "flutter/android/app/src/main/res/mipmap-xxxhdpi/ic_stat_logo.png",
        "saurus_remote_logo.png": "flutter/assets/saurus_remote_android_logo.png",
    }
    for relative_source, relative_destination in mappings.items():
        src = source / relative_source
        dst = root / relative_destination
        if not src.is_file():
            raise PatchError(f"Branding asset missing: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def create_manifest(root: Path, cfg: dict[str, object], version: str) -> None:
    manifest = {
        "schema": 1,
        "marker": MARKER,
        "product": cfg["product_name"],
        "version": version,
        "applicationId": cfg["application_id"],
        "mode": "android-host-primary",
        "rendezvousServer": cfg["rendezvous_server"],
        "permanentPasswordEmbedded": True,
        "hostFirst": True,
        "screenCaptureRequiresUserConsent": True,
        "inputControlRequiresAccessibilityService": True,
    }
    (root / "SAURUS_ANDROID_CUSTOMIZATION.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def apply(root: Path, kit_root: Path, version: str) -> None:
    cfg = json.loads((kit_root / "config.json").read_text(encoding="utf-8"))
    patch_config(root, cfg)
    patch_flutter_ffi(root, cfg)
    patch_mobile_home(root)
    patch_server_page(root)
    patch_server_model(root, cfg)
    patch_settings(root)
    patch_theme(root)
    patch_android_project(root, cfg)
    copy_branding(root, kit_root)
    create_manifest(root, cfg, version)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--version", default="1.0.0-test1")
    parser.add_argument("--verify-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.source_root.resolve()
    kit_root = Path(__file__).resolve().parent
    try:
        if args.verify_only:
            from verify_saurus_android import verify

            verify(root, kit_root)
        else:
            apply(root, kit_root, args.version)
            from verify_saurus_android import verify

            verify(root, kit_root)
        print(f"[OK] Saurus Remote Android host customization applied: {args.version}")
        return 0
    except (PatchError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
