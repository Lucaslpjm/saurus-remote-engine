#!/usr/bin/env python3
# SAURUS_REMOTE_FINAL_UI_NORMALIZER_V2
# SAURUS_REMOTE_FINAL_UI_NORMALIZER_V3
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

DEVICE_LABEL = "Este dispositivo"
CONNECT_LABEL = "Conectar a outro dispositivo"
HISTORY_LABEL = "Hist\u00f3rico e sess\u00f5es recentes"
FINAL_MARKER = "// SAURUS_REMOTE_PRODUCTION_UI_FINAL"

OLD_CONNECTION_LABELS = (
    "Conectar e acessar sessoes recentes",
    "Conectar e acessar sess\u00f5es recentes",
    "Conectar e acessar sess\u00c3\u00b5es recentes",
)
HISTORY_LABEL_VARIANTS = (
    "Historico e sessoes recentes",
    "Hist\u00c3\u00b3rico e sess\u00c3\u00b5es recentes",
)
FORBIDDEN_LABELS = (
    "Diagnostico rapido",
    "Diagn\u00f3stico r\u00e1pido",
    "Configuracoes de rede",
    "Configura\u00e7\u00f5es de rede",
)
MOJIBAKE_CHARS = ("\u251c", "\u252c", "\ufffd")
STALE_MARKER_RE = re.compile(
    r"(?m)^//\s*(?:"
    r"SAURUS_REMOTE_" r"PRODUCTION_UI_2026_07(?:_V\d+)?|"
    r"SAURUS_REMOTE_" r"FINAL_UI_3_2_3(?:_\d+)*"
    r")\s*\n?"
)


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def finalize_text(text: str) -> str:
    result = normalize_newlines(text)
    result = STALE_MARKER_RE.sub("", result)
    for old_label in OLD_CONNECTION_LABELS:
        result = result.replace(old_label, CONNECT_LABEL)
    for old_label in HISTORY_LABEL_VARIANTS:
        result = result.replace(old_label, HISTORY_LABEL)

    if FINAL_MARKER not in result:
        class_token = "class DesktopHomePage"
        if result.count(class_token) != 1:
            raise RuntimeError(
                "Classe DesktopHomePage nao foi localizada de forma unica."
            )
        result = result.replace(class_token, FINAL_MARKER + "\n" + class_token, 1)

    return result.rstrip("\n") + "\n"


def validate_text(text: str) -> list[str]:
    failures: list[str] = []
    for old_label in OLD_CONNECTION_LABELS:
        if old_label in text:
            failures.append(f"Rotulo legado ainda presente: {old_label}")
    for old_label in HISTORY_LABEL_VARIANTS:
        if old_label in text:
            failures.append(f"Rotulo de historico nao normalizado: {old_label}")
    for forbidden in FORBIDDEN_LABELS:
        if forbidden in text:
            failures.append(f"Elemento antigo ainda presente: {forbidden}")
    for required in (DEVICE_LABEL, CONNECT_LABEL, HISTORY_LABEL, FINAL_MARKER):
        if required not in text:
            failures.append(f"Marcador obrigatorio ausente: {required}")
    if text.count(FINAL_MARKER) != 1:
        failures.append("O marcador final deve aparecer exatamente uma vez.")
    if STALE_MARKER_RE.search(text):
        failures.append("Marcador final versionado ainda presente.")
    for char in MOJIBAKE_CHARS:
        if char in text:
            failures.append(
                f"Caractere corrompido detectado: U+{ord(char):04X}"
            )
    return failures


def self_test() -> int:
    sample = (
        "// SAURUS_REMOTE_" "FINAL_UI_3_2_3_2\n"
        "class DesktopHomePage {\n"
        "final a = 'Este dispositivo';\n"
        "final b = 'Conectar e acessar sess\\u00f5es recentes';\n"
        "final c = 'Historico e sessoes recentes';\n"
        "}\n"
    ).encode("ascii").decode("unicode_escape")
    final = finalize_text(sample)
    failures = validate_text(final)
    if failures:
        for item in failures:
            print(f"[ERRO] {item}", file=sys.stderr)
        return 1
    print("[OK] Autoteste do marcador final estavel concluido.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if not args.source_root:
        parser.error("--source-root e obrigatorio fora do autoteste")

    root = Path(args.source_root).resolve()
    home_page = (
        root
        / "flutter"
        / "lib"
        / "desktop"
        / "pages"
        / "desktop_home_page.dart"
    )
    if not home_page.is_file():
        print(f"Arquivo nao encontrado: {home_page}", file=sys.stderr)
        return 1

    try:
        original = home_page.read_text(encoding="utf-8-sig")
        final = finalize_text(original)
    except Exception as exc:
        print(f"Falha ao preparar interface final: {exc}", file=sys.stderr)
        return 1

    failures = validate_text(final)
    if failures:
        for item in failures:
            print(f"[ERRO] {item}", file=sys.stderr)
        return 1

    if not args.check_only and final != original:
        home_page.write_text(final, encoding="utf-8", newline="\n")
        print(f"[OK] Interface finalizada: {home_page}")
    else:
        print("[OK] Contrato do marcador final estavel aprovado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
