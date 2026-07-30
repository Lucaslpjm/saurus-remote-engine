#!/usr/bin/env python3
# SAURUS_REMOTE_PRODUCTION_UI_MARKER_CONTRACT_TEST_V1
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
MARKER = "SAURUS_REMOTE_PRODUCTION_UI_FINAL"

FILES = (
    ROOT / ".saurus" / "tools" / "finalize_saurus_production_ui.py",
    ROOT / ".saurus" / "scripts" / "Verify-SaurusCustomization.ps1",
    ROOT / ".saurus" / "tools" / "validate_kit.py",
)


def fail(message: str) -> int:
    print(f"[ERRO] {message}", file=sys.stderr)
    return 1


def main() -> int:
    for path in FILES:
        if not path.is_file():
            return fail(f"Arquivo obrigatorio ausente: {path}")
        if MARKER not in path.read_text(encoding="utf-8-sig"):
            return fail(f"Arquivo sem marcador estavel: {path}")

    finalizer_path = FILES[0]
    spec = importlib.util.spec_from_file_location("saurus_finalizer", finalizer_path)
    if spec is None or spec.loader is None:
        return fail("Nao foi possivel carregar o finalizador.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    sample = (
        "// SAURUS_REMOTE_" "FINAL_UI_3_2_3_2\n"
        "class DesktopHomePage {\n"
        "final a = 'Este dispositivo';\n"
        "final b = 'Conectar e acessar sessoes recentes';\n"
        "final c = 'Historico e sessoes recentes';\n"
        "}\n"
    )
    final = module.finalize_text(sample)
    failures = module.validate_text(final)
    if failures:
        return fail("; ".join(failures))
    if final.count("// " + MARKER) != 1:
        return fail("O marcador estavel nao foi emitido exatamente uma vez.")

    print("[OK] Contrato unico do marcador final da interface aprovado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
