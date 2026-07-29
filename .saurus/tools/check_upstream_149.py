#!/usr/bin/env python3
"""Preflight de compatibilidade para o fonte RustDesk 1.4.9.

Executa antes da customizacao. Confere que os pontos alterados pelo kit ainda
correspondem ao upstream esperado e falha explicitamente quando houver desvio.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    path: str
    pattern: str
    description: str
    regex: bool = False
    expected_count: int = 1


def read(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo upstream ausente: {relative}")
    return path.read_text(encoding="utf-8-sig", errors="strict")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    args = parser.parse_args()
    root = Path(args.source_root).resolve()

    checks = [
        Check("Cargo.toml", r'^version\s*=\s*"1\.4\.9"\s*$', "versao 1.4.9", True),
        Check("libs/hbb_common/src/config.rs", 'RwLock::new("RustDesk".to_owned())', "nome interno upstream"),
        Check("src/core_main.rs", '} else if args[0] == "--password" {', "CLI de senha upstream"),
        Check("src/core_main.rs", '} else if args[0] == "--update" {', "atualizador upstream"),
        Check("src/core_main.rs", '&crate::get_app_name(),', "titulo de despacho upstream"),
        Check("src/platform/windows.rs", 'const IS1: &str = "{54E86BC2-6C85-41F3-A9EB-1A94AC9B1F93}_is1";', "chave Inno upstream"),
        Check("src/platform/windows.rs", '.join("RustDeskCustomClientStaging")', "staging upstream"),
        Check("src/platform/windows.rs", 'if file_name.starts_with("rustdesk-")', "prefixo de temporarios upstream"),
        Check("src/platform/windows.rs", 'let caption = "RustDesk Output"', "titulo nativo upstream"),
        Check("src/platform/windows.rs", 'format!("{}\\\\{}", pf, crate::get_app_name())', "caminho de instalacao upstream"),
        Check("src/platform/windows.rs", 'DisplayName= \\"{app_name} Service\\"', "nome visual do servico upstream", expected_count=2),
        Check("src/privacy_mode/win_topmost_window.rs", '"RuntimeBroker_rustdesk.exe"', "broker de privacidade upstream"),
        Check("src/privacy_mode/win_topmost_window.rs", '"RustDeskPrivacyWindowClass"', "classe de privacidade upstream"),
        Check("src/privacy_mode/win_topmost_window.rs", '"RustDeskPrivacyWindow"', "janela de privacidade upstream"),
        Check("src/flutter_ffi.rs", 'pub fn main_get_app_name() -> String {', "FFI de nome visual"),
        Check("flutter/windows/runner/main.cpp", 'std::wstring app_name = L"RustDesk";', "fallback do titulo Windows"),
        Check("flutter/windows/runner/Runner.rc", 'VALUE "ProductName", "RustDesk"', "metadados Windows"),
        Check("flutter/lib/common.dart", 'static const Color accent = Color(0xFF0071FF);', "tema upstream"),
        Check("flutter/lib/desktop/widgets/remote_toolbar.dart", 'final List<Widget> toolbarItems = [];', "barra remota upstream"),
        Check("flutter/lib/desktop/widgets/remote_toolbar.dart", 'toolbarItems.add(_PinMenu(state: widget.state));', "pino da barra remota"),
        Check("flutter/pubspec.yaml", 'description: Your Remote Desktop Software', "descricao Flutter upstream"),
    ]

    failures: list[str] = []
    cache: dict[str, str] = {}
    for check in checks:
        try:
            content = cache.setdefault(check.path, read(root, check.path))
        except Exception as exc:
            failures.append(str(exc))
            continue
        count = (
            len(re.findall(check.pattern, content, flags=re.MULTILINE | re.DOTALL))
            if check.regex
            else content.count(check.pattern)
        )
        if count != check.expected_count:
            failures.append(
                f"{check.description}: esperado {check.expected_count}, encontrado {count} em {check.path}"
            )
        else:
            print(f"[OK] {check.description}")

    if failures:
        print("\nPreflight upstream REPROVADO:", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1

    print("\nPreflight upstream APROVADO para RustDesk 1.4.9.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
