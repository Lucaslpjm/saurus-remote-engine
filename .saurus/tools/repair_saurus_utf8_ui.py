#!/usr/bin/env python3
"""Repair UTF-8 text that was accidentally decoded as CP850.

The bug is visible as sequences such as ``Servi\u251c\u00bao``.  The tool repairs
only lines that contain the CP850 box-drawing marker, writes UTF-8/LF and then
fails if a known mojibake marker remains in the Saurus UX sources or Dart UI.
"""
from __future__ import annotations

import argparse
from pathlib import Path

MOJIBAKE_MARKERS = ("\u251c", "\u252c", "\ufffd")
SOURCE_RELATIVE = (
    ".saurus/tools/apply_saurus_ux_refresh.py",
    ".saurus/tools/verify_saurus_ux_refresh.py",
    ".saurus/tools/optimize_saurus_workflow.py",
    ".saurus/tests/test_ux_refresh.py",
)


def score(value: str) -> int:
    return sum(value.count(marker) for marker in MOJIBAKE_MARKERS)


def repair_line(line: str) -> str:
    if score(line) == 0:
        return line
    try:
        candidate = line.encode("cp850", errors="strict").decode("utf-8", errors="strict")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return line
    return candidate if score(candidate) < score(line) else line


def repair_file(path: Path) -> bool:
    raw = path.read_text(encoding="utf-8-sig", errors="strict")
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    repaired = "\n".join(repair_line(line).rstrip(" \t") for line in normalized.split("\n"))
    repaired = repaired.rstrip("\n") + "\n"
    if repaired != raw:
        path.write_text(repaired, encoding="utf-8", newline="\n")
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    args = parser.parse_args()

    root = Path(args.source_root).resolve()
    candidates: list[Path] = []
    for relative in SOURCE_RELATIVE:
        path = root / relative
        if path.is_file():
            candidates.append(path)

    flutter_root = root / "flutter" / "lib"
    if flutter_root.is_dir():
        candidates.extend(sorted(flutter_root.rglob("*.dart")))

    changed = 0
    for path in candidates:
        if repair_file(path):
            changed += 1
            print(f"[OK] UTF-8 reparado: {path.relative_to(root)}")

    failures: list[str] = []
    for path in candidates:
        content = path.read_text(encoding="utf-8-sig", errors="strict")
        remaining = [marker for marker in MOJIBAKE_MARKERS if marker in content]
        if remaining:
            failures.append(f"{path.relative_to(root)} ainda contem marcadores de mojibake")

    if failures:
        for failure in failures:
            print(f"[ERRO] {failure}")
        return 1

    print(f"[OK] Validacao UTF-8 concluida; arquivos ajustados: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
