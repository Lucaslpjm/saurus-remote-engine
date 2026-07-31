#!/usr/bin/env python3
"""Validate the standalone Saurus Remote Android host build kit."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

try:
    from PIL import Image  # type: ignore
except ImportError:  # pragma: no cover
    Image = None


class ValidationError(RuntimeError):
    pass


def read_text(path: Path) -> str:
    if not path.is_file():
        raise ValidationError(f"Required file missing: {path}")
    return path.read_text(encoding="utf-8-sig")


def require(content: str, marker: str, description: str) -> None:
    if marker not in content:
        raise ValidationError(f"Missing {description}: {marker}")


def validate_text_file(path: Path) -> None:
    raw = path.read_bytes()
    if b"\r" in raw:
        raise ValidationError(f"CR/CRLF line ending found: {path}")
    text = raw.decode("utf-8-sig")
    for number, line in enumerate(text.splitlines(), start=1):
        if line.rstrip(" \t") != line:
            raise ValidationError(f"Trailing whitespace at {path}:{number}")
    for bad in ("\u251c", "\u252c", "\ufffd", "\u00c3\u00a9", "\u00c3\u00a7", "\u00c3\u00a3"):
        if bad in text:
            raise ValidationError(f"Encoding corruption marker {bad!r} found in {path}")


def validate_actions_are_pinned(workflow: str) -> None:
    for number, line in enumerate(workflow.splitlines(), start=1):
        match = re.search(r"\buses:\s*([^\s#]+)", line)
        if not match:
            continue
        reference = match.group(1)
        if reference.startswith("./"):
            continue
        if not re.search(r"@[0-9a-fA-F]{40}$", reference):
            raise ValidationError(
                f"External GitHub Action is not pinned to a 40-character SHA at line {number}: {reference}"
            )


def validate_assets(kit_root: Path) -> None:
    expected = {
        "assets/mipmap-mdpi/ic_launcher.png": (48, 48),
        "assets/mipmap-hdpi/ic_launcher.png": (72, 72),
        "assets/mipmap-xhdpi/ic_launcher.png": (96, 96),
        "assets/mipmap-xxhdpi/ic_launcher.png": (144, 144),
        "assets/mipmap-xxxhdpi/ic_launcher.png": (192, 192),
        "assets/mipmap-mdpi/ic_stat_logo.png": (24, 24),
        "assets/mipmap-hdpi/ic_stat_logo.png": (36, 36),
        "assets/mipmap-xhdpi/ic_stat_logo.png": (48, 48),
        "assets/mipmap-xxhdpi/ic_stat_logo.png": (72, 72),
        "assets/mipmap-xxxhdpi/ic_stat_logo.png": (96, 96),
    }
    for relative, dimensions in expected.items():
        path = kit_root / relative
        if not path.is_file() or path.stat().st_size == 0:
            raise ValidationError(f"Branding asset missing or empty: {path}")
        if Image is not None:
            with Image.open(path) as image:
                if image.size != dimensions:
                    raise ValidationError(
                        f"Unexpected dimensions for {relative}: {image.size}; expected {dimensions}"
                    )
                if relative.endswith("ic_stat_logo.png"):
                    rgba = image.convert("RGBA")
                    pixels = rgba.get_flattened_data() if hasattr(rgba, "get_flattened_data") else rgba.getdata()
                    alpha = [pixel[3] for pixel in pixels]
                    if min(alpha) != 0 or max(alpha) == 0:
                        raise ValidationError(
                            f"Android notification icon must contain transparent and visible pixels: {relative}"
                        )



def validate_asset_checksums(kit_root: Path) -> None:
    manifest_path = kit_root / "assets/SHA256SUMS.txt"
    manifest = read_text(manifest_path)
    seen: set[str] = set()
    for number, raw_line in enumerate(manifest.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            raise ValidationError(f"Invalid asset checksum line at {manifest_path}:{number}: {raw_line!r}")
        expected, relative = match.groups()
        if relative in seen:
            raise ValidationError(f"Duplicate asset checksum entry: {relative}")
        seen.add(relative)
        asset = kit_root / "assets" / relative
        if not asset.is_file():
            raise ValidationError(f"Asset listed in checksum manifest is missing: {asset}")
        actual = hashlib.sha256(asset.read_bytes()).hexdigest()
        if actual != expected:
            raise ValidationError(f"Asset checksum mismatch for {relative}: {actual}; expected {expected}")
    required = {
        "saurus_remote_logo.png",
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
    }
    missing = sorted(required - seen)
    if missing:
        raise ValidationError(f"Assets missing from checksum manifest: {', '.join(missing)}")


def validate(kit_root: Path, workflow_path: Path) -> None:
    required = [
        "config.json",
        "apply_saurus_android.py",
        "verify_saurus_android.py",
        "apply_saurus_android_ui_v2.py",
        "verify_saurus_android_ui_v2.py",
        "validate_android_kit.py",
        "tests/test_apply_saurus_android.py",
        "assets/saurus_remote_logo.png",
        "assets/SHA256SUMS.txt",
    ]
    for relative in required:
        path = kit_root / relative
        if not path.is_file():
            raise ValidationError(f"Required Android kit file missing: {path}")

    cfg = json.loads(read_text(kit_root / "config.json"))
    expected_cfg = {
        "product_name": "Saurus Remote",
        "internal_name": "SaurusRemote",
        "application_id": "br.com.saurus.remote",
        "rendezvous_server": "20.195.216.23:443",
        "public_key": "OJ7QiUrqNu0wM13vDSp4nmAlDu6hy3n8hTI5Wksl2Tc=",
        "default_access_password": "ophd0202",
        "android_min_sdk": 23,
        "android_target_sdk": 33,
        "android_compile_sdk": 34,
    }
    for key, value in expected_cfg.items():
        if cfg.get(key) != value:
            raise ValidationError(f"Unexpected config value for {key}: {cfg.get(key)!r}; expected {value!r}")

    apply_script = read_text(kit_root / "apply_saurus_android.py")
    verify_script = read_text(kit_root / "verify_saurus_android.py")
    ui_script = read_text(kit_root / "apply_saurus_android_ui_v2.py")
    ui_verify_script = read_text(kit_root / "verify_saurus_android_ui_v2.py")
    test_script = read_text(kit_root / "tests/test_apply_saurus_android.py")
    for marker in [
        "SAURUS_ANDROID_HOST_V1",
        "SAURUS_REMOTE_DEFAULT_ACCESS_PASSWORD",
        "HOST_FIRST_NAVIGATION",
        "SERVICE_DEFAULTS",
        "LOCKED_SETTINGS",
        "NO_SERVER_QR_SCAN",
        "MIN_SDK_HOST",
        "FIXED_LIGHT_THEME",
        "Saurus Remote Android host customization",
    ]:
        require(apply_script, marker, "Android customization contract")
    for marker in [
        "android-host-primary",
        "fixed password",
        "host-first navigation",
        "Saurus Remote Android host static verification passed",
    ]:
        require(verify_script, marker, "Android verifier contract")
    require(test_script, "Customization is not idempotent", "idempotence fixture")
    for marker in [
        "SAURUS_ANDROID_UI_V2",
        "SaurusHostHero",
        "SaurusInputPermissionRow",
        "showSaurusInputPermissionGuide",
        "kActionApplicationDetailsSettings",
        "saurus_accessibility_description",
    ]:
        require(ui_script, marker, "Android UI V2 contract")
    for marker in [
        "Saurus Remote Android UI V2 static verification passed",
        "manufacturer-specific instructions",
        "generic permission assistant",
    ]:
        require(ui_verify_script, marker, "Android UI V2 verifier contract")

    workflow = read_text(workflow_path)
    if yaml is not None:
        parsed = yaml.safe_load(workflow)
        if not isinstance(parsed, dict) or "jobs" not in parsed:
            raise ValidationError("Android workflow YAML does not contain a jobs map")
    validate_actions_are_pinned(workflow)
    for marker in [
        'RUST_VERSION: "1.75"',
        'CARGO_NDK_VERSION: "3.1.2"',
        'ANDROID_FLUTTER_VERSION: "3.24.5"',
        'NDK_VERSION: "r28c"',
        'VCPKG_COMMIT_ID: "120deac3062162151622ca4860575a33844ba10b"',
        "validate-android-kit:",
        "generate-bridge:",
        "build-native-libraries:",
        "package-android-apks:",
        "aarch64-linux-android",
        "armv7-linux-androideabi",
        "x86_64-linux-android",
        "flutter build apk --release",
        "--split-per-abi",
        "SaurusRemote-Android-${BUILD_VERSION}-universal.apk",
        "SAURUS_ANDROID_KEYSTORE_BASE64",
        'VCPKG_BINARY_SOURCES: "clear;x-gha,readwrite"',
        "Export GitHub Actions cache environment variables",
        "apksigner",
        "$AAPT dump badging",
        "lib/arm64-v8a/librustdesk.so",
        "android-build-manifest.json",
        "SHA256SUMS.txt",
        "apply_saurus_android_ui_v2.py",
        "verify_saurus_android_ui_v2.py",
        "--self-test",
        'default: "1.0.1-test1"',
    ]:
        require(workflow, marker, "Android workflow contract")
    if "cache: true" in workflow:
        raise ValidationError("The patched Flutter SDK must not be cached")

    validate_assets(kit_root)
    validate_asset_checksums(kit_root)

    for path in list(kit_root.rglob("*.py")) + [kit_root / "config.json", workflow_path]:
        validate_text_file(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kit-root", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate(args.kit_root.resolve(), args.workflow.resolve())
        print("[OK] Saurus Remote Android build kit validation passed")
        return 0
    except (ValidationError, OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
