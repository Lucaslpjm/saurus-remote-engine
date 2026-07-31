#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANDROID = HERE.parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


apply_mod = load_module("apply_saurus_android", ANDROID / "apply_saurus_android.py")
verify_mod = load_module("verify_saurus_android", ANDROID / "verify_saurus_android.py")


def put(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip("\n") + "\n", encoding="utf-8")


def create_fixture(root: Path) -> None:
    put(
        root,
        "libs/hbb_common/src/config.rs",
        '''
use std::sync::RwLock;
lazy_static::lazy_static! {
    pub static ref PROD_RENDEZVOUS_SERVER: RwLock<String> = RwLock::new("".to_owned());
    pub static ref APP_NAME: RwLock<String> = RwLock::new("RustDesk".to_owned());
}
pub const RENDEZVOUS_SERVERS: &[&str] = &["rs-ny.rustdesk.com"];
pub const RS_PUB_KEY: &str = "old";
impl Config {
    pub fn set_permanent_password(password: &str) -> bool {
        if Self::is_disable_change_permanent_password() {
            return false;
        }
        let _ = password;
        true
    }
}
''',
    )
    put(
        root,
        "src/flutter_ffi.rs",
        '''
use hbb_common::{config, log};
pub fn main_get_app_name() -> String {
    get_app_name()
}
pub fn main_get_app_name_sync() -> SyncReturn<String> {
    SyncReturn(get_app_name())
}
pub unsafe extern "system" fn Java_ffi_FFI_startServer() {
        std::thread::spawn(move || start_server(true));
}
''',
    )
    put(
        root,
        "flutter/lib/mobile/pages/home_page.dart",
        '''
class HomePageState {
  var _selectedIndex = 0;
  final List<PageShape> _pages = [];
  int _chatPageTabIndex = -1;
  void initPages() {
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
  }
}
''',
    )
    put(
        root,
        "flutter/lib/mobile/pages/server_page.dart",
        '''
class ServerPage {
  final title = translate("Share screen");
  final icon = const Icon(Icons.mobile_screen_share);
  final appBarActions = (!bind.isDisableSettings() &&
          bind.mainGetBuildinOption(key: kOptionHideSecuritySetting) != 'Y')
      ? [_DropDownAction()]
      : [];
}
class ServiceNotRunningNotification {
  Widget build() {
    final serverModel = Provider.of<ServerModel>(context);
    return PaddingCard(
        title: translate("Service is not running"),
        child: ElevatedButton.icon(
                icon: const Icon(Icons.play_arrow),
                onPressed: () {
                  if (gFFI.userModel.userName.value.isEmpty &&
                      bind.mainGetLocalOption(key: "show-scam-warning") !=
                          "N") {
                    showScamWarning(context, serverModel);
                  } else {
                    serverModel.toggleService();
                  }
                },
                label: Text(translate("Start service"))));
  }
}
class ServerInfo {
  Widget build() {
    final showOneTime = serverModel.approveMode != 'click' &&
        serverModel.verificationMethod != kUsePermanentPassword;
    return PaddingCard(
        title: translate('Your Device'),
        child: Column(children: [
          Text(
                translate('One-time Password'),
          ),
          !showOneTime ? '-' : model.serverPasswd.value.text,
          !showOneTime
              ? SizedBox.shrink()
              : Row(children: [
                      IconButton(
                          visualDensity: VisualDensity.compact,
                          icon: const Icon(Icons.refresh),
                          onPressed: () => bind.mainUpdateTemporaryPassword()),
                      IconButton(icon: Icon(Icons.copy_outlined)),
                ])
        ]));
  }
}
''',
    )
    put(
        root,
        "flutter/lib/models/server_model.dart",
        '''
const kUseTemporaryPassword = "use-temporary-password";
const kUsePermanentPassword = "use-permanent-password";
const kUseBothPasswords = "use-both-passwords";
class ServerModel with ChangeNotifier {
  updatePasswordModel() async {
    var stopped = await mainGetBoolOption(kOptionStopService);
    final oldPwdText = _serverPasswd.text;
    if (stopped ||
        verificationMethod == kUsePermanentPassword ||
        _approveMode == 'click') {
      _serverPasswd.text = '-';
    } else {
      if (_serverPasswd.text != temporaryPassword &&
          temporaryPassword.isNotEmpty) {
        _serverPasswd.text = temporaryPassword;
      }
    }
  }
}
''',
    )
    put(
        root,
        "flutter/lib/mobile/pages/settings_page.dart",
        '''
class SettingsPage extends StatefulWidget implements PageShape {
  @override
  final title = translate("Settings");
  @override
  final icon = Icon(Icons.settings);
  @override
  final appBarActions = bind.isDisableSettings() ? [] : [ScanButton()];
}
class _SettingsState {
  var _hideServer = false;
  var _hideProxy = false;
  var _hideNetwork = false;
  var _hideWebSocket = false;
  _SettingsState() {
    _hideServer =
        bind.mainGetBuildinOption(key: kOptionHideServerSetting) == 'Y';
    _hideProxy = bind.mainGetBuildinOption(key: kOptionHideProxySetting) == 'Y';
    _hideNetwork =
        bind.mainGetBuildinOption(key: kOptionHideNetworkSetting) == 'Y';
    _hideWebSocket =
        bind.mainGetBuildinOption(key: kOptionHideWebSocketSetting) == 'Y' ||
            isWeb;
  }
  Widget build() {
    return SettingsList(sections: [
      if (!bind.isDisableAccount()) SettingsSection(),
      if (isAndroid && !bind.isOutgoingOnly())
            SettingsTile(
                title: Text(translate('Deploy')),
                leading: Icon(Icons.cloud_upload),
                onPressed: (context) {
                  showDeployDialog();
                }),
          SettingsTile(
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
          ),
      if (!bind.isDisableAccount()) SettingsTile.switchTile(),
    ]);
  }
}
''',
    )
    put(
        root,
        "flutter/lib/common.dart",
        '''
class MyTheme {
  static const Color grayBg = Color(0xFFEFEFF2);
  static const Color accent = Color(0xFF0071FF);
  static const Color accent50 = Color(0x770071FF);
  static const Color accent80 = Color(0xAA0071FF);
  static const Color canvasColor = Color(0xFF212121);
  static const Color idColor = Color(0xFF00B6F0);
  static const Color dark = Colors.black87;
  static const Color button = Color(0xFF2C8CFF);
  static ThemeMode getThemeModePreference() {
    return themeModeFromString(bind.mainGetLocalOption(key: kCommConfKeyTheme));
  }
}
''',
    )
    put(
        root,
        "flutter/android/app/src/main/AndroidManifest.xml",
        '''
<manifest>
<application android:label="RustDesk">
<receiver><action android:name="com.carriez.flutter_hbb.DEBUG_BOOT_COMPLETED" /></receiver>
<service android:label="RustDesk Input" />
<activity><data android:scheme="rustdesk" /></activity>
</application>
</manifest>
''',
    )
    put(
        root,
        "flutter/android/app/build.gradle",
        '''
android {
 defaultConfig {
        applicationId "com.carriez.flutter_hbb"
        minSdkVersion 22
 }
}
''',
    )
    put(
        root,
        "flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/MainService.kt",
        '''
const val DEFAULT_NOTIFY_TITLE = "RustDesk"
const val DEFAULT_NOTIFY_TEXT = "Service is running"
fun initNotification() {
    val channelId = "RustDesk"
    val channelName = "RustDesk Service"
    description = "RustDesk Service Channel"
}
''',
    )
    put(
        root,
        "flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/BootReceiver.kt",
        '''
const val DEBUG_BOOT_COMPLETED = "com.carriez.flutter_hbb.DEBUG_BOOT_COMPLETED"
fun boot() {
Toast.makeText(context, "RustDesk is Open", Toast.LENGTH_LONG).show()
}
''',
    )
    put(root, "flutter/pubspec.yaml", "description: Your Remote Desktop Software")



