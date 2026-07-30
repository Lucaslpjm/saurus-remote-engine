#!/usr/bin/env python3
"""Integrate UX refresh checks and low-risk build speed improvements into the workflow."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True)
    args = parser.parse_args()
    path = Path(args.workflow).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")

    if "group: saurus-remote-windows-x64" not in text:
        permissions_pattern = r"permissions:\s*\n\s+contents: read\s*\n"
        replacement = (
            "permissions:\n"
            "  contents: read\n\n"
            "# Avoid spending runner minutes on an obsolete manual build of the same label.\n"
            "concurrency:\n"
            "  group: saurus-remote-windows-x64-${{ github.ref }}-${{ inputs.build_label }}\n"
            "  cancel-in-progress: true\n"
        )
        text, count = re.subn(permissions_pattern, replacement, text, count=1)
        if count != 1:
            raise RuntimeError("Could not insert workflow concurrency block")

    # A full history is not required by this reproducible, tag-pinned build.
    text = text.replace("fetch-depth: 0", "fetch-depth: 1")

    if "Apply Saurus UX refresh" not in text:
        marker = "      - name: Verify Saurus customization and secret policy\n"
        pos = text.find(marker)
        if pos < 0:
            raise RuntimeError("Existing Saurus verification step was not found")
        step = (
            "      - name: Apply Saurus UX refresh\n"
            "        shell: pwsh\n"
            "        run: |\n"
            "          python .\\.saurus\\tests\\test_ux_refresh.py\n"
            "          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n"
            "          python .\\.saurus\\tools\\apply_saurus_ux_refresh.py --source-root .\n"
            "          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n\n"
        )
        text = text[:pos] + step + text[pos:]

    if "Verify Saurus UX refresh" not in text:
        next_marker = "      - name: Restore generated Flutter-Rust bridge\n"
        pos = text.find(next_marker)
        if pos < 0:
            raise RuntimeError("Bridge restore step was not found")
        step = (
            "      - name: Verify Saurus UX refresh\n"
            "        shell: pwsh\n"
            "        run: |\n"
            "          python .\\.saurus\\tools\\verify_saurus_ux_refresh.py --source-root .\n"
            "          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n\n"
        )
        text = text[:pos] + step + text[pos:]

    # Cache only Dart/Flutter package dependencies. The SDK itself is modified later
    # by the RustDesk engine and dropdown patches, so caching the whole SDK would risk
    # restoring a partially modified toolchain on a future build.
    flutter_step = re.search(
        r"      - name: Install Flutter\n(?:(?!      - name:).)*?          architecture: x64\n",
        text,
        flags=re.DOTALL,
    )
    if flutter_step:
        next_step = text.find("\n      - name:", flutter_step.end())
        if next_step < 0:
            next_step = len(text)
        flutter_block = text[flutter_step.start():next_step]
        block = flutter_step.group(0)
        block = block.replace("          cache: true\n", "")
        if "pub-cache: true" not in flutter_block:
            block = block.replace(
                "          architecture: x64\n",
                "          architecture: x64\n          pub-cache: true\n",
                1,
            )
        text = text[: flutter_step.start()] + block + text[flutter_step.end() :]

    # flutter doctor is useful interactively but comparatively slow and noisy in every CI run.
    text = text.replace("          flutter doctor -v\n", "          flutter --version\n")

    if "Format refreshed Flutter sources" not in text:
        marker = "      - name: Install Rust toolchain\n"
        pos = text.find(marker)
        if pos < 0:
            raise RuntimeError("Rust toolchain step was not found")
        step = (
            "      - name: Format refreshed Flutter sources\n"
            "        shell: pwsh\n"
            "        run: |\n"
            "          dart format .\\flutter\\lib\\desktop\\pages\\desktop_home_page.dart .\\flutter\\lib\\desktop\\pages\\connection_page.dart\n"
            "          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n"
            "          python .\\.saurus\\tools\\verify_saurus_ux_refresh.py --source-root .\n"
            "          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n\n"
        )
        text = text[:pos] + step + text[pos:]

    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"[OK] Workflow optimized: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
