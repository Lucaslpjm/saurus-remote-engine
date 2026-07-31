#!/usr/bin/env python3
"""Static verification for the Saurus Remote Android host customization."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MARKER = "SAURUS_ANDROID_HOST_V1"
UI_V2_SERVER_MARKER = "SAURUS_ANDROID_UI_V2_SERVER"
BASE_HOST_TITLE = 'final title = "Este dispositivo"'
FINAL_HOST_TITLE = 'final title = "Dispositivo"'


def expected_host_title(server_page: str) -> str:
    """Return the title contract for the currently applied customization stage.

    The base host patch intentionally uses ``Este dispositivo``. The visual V2
    layer later compacts the page title to ``Dispositivo`` and adds its marker.
    The verifier must support both valid stages so unit tests and production
    verification do not contradict each other.
    """
    return FINAL_HOST_TITLE if UI_V2_SERVER_MARKER in server_page else BASE_HOST_TITLE


def verify_host_title(server_page: str) -> None:
    expected = expected_host_title(server_page)
    require(server_page, expected, "host page title")
    unexpected = BASE_HOST_TITLE if expected == FINAL_HOST_TITLE else FINAL_HOST_TITLE
    if unexpected in server_page:
        raise VerificationError(
            f"Conflicting host page title for the detected customization stage: {unexpected}"
        )


class VerificationError(RuntimeError):
    pass


def read(path: Path) -> str:
    if not path.is_file():
        raise VerificationError(f"Required file missing: {path}")
    return path.read_text(encoding="utf-8-sig")


def require(content: str, value: str, description: str) -> None:
    if value not in content:
        raise VerificationError(f"Missing {description}: {value}")


def forbid(content: str, value: str, description: str) -> None:
    if value in content:
        raise VerificationError(f"Forbidden {description}: {value}")


def require_count(content: str, value: str, count: int, description: str) -> None:
    actual = content.count(value)
    if actual != count:
        raise VerificationError(f"{description}: expected {count}, found {actual}: {value}")


def verify(root: Path, kit_root: Path) -> None:
    cfg = json.loads((kit_root / "config.json").read_text(encoding="utf-8"))
    server = cfg["rendezvous_server"]
    key = cfg["public_key"]
    password = cfg["default_access_password"]

    config = read(root / "libs/hbb_common/src/config.rs")
    for value, description in [
        (f'RwLock::new("SaurusRemote".to_owned()); // {MARKER}_INTERNAL_NAME', "internal name"),
        (f'RENDEZVOUS_SERVERS: &[&str] = &["{server}"]', "rendezvous server"),
        (f'PROD_RENDEZVOUS_SERVER: RwLock<String> = RwLock::new("{server}".to_owned())', "production server"),
        (f'RS_PUB_KEY: &str = "{key}"', "public key"),
        (f'SAURUS_REMOTE_DEFAULT_ACCESS_PASSWORD: &str = "{password}"', "fixed password"),
        (f'{MARKER}_FIXED_PASSWORD', "password guard"),
    ]:
        require(config, value, description)

    ffi = read(root / "src/flutter_ffi.rs")
    for value, description in [
        (f'"Saurus Remote".to_owned() // {MARKER}_DISPLAY_NAME', "Flutter app name"),
        (f'{MARKER}_SERVICE_DEFAULTS', "Android service defaults"),
        ('"custom-rendezvous-server".to_owned()', "custom server option"),
        ('"verification-method".to_owned()', "verification method"),
        ('"use-permanent-password".to_owned()', "permanent password mode"),
        ('"approve-mode".to_owned(), "password".to_owned()', "password approval mode"),
        ('config::SAURUS_REMOTE_DEFAULT_ACCESS_PASSWORD', "service password enforcement"),
    ]:
        require(ffi, value, description)

    home = read(root / "flutter/lib/mobile/pages/home_page.dart")
    require(home, f'{MARKER}_HOST_FIRST_NAVIGATION', "host-first navigation marker")
    server_pos = home.find("_pages.add(ServerPage());")
    chat_pos = home.find("_pages.add(ChatPage(type: ChatPageType.mobileMain));")
    connection_pos = home.find("_pages.add(ConnectionPage(appBarActions: []));")
    if not (0 <= server_pos < chat_pos < connection_pos):
        raise VerificationError("Mobile navigation is not ordered as Host, Chat, Connections")

    server_page = read(root / "flutter/lib/mobile/pages/server_page.dart")
    verify_host_title(server_page)
    for value, description in [
        (f'{MARKER}_LOCKED_SECURITY_UI', "locked security menu"),
        (f'{MARKER}_SHOW_FIXED_PASSWORD', "fixed password visibility"),
        ("title: 'Este dispositivo'", "device card title"),
        ("'Senha de acesso'", "password label"),
        (f'{MARKER}_NO_RANDOM_PASSWORD_REFRESH', "random password refresh removal"),
        (f'{MARKER}_DIRECT_SERVICE_START', "direct service start without account dependency"),
        (f'{MARKER}_SERVICE_STATUS_TEXT', "localized service status"),
        ('const Text("Iniciar serviço")', "localized service start button"),
    ]:
        require(server_page, value, description)
    forbid(server_page, "final title = translate(\"Share screen\")", "old share-screen title")

    server_model = read(root / "flutter/lib/models/server_model.dart")
    require(server_model, f'kSaurusAndroidAccessPassword = "{password}"', "display password constant")
    require(server_model, f'{MARKER}_FIXED_PASSWORD_MODEL', "fixed password model")

    settings = read(root / "flutter/lib/mobile/pages/settings_page.dart")
    require(settings, f'{MARKER}_LOCKED_SETTINGS', "locked network settings")
    require(settings, f'{MARKER}_NO_SERVER_QR_SCAN', "hidden server QR scanner")
    require(settings, f'{MARKER}_FIXED_LIGHT_THEME', "hidden theme selector")
    require(settings, f'{MARKER}_BRANDING_LINKS', "Saurus mobile branding links")
    require_count(settings, 'if (false) /* Saurus: account disabled */', 2, "hidden account controls")
    require(settings, 'if (false) /* Saurus: deployment settings hidden */', "hidden deployment tool")

    theme = read(root / "flutter/lib/common.dart")
    require(theme, f'{MARKER}_GOLD', "Saurus gold theme")
    require(theme, f'{MARKER}_LIGHT_ONLY', "fixed light theme")

    manifest = read(root / "flutter/android/app/src/main/AndroidManifest.xml")
    for value, description in [
        ('android:label="Saurus Remote"', "application label"),
        ('android:label="Saurus Remote - Controle de entrada"', "accessibility service label"),
        ('android:name="br.com.saurus.remote.DEBUG_BOOT_COMPLETED"', "boot debug action"),
        ('android:scheme="saurusremote"', "deep link scheme"),
    ]:
        require(manifest, value, description)

    gradle = read(root / "flutter/android/app/build.gradle")
    require(gradle, f'applicationId "{cfg["application_id"]}"', "Android application ID")
    require(gradle, f'minSdkVersion {cfg["android_min_sdk"]}', "Android host minimum SDK")

    main_service = read(root / "flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/MainService.kt")
    for value, description in [
        ('DEFAULT_NOTIFY_TITLE = "Saurus Remote"', "notification title"),
        ('DEFAULT_NOTIFY_TEXT = "Acesso remoto ativo"', "notification text"),
        ('val channelId = "SaurusRemote"', "notification channel ID"),
        ('val channelName = "Saurus Remote"', "notification channel name"),
    ]:
        require(main_service, value, description)

    boot = read(root / "flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/BootReceiver.kt")
    require(boot, 'DEBUG_BOOT_COMPLETED = "br.com.saurus.remote.DEBUG_BOOT_COMPLETED"', "boot action")
    require(boot, '"Saurus Remote iniciado"', "boot notification")

    pubspec = read(root / "flutter/pubspec.yaml")
    require(pubspec, "description: Saurus Remote", "Flutter package description")

    for relative in [
        "mipmap-mdpi/ic_launcher.png",
        "mipmap-hdpi/ic_launcher.png",
        "mipmap-xhdpi/ic_launcher.png",
        "mipmap-xxhdpi/ic_launcher.png",
        "mipmap-xxxhdpi/ic_launcher.png",
        "mipmap-mdpi/ic_stat_logo.png",
        "mipmap-hdpi/ic_stat_logo.png",
        "mipmap-xhdpi/ic_stat_logo.png",
        "mipmap-xxhdpi/ic_stat_logo.png",
        "mipmap-xxxhdpi/ic_stat_logo.png",
    ]:
        path = root / "flutter/android/app/src/main/res" / relative
        if not path.is_file() or path.stat().st_size == 0:
            raise VerificationError(f"Branding file missing or empty: {path}")

    manifest_path = root / "SAURUS_ANDROID_CUSTOMIZATION.json"
    data = json.loads(read(manifest_path))
    if data.get("marker") != MARKER or data.get("mode") != "android-host-primary":
        raise VerificationError("Android customization manifest is invalid")

    # Block the most common encoding regressions in files changed by this kit.
    for relative in [
        "flutter/lib/mobile/pages/home_page.dart",
        "flutter/lib/mobile/pages/server_page.dart",
        "flutter/lib/models/server_model.dart",
        "flutter/lib/mobile/pages/settings_page.dart",
        "flutter/lib/common.dart",
        "flutter/android/app/src/main/AndroidManifest.xml",
        "flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/MainService.kt",
        "flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/BootReceiver.kt",
    ]:
        content = read(root / relative)
        for bad in ("\u00c3", "\u00e2\u20ac", "\u251c", "\u252c", "\ufffd"):
            if bad in content:
                raise VerificationError(f"Encoding corruption detected in {relative}: {bad}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        verify(args.source_root.resolve(), Path(__file__).resolve().parent)
        print("[OK] Saurus Remote Android host static verification passed")
        return 0
    except (VerificationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