def test_title_stage_contract() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        create_fixture(root)
        apply_mod.apply(root, ANDROID, "1.0.2-stage-test")
        server_path = root / "flutter/lib/mobile/pages/server_page.dart"
        base_content = server_path.read_text(encoding="utf-8")
        assert verify_mod.expected_host_title(base_content) == verify_mod.BASE_HOST_TITLE
        verify_mod.verify(root, ANDROID)

        final_content = base_content.replace(
            'final title = "Este dispositivo"; // SAURUS_ANDROID_HOST_V1_HOST_TITLE',
            'final title = "Dispositivo"; // SAURUS_ANDROID_UI_V2_SERVER',
            1,
        )
        assert final_content != base_content, "The fixture did not transition to the final UI stage"
        server_path.write_text(final_content, encoding="utf-8", newline="\n")
        assert verify_mod.expected_host_title(final_content) == verify_mod.FINAL_HOST_TITLE
        verify_mod.verify(root, ANDROID)

        conflicting = final_content.replace(
            'final title = "Dispositivo"; // SAURUS_ANDROID_UI_V2_SERVER',
            'final title = "Este dispositivo"; // SAURUS_ANDROID_UI_V2_SERVER',
            1,
        )
        try:
            verify_mod.verify_host_title(conflicting)
        except verify_mod.VerificationError:
            pass
        else:
            raise AssertionError("A mismatched UI marker/title pair was accepted")

def main() -> int:
    test_title_stage_contract()
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        create_fixture(root)
        apply_mod.apply(root, ANDROID, "1.0.0-test")
        verify_mod.verify(root, ANDROID)
        settings = (root / "flutter/lib/mobile/pages/settings_page.dart").read_text(encoding="utf-8")
        assert "if (false) //" not in settings, "A line comment cannot replace a Dart collection-if guard"
        assert settings.count("if (false) /* Saurus: account disabled */") == 2
        assert "if (false) /* Saurus: deployment settings hidden */" in settings
        before = {
            p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*")
            if p.is_file()
        }
        apply_mod.apply(root, ANDROID, "1.0.0-test")
        verify_mod.verify(root, ANDROID)
        after = {
            p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*")
            if p.is_file()
        }
        assert before == after, "Customization is not idempotent"
    print("[OK] Android base customization and title-stage contract tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
