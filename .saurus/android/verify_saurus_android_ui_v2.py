#!/usr/bin/env python3
"""Verify the Saurus Remote Android UI V2 customization."""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

MARKER = "SAURUS_ANDROID_UI_V2"
ANDROID_NAMESPACE = "http://schemas.android.com/apk/res/android"


class UiVerificationError(RuntimeError):
    pass


def read(path: Path) -> str:
    if not path.is_file():
        raise UiVerificationError(f"Required file missing: {path}")
    return path.read_text(encoding="utf-8-sig")


def require(content: str, marker: str, description: str) -> None:
    if marker not in content:
        raise UiVerificationError(f"Missing {description}: {marker}")


def forbid(content: str, marker: str, description: str) -> None:
    if marker in content:
        raise UiVerificationError(f"Forbidden {description}: {marker}")


def verify_ui_v2(root: Path) -> None:
    home = read(root / "flutter/lib/mobile/pages/home_page.dart")
    for marker, description in [
        (f"{MARKER}_HOME", "custom mobile scaffold"),
        (f"{MARKER}_HEADER", "Saurus header"),
        ("assets/saurus_remote_android_logo.png", "header logo"),
        ("backgroundColor: const Color(0xFF14213D)", "navy AppBar"),
        ("selectedItemColor: const Color(0xFFD8B62A)", "gold navigation"),
        ("return 'Conex\\u00f5es';", "compact connections label"),
    ]:
        require(home, marker, description)
    forbid(home, "return Text(bind.mainGetAppNameSync());", "unbranded mobile header")

    server = read(root / "flutter/lib/mobile/pages/server_page.dart")
    for marker, description in [
        ('final title = "Dispositivo"', "final compact host page title"),
        (f"{MARKER}_SERVER", "server page marker"),
        (f"{MARKER}_GUIDED_INPUT", "guided input permission"),
        ("class SaurusHostHero", "host hero card"),
        ("class SaurusInputPermissionRow", "input permission action card"),
        ("showSaurusInputPermissionGuide", "generic permission assistant"),
        ("kActionApplicationDetailsSettings", "app details shortcut"),
        ("Abrir acessibilidade", "accessibility action"),
        ("Configura\\u00e7\\u00e3o restrita", "generic restricted-settings guidance"),
        ("Compartilhe este dispositivo com seguran\\u00e7a.", "host safety message"),
        ("borderRadius: BorderRadius.circular(18)", "modern card radius"),
    ]:
        require(server, marker, description)
    for forbidden in [
        "Samsung",
        "Motorola",
        "Xiaomi",
        "One UI",
    ]:
        forbid(server, forbidden, "manufacturer-specific instructions")

    settings = read(root / "flutter/lib/mobile/pages/settings_page.dart")
    require(settings, f"{MARKER}_SETTINGS_TITLE", "localized settings title")

    common = read(root / "flutter/lib/common.dart")
    for marker, description in [
        (f"{MARKER}_THEME", "Saurus light background"),
        ("primary: Color(0xFF14213D)", "navy primary color"),
        ("secondary: Color(0xFFD8B62A)", "gold secondary color"),
        ("cardColor: Colors.white", "white cards"),
    ]:
        require(common, marker, description)

    manifest_path = root / "flutter/android/app/src/main/AndroidManifest.xml"
    config_path = root / "flutter/android/app/src/main/res/xml/accessibility_service_config.xml"
    strings_path = root / "flutter/android/app/src/main/res/values/saurus_accessibility_strings.xml"

    manifest = read(manifest_path)
    accessibility = read(config_path)
    strings = read(strings_path)
    require(manifest, f"{MARKER}_ACCESSIBILITY_METADATA", "accessibility metadata marker")
    require(accessibility, f"{MARKER}_ACCESSIBILITY_DESCRIPTION", "accessibility config marker")
    if manifest.count(f"{MARKER}_ACCESSIBILITY_METADATA") != 1:
        raise UiVerificationError("Accessibility manifest marker must occur exactly once")
    if accessibility.count(f"{MARKER}_ACCESSIBILITY_DESCRIPTION") != 1:
        raise UiVerificationError("Accessibility config marker must occur exactly once")

    try:
        manifest_root = ET.parse(manifest_path).getroot()
        config_root = ET.parse(config_path).getroot()
        strings_root = ET.parse(strings_path).getroot()
    except ET.ParseError as exc:
        raise UiVerificationError(f"Invalid customized Android XML: {exc}") from exc

    android_permission = f"{{{ANDROID_NAMESPACE}}}permission"
    android_description = f"{{{ANDROID_NAMESPACE}}}description"
    android_icon = f"{{{ANDROID_NAMESPACE}}}icon"
    services = [
        item
        for item in manifest_root.iter("service")
        if item.get(android_permission) == "android.permission.BIND_ACCESSIBILITY_SERVICE"
    ]
    if len(services) != 1:
        raise UiVerificationError(
            f"Expected one accessibility service in AndroidManifest.xml, found {len(services)}"
        )
    service = services[0]
    if service.get(android_description) != "@string/saurus_accessibility_description":
        raise UiVerificationError("Accessibility service description is not the Saurus resource")
    if service.get(android_icon) != "@mipmap/ic_launcher":
        raise UiVerificationError("Accessibility service icon is not the Saurus launcher icon")

    if config_root.tag != "accessibility-service":
        raise UiVerificationError(f"Unexpected accessibility config root: {config_root.tag}")
    if config_root.get(android_description) != "@string/saurus_accessibility_description":
        raise UiVerificationError("Accessibility config description is not the Saurus resource")

    descriptions = [
        item
        for item in strings_root.findall("string")
        if item.get("name") == "saurus_accessibility_description"
    ]
    if len(descriptions) != 1:
        raise UiVerificationError(
            f"Expected one Saurus accessibility string, found {len(descriptions)}"
        )
    description_text = descriptions[0].text or ""
    require(description_text, "Saurus Remote", "Saurus accessibility description")
    require(description_text, "sessao de suporte remoto autorizada", "permission purpose disclosure")

    for relative in [
        "flutter/lib/mobile/pages/home_page.dart",
        "flutter/lib/mobile/pages/server_page.dart",
        "flutter/lib/mobile/pages/settings_page.dart",
        "flutter/lib/common.dart",
        "flutter/android/app/src/main/AndroidManifest.xml",
        "flutter/android/app/src/main/res/xml/accessibility_service_config.xml",
        "flutter/android/app/src/main/res/values/saurus_accessibility_strings.xml",
    ]:
        content = read(root / relative)
        for bad in ("\u251c", "\u252c", "\ufffd", "\u00c3"):
            if bad in content:
                raise UiVerificationError(f"Encoding corruption in {relative}: {bad!r}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        verify_ui_v2(args.source_root.resolve())
        print("[OK] Saurus Remote Android UI V2 static verification passed")
        return 0
    except (UiVerificationError, OSError, UnicodeError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
