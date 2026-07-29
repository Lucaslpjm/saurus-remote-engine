#!/usr/bin/env python3
"""Static verification for the Saurus Remote 3.1.2 UX refresh."""
from __future__ import annotations

import argparse
from pathlib import Path


def require(text: str, value: str, label: str, errors: list[str]) -> None:
    if value not in text:
        errors.append(f"Missing {label}: {value}")
    else:
        print(f"[OK] {label}")


def forbid(text: str, value: str, label: str, errors: list[str]) -> None:
    if value in text:
        errors.append(f"Forbidden {label} still present: {value}")
    else:
        print(f"[OK] {label} removed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    args = parser.parse_args()
    root = Path(args.source_root).resolve()

    paths = {
        "home": root / "flutter/lib/desktop/pages/desktop_home_page.dart",
        "connection": root / "flutter/lib/desktop/pages/connection_page.dart",
        "main": root / "flutter/windows/runner/main.cpp",
    }
    errors: list[str] = []
    for label, path in paths.items():
        if not path.is_file():
            errors.append(f"Required file not found ({label}): {path}")
    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return 1

    home = paths["home"].read_text(encoding="utf-8")
    connection = paths["connection"].read_text(encoding="utf-8")
    main_cpp = paths["main"].read_text(encoding="utf-8")

    for value, label in [
        ("SAURUS_UX_REFRESH_3_1", "UX refresh marker"),
        ("_buildSaurusDashboard", "responsive dashboard"),
        ("constraints.maxWidth < 760 || constraints.maxHeight < 540", "small-screen breakpoint"),
        ("compactNavigation", "compact navigation"),
        ("Histórico e sessões recentes", "full-width history section"),
        ("Conectar a outro dispositivo", "separate connection section"),
        ("_buildSaurusDiagnosticsPage", "dedicated diagnostics page"),
        ("_runSaurusDiagnostics", "diagnostics runner"),
        ("Socket.connect", "server port test"),
        ("InternetAddress.lookup", "internet/DNS test"),
        ("Copiar relatório", "diagnostic report copy"),
        ("kRemoteViewStyleAdaptive", "adaptive scale factory default"),
        ("kOptionDisableAudio", "audio disabled factory default"),
        ("mainGetUserDefaultOption", "read user defaults"),
        ("mainSetUserDefaultOption", "write user defaults"),
        ("_saurusConfiguredServer", "configured diagnostics server"),
        ("if (disableAudio.isEmpty)", "preserve later audio preference"),
        ("if (viewStyle.isEmpty)", "preserve later scale preference"),
        ("unawaited(_ensureSaurusFactoryDefaults());", "factory defaults initialization"),
        ("showConnect: true", "connection-only mode usage"),
        ("showConnect: false", "history-only mode usage"),
        ("showStatus: false", "dashboard status duplication disabled"),
    ]:
        require(home, value, label, errors)

    # Validate only the refreshed Saurus block for removed dashboard duplication.
    start = home.find("// SAURUS_UX_REFRESH_3_1")
    end = home.find("  Widget _buildBlock({required Widget child})", start)
    saurus_block = home[start:end] if start >= 0 and end > start else home
    for value, label in [
        ("Diagnóstico rápido", "quick diagnostics dashboard card"),
        ("Status do servidor", "server status duplication"),
        ("Configurações de rede", "network button duplication"),
        ("_buildSaurusDiagnosticsCard", "old quick diagnostics method"),
    ]:
        forbid(saurus_block, value, label, errors)

    for value, label in [
        ("final bool showConnect;", "ConnectionPage connect mode"),
        ("final bool showPeers;", "ConnectionPage peers mode"),
        ("final bool showStatus;", "ConnectionPage status mode"),
        ("if (widget.showConnect)", "conditional connection initialization"),
        ("if (widget.showPeers)", "conditional peer history"),
        ("if (widget.showStatus && !isOutgoingOnly)", "conditional status footer"),
    ]:
        require(connection, value, label, errors)

    for value, label in [
        ("SAURUS_UX_REFRESH_3_1_WINDOW", "window sizing marker"),
        ("Win32Window::Size size(1180u, 780u);", "larger default window"),
        ("Win32Desktop::FitToWorkArea(origin, size);", "small-monitor work-area fitting"),
    ]:
        require(main_cpp, value, label, errors)
    forbid(main_cpp, "Win32Window::Size size(800u, 600u);", "old default size", errors)

    if errors:
        print("\nSaurus UX refresh validation failed:")
        for error in errors:
            print(f" - {error}")
        return 1

    print("\n[OK] Saurus Remote UX refresh 3.1.2 static validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
