#!/usr/bin/env python3
"""Fast synthetic regression test for patch idempotence and workflow integration."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APPLY = ROOT / ".saurus/tools/apply_saurus_ux_refresh.py"
VERIFY = ROOT / ".saurus/tools/verify_saurus_ux_refresh.py"
OPTIMIZE = ROOT / ".saurus/tools/optimize_saurus_workflow.py"

HOME = """import 'dart:async';
import 'dart:io';
import 'dart:convert';
class _DesktopHomePageState {
  final GlobalKey _childKey = GlobalKey();
  Widget build(BuildContext context) {
    return _buildBlock(child: _buildSaurusShell(context));
  }
  static const Color _saurusNavy = Color(0xFF111C35);
  Widget _buildSaurusShell(BuildContext context) => Container();
  Widget _buildSaurusDiagnosticsCard(BuildContext context) => Container();
  Widget _buildSaurusDeviceCard(BuildContext context) =>
      Text('Status do servidor Configura├º├Áes de rede Diagn├│stico r├ípido');
  Widget _buildBlock({required Widget child}) { return child; }
  void initState() {
    super.initState();
  }
}
"""

CONNECTION = """class OnlineStatusWidget extends StatefulWidget {
  const OnlineStatusWidget({Key? key}) : super(key: key);
  State<OnlineStatusWidget> createState() => _OnlineStatusWidgetState();
}
class _OnlineStatusWidgetState extends State<OnlineStatusWidget> {
  @override
  void initState() {
    super.initState();
    startStatusTimer();
  }
  @override
  void dispose() {
    stopStatusTimer();
    super.dispose();
  }
  @override
  Widget build(BuildContext context) {
    return const Text('status');
  }
}
class ConnectionPage extends StatefulWidget {
  const ConnectionPage({Key? key}) : super(key: key);
  State<ConnectionPage> createState() => _ConnectionPageState();
}
class _ConnectionPageState extends State<ConnectionPage> {
  @override
  void initState() {
    super.initState();
    _allPeersLoader.init(setState);
    _idFocusNode.addListener(onFocusChanged);
    if (_idController.text.isEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) async {
        final lastRemoteId = await bind.mainGetLastRemoteId();
        if (lastRemoteId != _idController.id) {
          setState(() { _idController.id = lastRemoteId; });
        }
      });
    }
    Get.put<TextEditingController>(_idEditingController);
    Get.put<IDTextEditingController>(_idController);
    windowManager.addListener(this);
  }
  @override
  void dispose() {
    _idController.dispose();
    windowManager.removeListener(this);
    _allPeersLoader.clear();
    _idFocusNode.removeListener(onFocusChanged);
    _idFocusNode.dispose();
    _idEditingController.dispose();
    if (Get.isRegistered<IDTextEditingController>()) {
      Get.delete<IDTextEditingController>();
    }
    if (Get.isRegistered<TextEditingController>()) {
      Get.delete<TextEditingController>();
    }
    super.dispose();
  }
  @override
  void onWindowEvent(String eventName) {}
  @override
  Widget build(BuildContext context) {
    final isOutgoingOnly = bind.isOutgoingOnly();
    return Column(
      children: [
        Expanded(
            child: Column(
          children: [
            Row(children: [Flexible(child: _buildRemoteIDTextField(context))])
                .marginOnly(top: 22),
            SizedBox(height: 12),
            Divider().paddingOnly(right: 12),
            Expanded(child: PeerTabPage()),
          ],
        ).paddingOnly(left: 12.0)),
        if (!isOutgoingOnly) const Divider(height: 1),
        if (!isOutgoingOnly) OnlineStatusWidget()
      ],
    );
  }
  /// Callback for the connect button.
  void onConnect() {}
}
"""

MAIN_CPP = """  // Compute window bounds for default main window position: (10, 10) x(800, 600)
  Win32Window::Point relative_origin(10, 10);
  Win32Window::Size size(800u, 600u);
  Win32Desktop::FitToWorkArea(origin, size);
"""

WORKFLOW = """name: Build Saurus Remote Engine (Windows x64)
on:
  workflow_dispatch:
    inputs:
      build_label:
        type: string
permissions:
  contents: read
jobs:
  build-windows-x64:
    runs-on: windows-2022
    steps:
      - name: Checkout fork with submodules
        uses: actions/checkout@sha
        with:
          submodules: recursive
          fetch-depth: 0
      - name: Apply Saurus customization
        shell: pwsh
        run: echo apply
      - name: Verify Saurus customization and secret policy
        shell: pwsh
        run: echo verify
      - name: Restore generated Flutter-Rust bridge
        uses: actions/download-artifact@sha
      - name: Install Flutter
        uses: subosito/flutter-action@sha
        with:
          channel: stable
          flutter-version: 3.24.5
          architecture: x64
      - name: Install RustDesk custom Flutter engine
        shell: pwsh
        run: flutter doctor -v
      - name: Apply Flutter 3.24 dropdown patch safely
        shell: bash
        run: echo patch
      - name: Install Rust toolchain
        uses: dtolnay/rust-toolchain@sha
"""


def run(*args: str) -> None:
    subprocess.run([sys.executable, *args], check=True)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pages = root / "flutter/lib/desktop/pages"
        runner = root / "flutter/windows/runner"
        pages.mkdir(parents=True)
        runner.mkdir(parents=True)
        (pages / "desktop_home_page.dart").write_text(HOME, encoding="utf-8")
        (pages / "connection_page.dart").write_text(CONNECTION, encoding="utf-8")
        (runner / "main.cpp").write_text(MAIN_CPP, encoding="utf-8")
        workflow = root / "workflow.yml"
        workflow.write_text(WORKFLOW, encoding="utf-8")

        run(str(APPLY), "--source-root", str(root))
        run(str(VERIFY), "--source-root", str(root))
        first_home = (pages / "desktop_home_page.dart").read_text(encoding="utf-8")
        first_connection = (pages / "connection_page.dart").read_text(encoding="utf-8")
        run(str(APPLY), "--source-root", str(root))
        run(str(VERIFY), "--source-root", str(root))
        assert first_home == (pages / "desktop_home_page.dart").read_text(encoding="utf-8")
        assert first_connection == (pages / "connection_page.dart").read_text(encoding="utf-8")
        assert first_connection.count("class OnlineStatusWidget") == 1
        assert "startStatusTimer();" in first_connection
        assert "stopStatusTimer();" in first_connection

        run(str(OPTIMIZE), "--workflow", str(workflow))
        first_workflow = workflow.read_text(encoding="utf-8")
        run(str(OPTIMIZE), "--workflow", str(workflow))
        assert first_workflow == workflow.read_text(encoding="utf-8")
        assert "fetch-depth: 1" in first_workflow
        assert "pub-cache: true" in first_workflow
        assert "          cache: true" not in first_workflow
        assert "Verify Saurus UX refresh" in first_workflow

    print("[OK] Synthetic UX refresh regression test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
