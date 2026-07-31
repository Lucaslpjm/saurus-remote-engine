#!/usr/bin/env python3
"""Cross-file contracts for the Saurus Remote Android build pipeline."""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class ContractError(RuntimeError):
    pass


def read(path: Path) -> str:
    if not path.is_file():
        raise ContractError(f"Required file missing: {path}")
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def require(content: str, marker: str, description: str) -> None:
    if marker not in content:
        raise ContractError(f"Missing {description}: {marker}")




def validate_py_compile_block(workflow: str) -> None:
    match = re.search(
        r"python -m py_compile \\\n(?P<body>(?:\s+[^\n]+\n)+?)\s+python \.saurus/android/validate_android_kit\.py",
        workflow,
    )
    if not match:
        raise ContractError("Could not locate the Python compilation block in the Android workflow")
    lines = [line.strip() for line in match.group("body").splitlines() if line.strip()]
    expected = [
        ".saurus/android/apply_saurus_android.py",
        ".saurus/android/verify_saurus_android.py",
        ".saurus/android/apply_saurus_android_ui_v2.py",
        ".saurus/android/verify_saurus_android_ui_v2.py",
        ".saurus/android/run_saurus_android_pipeline.py",
        ".saurus/android/validate_android_pipeline_contracts.py",
        ".saurus/android/validate_android_kit.py",
        ".saurus/android/tests/test_apply_saurus_android.py",
    ]
    actual: list[str] = []
    for index, line in enumerate(lines):
        has_continuation = line.endswith("\\")
        value = line[:-1].rstrip() if has_continuation else line
        actual.append(value)
        if index < len(lines) - 1 and not has_continuation:
            raise ContractError(f"Missing line continuation in py_compile block: {line}")
        if index == len(lines) - 1 and has_continuation:
            raise ContractError("The final py_compile file must not end with a line continuation")
    if actual != expected:
        raise ContractError(f"Unexpected py_compile file list: {actual}")


def validate_bash_run_blocks(workflow: str) -> None:
    try:
        import yaml  # type: ignore
    except ImportError:
        return
    bash = shutil.which("bash")
    if bash is None:
        return
    parsed = yaml.safe_load(workflow)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("jobs"), dict):
        raise ContractError("Workflow YAML does not contain a jobs map")
    expression = re.compile(r"\$\{\{.*?\}\}")
    for job_name, job in parsed["jobs"].items():
        if not isinstance(job, dict):
            continue
        for index, step in enumerate(job.get("steps", [])):
            if not isinstance(step, dict) or step.get("shell") != "bash" or "run" not in step:
                continue
            script = expression.sub("GH_EXPR", str(step["run"]))
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", suffix=".sh", delete=False) as handle:
                handle.write(script)
                path = Path(handle.name)
            try:
                result = subprocess.run([bash, "-n", str(path)], capture_output=True, text=True, encoding="utf-8")
            finally:
                path.unlink(missing_ok=True)
            if result.returncode != 0:
                name = step.get("name", f"step {index + 1}")
                raise ContractError(
                    f"Bash syntax error in {job_name}/{name}: {result.stderr.strip()}"
                )


def validate(repo_root: Path) -> None:
    android = repo_root / ".saurus/android"
    workflow = read(repo_root / ".github/workflows/build-saurus-remote-android.yml")
    base_verify = read(android / "verify_saurus_android.py")
    ui_verify = read(android / "verify_saurus_android_ui_v2.py")
    base_test = read(android / "tests/test_apply_saurus_android.py")
    runner = read(android / "run_saurus_android_pipeline.py")

    for marker in [
        'BASE_HOST_TITLE = \'final title = "Este dispositivo"\'',
        'FINAL_HOST_TITLE = \'final title = "Dispositivo"\'',
        'UI_V2_SERVER_MARKER = "SAURUS_ANDROID_UI_V2_SERVER"',
        "def expected_host_title(server_page: str)",
        "verify_host_title(server_page)",
    ]:
        require(base_verify, marker, "stage-aware base verifier contract")

    require(ui_verify, 'final title = "Dispositivo"', "final UI title contract")
    require(base_test, "test_title_stage_contract", "title-stage regression test")
    require(base_test, "SAURUS_ANDROID_UI_V2_SERVER", "final-stage test marker")

    require(runner, "Android base host stage applied and verified", "base pipeline stage")
    require(runner, "Android final UI stage applied and verified", "final pipeline stage")
    require(runner, "Android pipeline idempotency verified", "idempotency gate")

    call = "python .saurus/android/run_saurus_android_pipeline.py"
    call_count = workflow.count(call)
    if call_count != 3:
        raise ContractError(f"Expected 3 centralized pipeline calls in workflow, found {call_count}")
    if workflow.count("--verify-idempotency") != 1:
        raise ContractError("The validation job must run exactly one idempotency check")

    validate_py_compile_block(workflow)
    validate_bash_run_blocks(workflow)

    for marker in [
        "timeout-minutes: 20",
        "timeout-minutes: 120",
        "timeout-minutes: 75",
        "Release signing configuration validated",
        "Could not locate the Android signingConfig contract",
        "Expected exactly 4 generated APKs",
        "org.gradle.jvmargs=-Xmx3g",
        "Parse customized Dart and Android XML files",
        "dart format --output=none",
        "ET.parse(path)",
    ]:
        require(workflow, marker, "hardened Android workflow contract")

    for forbidden in [
        "python .saurus/android/apply_saurus_android.py \\",
        "python .saurus/android/apply_saurus_android_ui_v2.py --source-root",
        "python .saurus/android/verify_saurus_android.py --source-root",
        "python .saurus/android/verify_saurus_android_ui_v2.py --source-root",
    ]:
        if forbidden in workflow:
            raise ContractError(f"Legacy direct pipeline command remains in workflow: {forbidden}")

    match = re.search(
        r"build_version:\s*\n(?:\s+[^\n]*\n){0,6}?\s+default:\s*[\"']([^\"']+)[\"']",
        workflow,
    )
    if not match or not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._-]{0,63}", match.group(1)):
        raise ContractError("workflow_dispatch.build_version does not have a valid semantic default")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate(args.repo_root.resolve())
        print("[OK] Saurus Remote Android cross-file pipeline contracts passed")
        return 0
    except (ContractError, OSError, UnicodeError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
