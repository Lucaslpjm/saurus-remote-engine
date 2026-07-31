#!/usr/bin/env python3
"""Static validation for the consolidated Saurus Remote Android build kit."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


class ValidationError(RuntimeError):
    pass


def read(path: Path) -> str:
    if not path.is_file():
        raise ValidationError(f"Required file missing: {path}")
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def require(content: str, marker: str, description: str) -> None:
    if marker not in content:
        raise ValidationError(f"Missing {description}: {marker}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(kit_root: Path, workflow_path: Path) -> None:
    required = [
        "config.json",
        "apply_saurus_android.py",
        "verify_saurus_android.py",
        "apply_saurus_android_ui_v2.py",
        "verify_saurus_android_ui_v2.py",
        "run_saurus_android_pipeline.py",
        "validate_android_pipeline_contracts.py",
        "validate_android_kit.py",
        "tests/test_apply_saurus_android.py",
        "assets/SHA256SUMS.txt",
        "assets/saurus_remote_logo.png",
    ]
    densities = ["mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"]
    for density in densities:
        required.extend(
            [
                f"assets/mipmap-{density}/ic_launcher.png",
                f"assets/mipmap-{density}/ic_stat_logo.png",
            ]
        )
    for relative in required:
        path = kit_root / relative
        if not path.is_file() or path.stat().st_size == 0:
            raise ValidationError(f"Required Android kit file missing or empty: {path}")

    config = json.loads(read(kit_root / "config.json"))
    expected_config = {
        "product_name": "Saurus Remote",
        "application_id": "br.com.saurus.remote",
        "rendezvous_server": "20.195.216.23:443",
        "default_access_password": "ophd0202",
    }
    for key, value in expected_config.items():
        if config.get(key) != value:
            raise ValidationError(f"Invalid config.json value for {key}: {config.get(key)!r}")

    manifest = read(kit_root / "assets/SHA256SUMS.txt")
    expected_hashes: dict[str, str] = {}
    for line in manifest.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(.+)", line)
        if not match:
            raise ValidationError(f"Invalid SHA256SUMS line: {line}")
        expected_hashes[match.group(2).replace("\\", "/")] = match.group(1).lower()
    for relative, expected in expected_hashes.items():
        path = kit_root / "assets" / relative
        if not path.is_file():
            raise ValidationError(f"Asset listed in SHA256SUMS is missing: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise ValidationError(f"Asset hash mismatch: {relative}: {actual} != {expected}")

    workflow = read(workflow_path)
    for marker in [
        'UPSTREAM_VERSION: "1.4.9"',
        'RUST_VERSION: "1.75"',
        'ANDROID_FLUTTER_VERSION: "3.24.5"',
        'NDK_VERSION: "r28c"',
        'CARGO_NDK_VERSION: "3.1.2"',
        'VCPKG_COMMIT_ID: "120deac3062162151622ca4860575a33844ba10b"',
        "validate-android-kit:",
        "build-native-libraries:",
        "package-android-apks:",
        "run_saurus_android_pipeline.py",
        "validate_android_pipeline_contracts.py",
        "--verify-idempotency",
        "dart format --output=none",
        "ET.parse(path)",
        "SaurusRemote-Android-",
        "SHA256SUMS.txt",
    ]:
        require(workflow, marker, "Android workflow contract")

    version_match = re.search(
        r"build_version:\s*\n(?:\s+[^\n]*\n){0,6}?\s+default:\s*[\"']([^\"']+)[\"']",
        workflow,
    )
    if not version_match or not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._-]{0,63}", version_match.group(1)):
        raise ValidationError("workflow_dispatch.build_version default is missing or invalid")

    for line_number, line in enumerate(workflow.splitlines(), start=1):
        match = re.search(r"\buses:\s*([^\s#]+)", line)
        if not match:
            continue
        ref = match.group(1)
        if ref.startswith("./"):
            continue
        if not re.search(r"@[0-9a-fA-F]{40}$", ref):
            raise ValidationError(f"GitHub Action is not pinned to a 40-char SHA at line {line_number}: {ref}")

    base_verify = read(kit_root / "verify_saurus_android.py")
    ui_verify = read(kit_root / "verify_saurus_android_ui_v2.py")
    ui_apply = read(kit_root / "apply_saurus_android_ui_v2.py")
    test = read(kit_root / "tests/test_apply_saurus_android.py")
    runner = read(kit_root / "run_saurus_android_pipeline.py")

    for marker in [
        'BASE_HOST_TITLE = \'final title = "Este dispositivo"\'',
        'FINAL_HOST_TITLE = \'final title = "Dispositivo"\'',
        'UI_V2_SERVER_MARKER = "SAURUS_ANDROID_UI_V2_SERVER"',
        "def expected_host_title(server_page: str)",
        "verify_host_title(server_page)",
    ]:
        require(base_verify, marker, "stage-aware host-title verifier")
    require(ui_verify, 'final title = "Dispositivo"', "final UI title verifier")
    require(test, "test_title_stage_contract", "base/final title regression test")
    require(test, "mismatched UI marker/title pair", "negative title-stage test")

    for marker in [
        "SAURUS_ANDROID_THEME_PATCH_V3",
        "def replace_dart_class_pair",
        "Dart class boundary self-test",
        "Theme variant self-test",
        "showSaurusInputPermissionGuide",
        "xml.etree.ElementTree as ET",
        "ACCESSIBILITY_DESCRIPTION",
    ]:
        require(ui_apply, marker, "robust Android UI patch")

    for manufacturer in ["Samsung", "Motorola", "Xiaomi", "One UI"]:
        if manufacturer in ui_apply:
            raise ValidationError(f"Manufacturer-specific guidance is forbidden: {manufacturer}")

    for marker in [
        "Android base host stage applied and verified",
        "Android final UI stage applied and verified",
        "Android pipeline idempotency verified",
    ]:
        require(runner, marker, "central Android pipeline")

    try:
        import yaml  # type: ignore

        parsed = yaml.safe_load(workflow)
        if not isinstance(parsed, dict) or not isinstance(parsed.get("jobs"), dict):
            raise ValidationError("Workflow YAML does not contain a jobs map")
    except ImportError:
        pass

    try:
        from PIL import Image  # type: ignore

        logo = kit_root / "assets/saurus_remote_logo.png"
        with Image.open(logo) as image:
            if image.width < 128 or image.height < 64:
                raise ValidationError(f"Saurus Android logo is unexpectedly small: {image.size}")
        for density in densities:
            for name in ["ic_launcher.png", "ic_stat_logo.png"]:
                with Image.open(kit_root / f"assets/mipmap-{density}/{name}") as image:
                    if image.width <= 0 or image.height <= 0:
                        raise ValidationError(f"Invalid image dimensions: {density}/{name}")
    except ImportError:
        pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kit-root", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate(args.kit_root.resolve(), args.workflow.resolve())
        print("[OK] Saurus Remote Android consolidated build kit validation passed")
        return 0
    except (ValidationError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
