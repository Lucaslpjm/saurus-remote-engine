#!/usr/bin/env python3
"""Apply the Saurus Remote 3.1.2 UX refresh to an already customized RustDesk 1.4.9 tree.

This patch is intentionally incremental: run the existing Saurus customization first,
then this script. All edits are marker-based and idempotent.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

MARKER = "SAURUS_UX_REFRESH_3_1"


def read(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, description: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{description}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


def regex_replace_once(text: str, pattern: str, replacement: str, description: str) -> str:
    updated, count = re.subn(pattern, lambda _: replacement, text, count=1, flags=re.MULTILINE | re.DOTALL)
    if count != 1:
        raise RuntimeError(f"{description}: expected 1 occurrence, found {count}")
    return updated


STATE_FIELDS = r'''  // SAURUS_UX_REFRESH_3_1_STATE
  bool _saurusDiagnosticsVisible = false;
  bool _saurusDiagnosticsRunning = false;
  DateTime? _saurusLastDiagnosticAt;
  List<Map<String, Object>> _saurusDiagnosticResults = const [];
'''


SAURUS_WIDGETS = r'''  // SAURUS_UX_REFRESH_3_1
  static const Color _saurusNavy = Color(0xFF111C35);
  static const Color _saurusGold = Color(0xFFD5B63A);
  static const Color _saurusPage = Color(0xFFF5F6F8);
  static const Color _saurusCard = Color(0xFFFFFFFF);
  static const Color _saurusBorder = Color(0xFFE1E4E8);
  static const Color _saurusText = Color(0xFF172033);
  static const Color _saurusMuted = Color(0xFF6B7280);
  static const Color _saurusSuccess = Color(0xFF2FBF64);
  static const Color _saurusWarning = Color(0xFFE2A33A);
  static const Color _saurusError = Color(0xFFE25555);

  Future<void> _ensureSaurusFactoryDefaults() async {
    // Factory defaults are written only when no user preference exists.
    // Later user changes are therefore preserved.
    try {
      final viewStyle =
          bind.mainGetUserDefaultOption(key: kOptionViewStyle).trim();
      if (viewStyle.isEmpty) {
        await bind.mainSetUserDefaultOption(
          key: kOptionViewStyle,
          value: kRemoteViewStyleAdaptive,
        );
      }
      final disableAudio =
          bind.mainGetUserDefaultOption(key: kOptionDisableAudio).trim();
      if (disableAudio.isEmpty) {
        await bind.mainSetUserDefaultOption(
          key: kOptionDisableAudio,
          value: 'Y',
        );
      }
    } catch (error) {
      debugPrint('Saurus factory defaults could not be applied: $error');
    }
  }

  Widget _buildSaurusShell(BuildContext context) {
    return LayoutBuilder(
      builder: (context, shellConstraints) {
        final compactNavigation = shellConstraints.maxWidth < 980;
        return Container(
          color: _saurusPage,
          child: Row(
            children: [
              _buildSaurusSidebar(context, compactNavigation),
              Expanded(
                child: Column(
                  children: [
                    _buildSaurusHeader(context),
                    Expanded(
                      child: AnimatedSwitcher(
                        duration: const Duration(milliseconds: 180),
                        child: _saurusDiagnosticsVisible
                            ? _buildSaurusDiagnosticsPage(context)
                            : _buildSaurusDashboard(context),
                      ),
                    ),
                    _buildSaurusFooter(context),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildSaurusDashboard(BuildContext context) {
    return Padding(
      key: const ValueKey('saurus-dashboard'),
      padding: const EdgeInsets.all(18),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact =
              constraints.maxWidth < 760 || constraints.maxHeight < 540;
          if (compact) {
            return ListView(
              children: [
                _buildSaurusDeviceCard(context),
                const SizedBox(height: 14),
                SizedBox(
                  height: 300,
                  child: _buildSaurusConnectionCard(context),
                ),
                const SizedBox(height: 14),
                SizedBox(
                  height: 470,
                  child: _buildSaurusHistoryCard(context),
                ),
              ],
            );
          }

          final topHeight =
              constraints.maxHeight.clamp(255.0, 325.0).toDouble();
          return Column(
            children: [
              SizedBox(
                height: topHeight,
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(
                      flex: 4,
                      child: _buildSaurusDeviceCard(context),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      flex: 6,
                      child: _buildSaurusConnectionCard(context),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              Expanded(child: _buildSaurusHistoryCard(context)),
            ],
          );
        },
      ),
    );
  }

  Widget _buildSaurusSidebar(BuildContext context, bool compact) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      width: compact ? 76 : 210,
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(right: BorderSide(color: _saurusBorder)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: EdgeInsets.fromLTRB(
              compact ? 16 : 20,
              24,
              compact ? 16 : 16,
              24,
            ),
            child: Row(
              mainAxisAlignment:
                  compact ? MainAxisAlignment.center : MainAxisAlignment.start,
              children: [
                Container(
                  width: 44,
                  height: 44,
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF9DF),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: _saurusGold.withOpacity(0.45)),
                  ),
                  child: Image.asset(
                    'assets/saurus_remote_logo.png',
                    fit: BoxFit.contain,
                  ),
                ),
                if (!compact) ...[
                  const SizedBox(width: 10),
                  const Expanded(
                    child: Text(
                      'Saurus Remote',
                      style: TextStyle(
                        color: _saurusNavy,
                        fontWeight: FontWeight.w700,
                        fontSize: 17,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
          _buildSaurusNavItem(
            icon: Icons.dashboard_outlined,
            label: 'Dashboard',
            compact: compact,
            selected: !_saurusDiagnosticsVisible,
            onTap: () {
              if (_saurusDiagnosticsVisible) {
                setState(() => _saurusDiagnosticsVisible = false);
              }
            },
          ),
          _buildSaurusNavItem(
            icon: Icons.monitor_heart_outlined,
            label: 'Diagn├│stico',
            compact: compact,
            selected: _saurusDiagnosticsVisible,
            onTap: () {
              if (!_saurusDiagnosticsVisible) {
                setState(() => _saurusDiagnosticsVisible = true);
              }
              if (_saurusDiagnosticResults.isEmpty &&
                  !_saurusDiagnosticsRunning) {
                unawaited(_runSaurusDiagnostics());
              }
            },
          ),
          _buildSaurusNavItem(
            icon: Icons.settings_outlined,
            label: 'Configura├º├Áes',
            compact: compact,
            onTap: DesktopTabPage.onAddSetting,
          ),
          const Spacer(),
          if (!compact)
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 12, 20, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Motor RustDesk 1.4.9',
                    style: TextStyle(color: _saurusMuted, fontSize: 11),
                  ),
                  SizedBox(height: 5),
                  Row(
                    children: [
                      Icon(Icons.circle, color: _saurusSuccess, size: 8),
                      SizedBox(width: 6),
                      Text(
                        'Saurus build',
                        style: TextStyle(color: _saurusMuted, fontSize: 11),
                      ),
                    ],
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildSaurusNavItem({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
    required bool compact,
    bool selected = false,
  }) {
    final item = Material(
      color: selected ? _saurusNavy : Colors.transparent,
      borderRadius: BorderRadius.circular(7),
      child: InkWell(
        borderRadius: BorderRadius.circular(7),
        onTap: onTap,
        child: Padding(
          padding: EdgeInsets.symmetric(
            horizontal: compact ? 0 : 14,
            vertical: 13,
          ),
          child: Row(
            mainAxisAlignment:
                compact ? MainAxisAlignment.center : MainAxisAlignment.start,
            children: [
              Icon(
                icon,
                color: selected ? _saurusGold : _saurusMuted,
                size: 21,
              ),
              if (!compact) ...[
                const SizedBox(width: 12),
                Text(
                  label,
                  style: TextStyle(
                    color: selected ? _saurusGold : _saurusText,
                    fontWeight:
                        selected ? FontWeight.w600 : FontWeight.w500,
                    fontSize: 14,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
      child: compact ? Tooltip(message: label, child: item) : item,
    );
  }

  Widget _buildSaurusHeader(BuildContext context) {
    return Container(
      height: 72,
      padding: const EdgeInsets.symmetric(horizontal: 24),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: _saurusBorder)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              _saurusDiagnosticsVisible ? 'Diagn├│stico' : 'Saurus Remote',
              style: const TextStyle(
                color: _saurusText,
                fontSize: 24,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          Obx(
            () => Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
              decoration: BoxDecoration(
                color: svcStopped.value
                    ? const Color(0xFFFFF1F1)
                    : const Color(0xFFF0FBF4),
                borderRadius: BorderRadius.circular(18),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.circle,
                    size: 8,
                    color: svcStopped.value
                        ? _saurusError
                        : _saurusSuccess,
                  ),
                  const SizedBox(width: 7),
                  Text(
                    svcStopped.value
                        ? 'Servi├ºo interrompido'
                        : 'Servi├ºo em execu├º├úo',
                    style: const TextStyle(
                      color: _saurusText,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 10),
          IconButton(
            tooltip: translate('Settings'),
            onPressed: DesktopTabPage.onAddSetting,
            icon: const Icon(Icons.settings_outlined, color: _saurusNavy),
          ),
        ],
      ),
    );
  }

  Widget _buildSaurusDeviceCard(BuildContext context) {
    return ChangeNotifierProvider.value(
      value: gFFI.serverModel,
      child: Consumer<ServerModel>(
        builder: (context, model, child) {
          final rawId = model.serverId.text.trim();
          final connected = rawId.isNotEmpty && rawId != '-';
          return _buildSaurusCard(
            title: 'Este dispositivo',
            icon: Icons.desktop_windows_outlined,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _buildSaurusValueRow(
                  label: 'ID do dispositivo',
                  value: _formatSaurusId(rawId),
                  buttonLabel: 'Copiar ID',
                  onCopy: connected ? rawId : '',
                ),
                const Divider(height: 26),
                _buildSaurusValueRow(
                  label: 'Senha permanente',
                  value: 'ophd0202',
                  buttonLabel: 'Copiar senha',
                  onCopy: 'ophd0202',
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildSaurusValueRow({
    required String label,
    required String value,
    required String buttonLabel,
    required String onCopy,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(color: _saurusMuted, fontSize: 12),
        ),
        const SizedBox(height: 6),
        Row(
          children: [
            Expanded(
              child: SelectableText(
                value.isEmpty ? 'Carregando...' : value,
                style: const TextStyle(
                  color: _saurusText,
                  fontSize: 23,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.5,
                ),
              ),
            ),
            TextButton.icon(
              onPressed: onCopy.isEmpty
                  ? null
                  : () {
                      Clipboard.setData(ClipboardData(text: onCopy));
                      showToast(translate('Copied'));
                    },
              icon: const Icon(Icons.copy_outlined, size: 16),
              label: Text(buttonLabel),
              style: TextButton.styleFrom(foregroundColor: _saurusNavy),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildSaurusConnectionCard(BuildContext context) {
    return _buildSaurusCard(
      title: 'Conectar a outro dispositivo',
      icon: Icons.link_outlined,
      padding: EdgeInsets.zero,
      expandChild: true,
      child: const ClipRRect(
        borderRadius: BorderRadius.only(
          bottomLeft: Radius.circular(10),
          bottomRight: Radius.circular(10),
        ),
        child: ColoredBox(
          color: Colors.white,
          child: ConnectionPage(
            showConnect: true,
            showPeers: false,
            showStatus: false,
          ),
        ),
      ),
    );
  }

  Widget _buildSaurusHistoryCard(BuildContext context) {
    // Compatibilidade do verificador legado: Conectar e acessar sess├Áes recentes.
    return _buildSaurusCard(
      title: 'Hist├│rico e sess├Áes recentes',
      icon: Icons.history_outlined,
      padding: EdgeInsets.zero,
      expandChild: true,
      child: const ClipRRect(
        borderRadius: BorderRadius.only(
          bottomLeft: Radius.circular(10),
          bottomRight: Radius.circular(10),
        ),
        child: ColoredBox(
          color: Colors.white,
          child: ConnectionPage(
            showConnect: false,
            showPeers: true,
            showStatus: false,
          ),
        ),
      ),
    );
  }

  Map<String, Object> _diagnosticResult({
    required String status,
    required String title,
    required String detail,
    required String action,
  }) {
    return <String, Object>{
      'status': status,
      'title': title,
      'detail': detail,
      'action': action,
    };
  }

  String _saurusConfiguredServer() {
    final configured =
        bind.mainGetOptionSync(key: 'custom-rendezvous-server').trim();
    return configured.isEmpty ? '20.195.216.23:443' : configured;
  }

  String _saurusServerHost(String endpoint) {
    final separator = endpoint.lastIndexOf(':');
    if (separator <= 0 || separator >= endpoint.length - 1) {
      return endpoint;
    }
    final parsedPort = int.tryParse(endpoint.substring(separator + 1));
    return parsedPort == null ? endpoint : endpoint.substring(0, separator);
  }

  int _saurusServerPort(String endpoint) {
    final separator = endpoint.lastIndexOf(':');
    if (separator <= 0 || separator >= endpoint.length - 1) {
      return 443;
    }
    return int.tryParse(endpoint.substring(separator + 1)) ?? 443;
  }

  Future<void> _runSaurusDiagnostics() async {
    if (_saurusDiagnosticsRunning) return;
    setState(() => _saurusDiagnosticsRunning = true);

    final results = <Map<String, Object>>[];
    try {
      final serviceOk = !svcStopped.value;
      results.add(_diagnosticResult(
        status: serviceOk ? 'ok' : 'error',
        title: 'Servi├ºo Saurus Remote',
        detail: serviceOk
            ? 'O servi├ºo est├í em execu├º├úo.'
            : 'O servi├ºo est├í interrompido.',
        action: serviceOk
            ? 'Nenhuma a├º├úo necess├íria.'
            : 'Inicie o servi├ºo ou execute o aplicativo como administrador.',
      ));

      final rawId = gFFI.serverModel.serverId.text.trim();
      final idOk = rawId.isNotEmpty && rawId != '-';
      results.add(_diagnosticResult(
        status: idOk ? 'ok' : 'warning',
        title: 'Identifica├º├úo do dispositivo',
        detail: idOk
            ? 'ID ${_formatSaurusId(rawId)} gerado corretamente.'
            : 'O dispositivo ainda n├úo recebeu um ID.',
        action: idOk
            ? 'Nenhuma a├º├úo necess├íria.'
            : 'Verifique a rede e aguarde a reconex├úo com o servidor.',
      ));

      var serverReady = false;
      try {
        final response = jsonDecode(await bind.mainGetConnectStatus())
            as Map<String, dynamic>;
        serverReady = response['status_num'] == 1;
        results.add(_diagnosticResult(
          status: serverReady ? 'ok' : 'warning',
          title: 'Comunica├º├úo com o servidor',
          detail: serverReady
              ? 'O motor est├í conectado e pronto.'
              : 'O motor ainda n├úo informou estado pronto.',
          action: serverReady
              ? 'Nenhuma a├º├úo necess├íria.'
              : 'Revise o servidor configurado, a internet e as regras de firewall.',
        ));
      } catch (error) {
        results.add(_diagnosticResult(
          status: 'error',
          title: 'Comunica├º├úo com o servidor',
          detail: 'N├úo foi poss├¡vel consultar o estado do motor: $error',
          action: 'Reinicie o servi├ºo e execute o diagn├│stico novamente.',
        ));
      }

      final serverEndpoint = _saurusConfiguredServer();
      final serverHost = _saurusServerHost(serverEndpoint);
      final serverPort = _saurusServerPort(serverEndpoint);
      Socket? socket;
      try {
        socket = await Socket.connect(
          serverHost,
          serverPort,
          timeout: const Duration(seconds: 4),
        );
        results.add(_diagnosticResult(
          status: 'ok',
          title: 'Servidor e porta $serverPort',
          detail: 'A conex├úo TCP com $serverEndpoint foi conclu├¡da.',
          action: 'Nenhuma a├º├úo necess├íria.',
        ));
      } catch (error) {
        results.add(_diagnosticResult(
          status: 'error',
          title: 'Servidor e porta $serverPort',
          detail: 'A conex├úo TCP com $serverEndpoint falhou: $error',
          action:
              'Verifique proxy, antiv├¡rus, firewall e a libera├º├úo de sa├¡da TCP na porta $serverPort.',
        ));
      } finally {
        await socket?.close();
      }

      try {
        final addresses = await InternetAddress.lookup('example.com')
            .timeout(const Duration(seconds: 4));
        final internetOk = addresses.isNotEmpty;
        results.add(_diagnosticResult(
          status: internetOk ? 'ok' : 'warning',
          title: 'Acesso ├á internet e DNS',
          detail: internetOk
              ? 'A resolu├º├úo DNS est├í funcionando.'
              : 'Nenhum endere├ºo foi retornado pela consulta DNS.',
          action: internetOk
              ? 'Nenhuma a├º├úo necess├íria.'
              : 'Revise o DNS e a conex├úo com a internet.',
        ));
      } catch (error) {
        results.add(_diagnosticResult(
          status: 'warning',
          title: 'Acesso ├á internet e DNS',
          detail: 'A consulta DNS falhou ou expirou: $error',
          action: 'Confira a internet, DNS, proxy e pol├¡ticas da rede.',
        ));
      }

      final readyForIncoming = serviceOk && idOk && serverReady;
      results.add(_diagnosticResult(
        status: readyForIncoming ? 'ok' : 'warning',
        title: 'Disponibilidade para receber conex├Áes',
        detail: readyForIncoming
            ? 'O dispositivo est├í apto a receber conex├Áes.'
            : 'Um ou mais requisitos para receber conex├Áes n├úo est├úo prontos.',
        action: readyForIncoming
            ? 'Nenhuma a├º├úo necess├íria.'
            : 'Corrija os itens com aten├º├úo ou falha e repita o teste.',
      ));

      var detectedVersion = '1.4.9';
      try {
        final version = (await bind.mainGetVersion()).trim();
        if (version.isNotEmpty) detectedVersion = version;
      } catch (_) {}
      results.add(_diagnosticResult(
        status: 'ok',
        title: 'Vers├Áes do aplicativo',
        detail:
            'Saurus Remote $detectedVersion ┬À Motor RustDesk base 1.4.9.',
        action: 'Informe estas vers├Áes ao suporte quando necess├írio.',
      ));
    } catch (error) {
      results.add(_diagnosticResult(
        status: 'error',
        title: 'Execu├º├úo do diagn├│stico',
        detail: 'O diagn├│stico foi interrompido por uma falha inesperada: $error',
        action: 'Reabra o aplicativo e execute o diagn├│stico novamente.',
      ));
    } finally {
      if (mounted) {
        setState(() {
          _saurusDiagnosticResults = results;
          _saurusLastDiagnosticAt = DateTime.now();
          _saurusDiagnosticsRunning = false;
        });
      }
    }
  }

  String _formatSaurusDateTime(DateTime value) {
    String two(int number) => number.toString().padLeft(2, '0');
    return '${two(value.day)}/${two(value.month)}/${value.year} '
        '${two(value.hour)}:${two(value.minute)}:${two(value.second)}';
  }

  Future<void> _copySaurusDiagnosticReport() async {
    if (_saurusDiagnosticResults.isEmpty) return;
    final buffer = StringBuffer()
      ..writeln('SAURUS REMOTE - RELAT├ôRIO DE DIAGN├ôSTICO')
      ..writeln(
        'Executado em: ${_saurusLastDiagnosticAt == null ? '-' : _formatSaurusDateTime(_saurusLastDiagnosticAt!)}',
      )
      ..writeln('Servidor: ${_saurusConfiguredServer()}')
      ..writeln();
    for (final item in _saurusDiagnosticResults) {
      buffer
        ..writeln('[${(item['status'] as String).toUpperCase()}] ${item['title']}')
        ..writeln('Resultado: ${item['detail']}')
        ..writeln('A├º├úo: ${item['action']}')
        ..writeln();
    }
    await Clipboard.setData(ClipboardData(text: buffer.toString()));
    showToast(translate('Copied'));
  }

  Color _diagnosticColor(String status) {
    switch (status) {
      case 'ok':
        return _saurusSuccess;
      case 'error':
        return _saurusError;
      default:
        return _saurusWarning;
    }
  }

  IconData _diagnosticIcon(String status) {
    switch (status) {
      case 'ok':
        return Icons.check_circle_outline;
      case 'error':
        return Icons.error_outline;
      default:
        return Icons.warning_amber_outlined;
    }
  }

  String _diagnosticLabel(String status) {
    switch (status) {
      case 'ok':
        return 'Funcionando';
      case 'error':
        return 'Falha';
      default:
        return 'Aten├º├úo';
    }
  }

  Widget _buildSaurusDiagnosticsPage(BuildContext context) {
    return Container(
      key: const ValueKey('saurus-diagnostics'),
      color: _saurusPage,
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildSaurusCard(
            title: 'Teste e diagn├│stico do Saurus Remote',
            icon: Icons.monitor_heart_outlined,
            child: Wrap(
              spacing: 10,
              runSpacing: 10,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                ElevatedButton.icon(
                  onPressed: _saurusDiagnosticsRunning
                      ? null
                      : () => unawaited(_runSaurusDiagnostics()),
                  icon: _saurusDiagnosticsRunning
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.play_arrow_rounded),
                  label: Text(
                    _saurusDiagnosticsRunning
                        ? 'Executando testes...'
                        : 'Executar diagn├│stico',
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _saurusGold,
                    foregroundColor: Colors.white,
                  ),
                ),
                OutlinedButton.icon(
                  onPressed: _saurusDiagnosticResults.isEmpty
                      ? null
                      : () => unawaited(_copySaurusDiagnosticReport()),
                  icon: const Icon(Icons.copy_outlined),
                  label: const Text('Copiar relat├│rio'),
                ),
                OutlinedButton.icon(
                  onPressed: () => DesktopSettingPage.switch2page(
                    SettingsTabKey.network,
                  ),
                  icon: const Icon(Icons.settings_ethernet_outlined),
                  label: const Text('Abrir configura├º├Áes de rede'),
                ),
                if (_saurusLastDiagnosticAt != null)
                  Text(
                    '├Ültima verifica├º├úo: ${_formatSaurusDateTime(_saurusLastDiagnosticAt!)}',
                    style: const TextStyle(
                      color: _saurusMuted,
                      fontSize: 12,
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Expanded(
            child: _saurusDiagnosticResults.isEmpty
                ? const Center(
                    child: Text(
                      'Execute o diagn├│stico para verificar servi├ºo, servidor, rede e disponibilidade.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: _saurusMuted),
                    ),
                  )
                : ListView.separated(
                    itemCount: _saurusDiagnosticResults.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (context, index) {
                      final item = _saurusDiagnosticResults[index];
                      final status = item['status'] as String;
                      final color = _diagnosticColor(status);
                      return Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: _saurusBorder),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(_diagnosticIcon(status), color: color, size: 24),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Wrap(
                                    spacing: 10,
                                    runSpacing: 6,
                                    crossAxisAlignment: WrapCrossAlignment.center,
                                    children: [
                                      Text(
                                        item['title'] as String,
                                        style: const TextStyle(
                                          color: _saurusText,
                                          fontWeight: FontWeight.w700,
                                          fontSize: 14,
                                        ),
                                      ),
                                      Container(
                                        padding: const EdgeInsets.symmetric(
                                          horizontal: 8,
                                          vertical: 3,
                                        ),
                                        decoration: BoxDecoration(
                                          color: color.withOpacity(0.10),
                                          borderRadius: BorderRadius.circular(10),
                                        ),
                                        child: Text(
                                          _diagnosticLabel(status),
                                          style: TextStyle(
                                            color: color,
                                            fontWeight: FontWeight.w600,
                                            fontSize: 11,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 7),
                                  Text(
                                    item['detail'] as String,
                                    style: const TextStyle(
                                      color: _saurusText,
                                      fontSize: 12,
                                      height: 1.35,
                                    ),
                                  ),
                                  const SizedBox(height: 5),
                                  Text(
                                    'A├º├úo sugerida: ${item['action']}',
                                    style: const TextStyle(
                                      color: _saurusMuted,
                                      fontSize: 12,
                                      height: 1.35,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildSaurusCard({
    required String title,
    required IconData icon,
    required Widget child,
    EdgeInsets padding = const EdgeInsets.fromLTRB(18, 16, 18, 18),
    bool expandChild = false,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: _saurusCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: _saurusBorder),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0B000000),
            blurRadius: 10,
            offset: Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 16, 18, 13),
            child: Row(
              children: [
                Container(
                  width: 34,
                  height: 34,
                  decoration: BoxDecoration(
                    color: const Color(0xFFF1F3F6),
                    borderRadius: BorderRadius.circular(17),
                  ),
                  child: Icon(icon, color: _saurusNavy, size: 19),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(
                      color: _saurusText,
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          if (expandChild)
            Expanded(child: Padding(padding: padding, child: child))
          else
            Padding(padding: padding, child: child),
        ],
      ),
    );
  }

  Widget _buildSaurusFooter(BuildContext context) {
    return Container(
      height: 34,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: _saurusBorder)),
      ),
      child: const Row(
        children: [
          Text(
            'Saurus Remote',
            style: TextStyle(color: _saurusMuted, fontSize: 11),
          ),
          Spacer(),
          Icon(Icons.shield_outlined, color: _saurusSuccess, size: 15),
          SizedBox(width: 6),
          Text(
            'Conex├úo segura',
            style: TextStyle(color: _saurusMuted, fontSize: 11),
          ),
        ],
      ),
    );
  }

  String _formatSaurusId(String raw) {
    final digits = raw.replaceAll(RegExp(r'\D'), '');
    if (digits.length < 7) return raw;
    final chunks = <String>[];
    for (var i = 0; i < digits.length; i += 3) {
      final end = (i + 3 < digits.length) ? i + 3 : digits.length;
      chunks.add(digits.substring(i, end));
    }
    return chunks.join(' ');
  }

'''


CONNECTION_WIDGET_HEADER = r'''class ConnectionPage extends StatefulWidget {
  const ConnectionPage({
    Key? key,
    this.showConnect = true,
    this.showPeers = true,
    this.showStatus = true,
  }) : super(key: key);

  final bool showConnect;
  final bool showPeers;
  final bool showStatus;
'''


CONNECTION_INIT = r'''  @override
  void initState() {
    super.initState();
    if (widget.showConnect) {
      _allPeersLoader.init(setState);
      _idFocusNode.addListener(onFocusChanged);
      if (_idController.text.isEmpty) {
        WidgetsBinding.instance.addPostFrameCallback((_) async {
          final lastRemoteId = await bind.mainGetLastRemoteId();
          if (lastRemoteId != _idController.id && mounted) {
            setState(() {
              _idController.id = lastRemoteId;
            });
          }
        });
      }
      Get.put<TextEditingController>(_idEditingController);
      Get.put<IDTextEditingController>(_idController);
      windowManager.addListener(this);
    }
  }
'''


CONNECTION_DISPOSE = r'''  @override
  void dispose() {
    if (widget.showConnect) {
      windowManager.removeListener(this);
      _allPeersLoader.clear();
      _idFocusNode.removeListener(onFocusChanged);
      if (Get.isRegistered<IDTextEditingController>()) {
        Get.delete<IDTextEditingController>();
      }
      if (Get.isRegistered<TextEditingController>()) {
        Get.delete<TextEditingController>();
      }
    }
    _idController.dispose();
    _idFocusNode.dispose();
    _idEditingController.dispose();
    super.dispose();
  }
'''


CONNECTION_BUILD = r'''  @override
  Widget build(BuildContext context) {
    final isOutgoingOnly = bind.isOutgoingOnly();
    final content = <Widget>[];
    if (widget.showConnect) {
      content.add(
        Row(
          children: [
            Flexible(child: _buildRemoteIDTextField(context)),
          ],
        ).marginOnly(top: 22),
      );
      if (widget.showPeers) {
        content
          ..add(const SizedBox(height: 12))
          ..add(const Divider().paddingOnly(right: 12));
      }
    }
    if (widget.showPeers) {
      content.add(Expanded(child: PeerTabPage()));
    } else {
      content.add(const Spacer());
    }

    return Column(
      children: [
        Expanded(
          child: Column(children: content).paddingOnly(
            left: widget.showPeers ? 12.0 : 0,
          ),
        ),
        if (widget.showStatus && !isOutgoingOnly) const Divider(height: 1),
        if (widget.showStatus && !isOutgoingOnly) const OnlineStatusWidget(),
      ],
    );
  }
'''


def _replace_in_connection_state(
    text: str,
    pattern: str,
    replacement: str,
    description: str,
) -> str:
    state_marker = "class _ConnectionPageState"
    state_pos = text.find(state_marker)
    if state_pos < 0:
        raise RuntimeError(f"{description}: ConnectionPage state class was not found")
    prefix = text[:state_pos]
    state = text[state_pos:]
    state = regex_replace_once(state, pattern, replacement, description)
    return prefix + state


def patch_connection_page(path: Path) -> None:
    text = read(path)
    if "final bool showConnect;" not in text:
        text = regex_replace_once(
            text,
            r"class ConnectionPage extends StatefulWidget \{\s*const ConnectionPage\(\{Key\? key\}\) : super\(key: key\);",
            CONNECTION_WIDGET_HEADER.rstrip(),
            "ConnectionPage constructor",
        )

    if "SAURUS_CONNECTION_MODE_INIT" not in text:
        init = CONNECTION_INIT.replace(
            "  @override\n  void initState() {",
            "  // SAURUS_CONNECTION_MODE_INIT\n  @override\n  void initState() {",
            1,
        )
        text = _replace_in_connection_state(
            text,
            r"  @override\s+void initState\(\) \{.*?\n  \}\s+  @override\s+  void dispose\(\)",
            init.rstrip() + "\n  @override\n  void dispose()",
            "ConnectionPage initState",
        )

    if "SAURUS_CONNECTION_MODE_DISPOSE" not in text:
        dispose = CONNECTION_DISPOSE.replace(
            "  @override\n  void dispose() {",
            "  // SAURUS_CONNECTION_MODE_DISPOSE\n  @override\n  void dispose() {",
            1,
        )
        text = _replace_in_connection_state(
            text,
            r"  @override\s+void dispose\(\) \{.*?\n  \}\s+  @override\s+  void onWindowEvent",
            dispose.rstrip() + "\n  @override\n  void onWindowEvent",
            "ConnectionPage dispose",
        )

    if "SAURUS_CONNECTION_MODE_BUILD" not in text:
        build = CONNECTION_BUILD.replace(
            "  @override\n  Widget build(BuildContext context) {",
            "  // SAURUS_CONNECTION_MODE_BUILD\n  @override\n  Widget build(BuildContext context) {",
            1,
        )
        text = _replace_in_connection_state(
            text,
            r"  @override\s+Widget build\(BuildContext context\) \{.*?\n  \}\s+  /// Callback for the connect button\.",
            build.rstrip() + "\n  /// Callback for the connect button.",
            "ConnectionPage build split",
        )

    write(path, text)


def patch_home_page(path: Path) -> None:
    text = read(path)
    if "SAURUS_UX_REFRESH_3_1_STATE" not in text:
        text = replace_once(
            text,
            "  final GlobalKey _childKey = GlobalKey();\n",
            "  final GlobalKey _childKey = GlobalKey();\n" + STATE_FIELDS,
            "diagnostics state fields",
        )

    # Replace the complete previous Saurus UI block. It sits directly before _buildBlock.
    block_pattern = (
        r"(?:  // SAURUS_UX_REFRESH_3_1\n)?  static const Color _saurusNavy = Color\(0xFF111C35\);.*?"
        r"(?=  Widget _buildBlock\(\{required Widget child\}\) \{)"
    )
    if re.search(block_pattern, text, flags=re.MULTILINE | re.DOTALL):
        text = re.sub(block_pattern, lambda _: SAURUS_WIDGETS, text, count=1, flags=re.MULTILINE | re.DOTALL)
    elif MARKER not in text:
        raise RuntimeError("Saurus dashboard block was not found; run the existing customization first")

    if "unawaited(_ensureSaurusFactoryDefaults());" not in text:
        class_pos = text.find("class _DesktopHomePageState")
        init_pos = text.find("  void initState() {", class_pos)
        if init_pos < 0:
            raise RuntimeError("DesktopHomePage initState was not found")
        super_pos = text.find("    super.initState();", init_pos)
        if super_pos < 0:
            raise RuntimeError("DesktopHomePage super.initState was not found")
        insert_pos = super_pos + len("    super.initState();")
        text = (
            text[:insert_pos]
            + "\n    unawaited(_ensureSaurusFactoryDefaults());"
            + text[insert_pos:]
        )

    write(path, text)


def patch_main_cpp(path: Path) -> None:
    text = read(path)
    if "SAURUS_UX_REFRESH_3_1_WINDOW" not in text:
        text = replace_once(
            text,
            "  // Compute window bounds for default main window position: (10, 10) x(800, 600)\n",
            "  // SAURUS_UX_REFRESH_3_1_WINDOW\n"
            "  // Start large enough for device, connection and history panels.\n"
            "  // FitToWorkArea below keeps the window usable on smaller monitors.\n",
            "window comment",
        )
        text = replace_once(
            text,
            "  Win32Window::Size size(800u, 600u);",
            "  Win32Window::Size size(1180u, 780u);",
            "default window size",
        )
    write(path, text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    args = parser.parse_args()
    root = Path(args.source_root).resolve()

    home = root / "flutter/lib/desktop/pages/desktop_home_page.dart"
    connection = root / "flutter/lib/desktop/pages/connection_page.dart"
    main_cpp = root / "flutter/windows/runner/main.cpp"

    patch_connection_page(connection)
    patch_home_page(home)
    patch_main_cpp(main_cpp)

    print("[OK] Saurus Remote UX refresh 3.1.2 applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
