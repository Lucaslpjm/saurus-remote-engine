#!/usr/bin/env python3
"""Run the complete Saurus Remote Android customization as one contract.

The base host customization and the visual V2 layer are intentionally separate,
but every build must apply and verify them in the same order. Centralizing that
order prevents workflow jobs and unit tests from drifting apart.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

HERE = Path(__file__).resolve().parent


class PipelineError(RuntimeError):
    pass


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise PipelineError(f"Could not load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def changed_paths(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain=v1", "--untracked-files=all"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise PipelineError(f"git status failed: {result.stderr.strip()}")
    paths: list[Path] = []
    for raw in result.stdout.splitlines():
        if len(raw) < 4:
            continue
        relative = raw[3:]
        if " -> " in relative:
            relative = relative.split(" -> ", 1)[1]
        path = root / relative
        if path.is_file():
            paths.append(path)
    return sorted(set(paths))


def snapshot(paths: list[Path], root: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in paths:
        relative = path.relative_to(root).as_posix()
        values[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return values


def run(root: Path, version: str, verify_idempotency: bool) -> None:
    apply_base = load_module("saurus_apply_base", HERE / "apply_saurus_android.py")
    verify_base = load_module("saurus_verify_base", HERE / "verify_saurus_android.py")
    apply_ui = load_module("saurus_apply_ui", HERE / "apply_saurus_android_ui_v2.py")
    verify_ui = load_module("saurus_verify_ui", HERE / "verify_saurus_android_ui_v2.py")

    apply_base.apply(root, HERE, version)
    verify_base.verify(root, HERE)
    print("[OK] Android base host stage applied and verified", flush=True)

    apply_ui.apply_ui_v2(root)
    verify_base.verify(root, HERE)
    verify_ui.verify_ui_v2(root)
    print("[OK] Android final UI stage applied and verified", flush=True)

    if verify_idempotency:
        paths_before = changed_paths(root)
        state_before = snapshot(paths_before, root)
        apply_base.apply(root, HERE, version)
        apply_ui.apply_ui_v2(root)
        verify_base.verify(root, HERE)
        verify_ui.verify_ui_v2(root)
        paths_after = changed_paths(root)
        state_after = snapshot(paths_after, root)
        if [p.relative_to(root).as_posix() for p in paths_before] != [
            p.relative_to(root).as_posix() for p in paths_after
        ]:
            raise PipelineError("The second pass changed the set of customized files")
        if state_before != state_after:
            changed = sorted(k for k in state_before if state_before.get(k) != state_after.get(k))
            raise PipelineError(f"Android customization is not idempotent: {changed}")
        print(f"[OK] Android pipeline idempotency verified across {len(state_after)} files", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--verify-idempotency", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        run(args.source_root.resolve(), args.version, args.verify_idempotency)
        print(f"[OK] Saurus Remote Android pipeline completed: {args.version}", flush=True)
        return 0
    except Exception as exc:  # diagnostic boundary for GitHub Actions
        print(f"[FAIL] {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
