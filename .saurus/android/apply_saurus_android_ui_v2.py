#!/usr/bin/env python3
"""Apply the Saurus Remote Android visual identity and guided permissions UX.

This layer runs after the base Android host customization. It is intentionally
ASCII-only in source; Portuguese strings use Unicode escapes so the patch is
stable on Windows and Linux.
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

MARKER = "SAURUS_ANDROID_UI_V2"
NAVY = "0xFF14213D"
GOLD = "0xFFD8B62A"
BACKGROUND = "0xFFF4F6F8"
BORDER = "0xFFE2E7EC"
MUTED = "0xFF667085"
XML_ATTRIBUTE_PATCH_MARKER = "SAURUS_ANDROID_XML_ATTRIBUTE_PATCH_V5"
LAUNCHER_PATCH_MARKER = "SAURUS_ANDROID_ADAPTIVE_LAUNCHER_V1"
INCOMING_ACCEPT_MARKER = "SAURUS_ANDROID_INCOMING_ACCEPT_V2"
ANDROID_NAMESPACE = "http://schemas.android.com/apk/res/android"


class UiPatchError(RuntimeError):
    pass


def read_text(path: Path) -> str:
    if not path.is_file():
        raise UiPatchError(f"Required file not found: {path}")
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")


def replace_once(path: Path, old: str, new: str, *, marker: str | None = None) -> bool:
    content = read_text(path)
    if marker and marker in content:
        return False
    count = content.count(old)
    if count != 1:
        if new in content and count == 0:
            return False
        raise UiPatchError(f"{path}: expected one occurrence, found {count}: {old[:120]!r}")
    write_text(path, content.replace(old, new, 1))
    return True


def replace_regex_once(
    path: Path,
    pattern: str,
    replacement: str,
    *,
    marker: str | None = None,
    flags: int = 0,
) -> bool:
    content = read_text(path)
    if marker and marker in content:
        return False
    updated, count = re.subn(pattern, replacement, content, count=1, flags=flags)
    if count != 1:
        raise UiPatchError(f"{path}: expected one regex match, found {count}: {pattern}")
    write_text(path, updated)
    return True


def insert_before(path: Path, anchor: str, insertion: str, marker: str) -> bool:
    content = read_text(path)
    if marker in content:
        return False
    count = content.count(anchor)
    if count != 1:
        raise UiPatchError(f"{path}: expected one insertion anchor, found {count}: {anchor!r}")
    write_text(path, content.replace(anchor, insertion + anchor, 1))
    return True


def replace_dart_class_pair(
    content: str,
    class_name: str,
    next_class_name: str,
    replacement: str,
    path: Path,
) -> str:
    """Replace one complete top-level Dart class up to the next class declaration."""
    pattern = re.compile(
        rf"(?ms)^class {re.escape(class_name)}\b.*?^class {re.escape(next_class_name)}\b"
    )
    updated, count = pattern.subn(lambda _match: replacement, content, count=1)
    if count != 1:
        raise UiPatchError(
            f"{path}: Dart class boundary not found exactly once: "
            f"{class_name} -> {next_class_name}"
        )
    return updated


def patch_home_page(root: Path) -> None:
    path = root / "flutter/lib/mobile/pages/home_page.dart"
    content = read_text(path)
    if f"{MARKER}_HOME" in content:
        return

    content = content.replace(
        """        child: Scaffold(\n          // backgroundColor: MyTheme.grayBg,""",
        f"""        child: Scaffold(\n          backgroundColor: const Color({BACKGROUND}), // {MARKER}_HOME""",
        1,
    )
    if f"{MARKER}_HOME" not in content:
        raise UiPatchError(f"{path}: Scaffold contract not found")

    old_appbar = """          appBar: AppBar(
            centerTitle: true,
            title: appTitle(),
            actions: _pages.elementAt(_selectedIndex).appBarActions,
          ),"""
    new_appbar = f"""          appBar: AppBar(
            centerTitle: true,
            toolbarHeight: 68,
            backgroundColor: const Color({NAVY}),
            foregroundColor: Colors.white,
            surfaceTintColor: Colors.transparent,
            elevation: 0,
            title: appTitle(),
            actions: _pages.elementAt(_selectedIndex).appBarActions,
          ),"""
    if old_appbar not in content:
        raise UiPatchError(f"{path}: AppBar contract not found")
    content = content.replace(old_appbar, new_appbar, 1)

    old_items = """            items: _pages
                .map((page) =>
                    BottomNavigationBarItem(icon: page.icon, label: page.title))
                .toList(),"""
    new_items = """            items: _pages
                .map((page) => BottomNavigationBarItem(
                    icon: page.icon, label: _saurusNavigationLabel(page)))
                .toList(),"""
    if old_items not in content:
        raise UiPatchError(f"{path}: navigation items contract not found")
    content = content.replace(old_items, new_items, 1)

    old_nav = """            currentIndex: _selectedIndex,
            type: BottomNavigationBarType.fixed,
            selectedItemColor: MyTheme.accent, //
            unselectedItemColor: MyTheme.darkGray,"""
    new_nav = f"""            currentIndex: _selectedIndex,
            type: BottomNavigationBarType.fixed,
            backgroundColor: Colors.white,
            elevation: 12,
            selectedItemColor: const Color({GOLD}),
            unselectedItemColor: const Color({MUTED}),
            selectedFontSize: 12,
            unselectedFontSize: 11,
            showUnselectedLabels: true,"""
    if old_nav not in content:
        raise UiPatchError(f"{path}: navigation style contract not found")
    content = content.replace(old_nav, new_nav, 1)

    old_title = "    return Text(bind.mainGetAppNameSync());"
    new_title = f"    return const _SaurusMobileHeader(); // {MARKER}_HEADER"
    if old_title not in content:
        raise UiPatchError(f"{path}: default app title contract not found")
    content = content.replace(old_title, new_title, 1)

    helper = r'''
String _saurusNavigationLabel(PageShape page) {
  if (page is ServerPage) return 'Dispositivo';
  if (page is ConnectionPage) return 'Conex\u00f5es';
  if (page is SettingsPage) return 'Ajustes';
  return page.title;
}

class _SaurusMobileHeader extends StatelessWidget {
  const _SaurusMobileHeader();

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 38,
          height: 38,
          padding: const EdgeInsets.all(7),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(11),
          ),
          child: Image.asset(
            'assets/saurus_remote_android_logo.png',
            fit: BoxFit.contain,
          ),
        ),
        const SizedBox(width: 10),
        const Text(
          'Saurus Remote',
          style: TextStyle(
            color: Colors.white,
            fontSize: 21,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.1,
          ),
        ),
      ],
    );
  }
}

'''
    anchor = "class HomePage extends StatefulWidget {"
    if anchor not in content:
        raise UiPatchError(f"{path}: HomePage anchor not found")
    content = content.replace(anchor, helper + anchor, 1)
    write_text(path, content)


def patch_theme(root: Path) -> None:
    """Apply the Saurus mobile theme without depending on one exact upstream block."""
    path = root / "flutter/lib/common.dart"
    content = read_text(path)
    theme_marker = f"{MARKER}_THEME"
    robust_marker = "SAURUS_ANDROID_THEME_PATCH_V3"

    if theme_marker in content:
        for required in (
            robust_marker,
            f"primary: Color({NAVY})",
            f"secondary: Color({GOLD})",
            "cardColor: Colors.white",
        ):
            if required not in content:
                raise UiPatchError(f"{path}: incomplete idempotent theme contract: {required}")
        return

    light_anchor = "  static ThemeData lightTheme = ThemeData("
    dark_anchor = "  static ThemeData darkTheme = ThemeData("
    light_start = content.find(light_anchor)
    dark_start = content.find(dark_anchor, light_start + len(light_anchor))
    if light_start < 0 or dark_start < 0 or dark_start <= light_start:
        raise UiPatchError(f"{path}: light/dark ThemeData boundaries were not found")

    block = content[light_start:dark_start]

    def insert_after_property(source: str, property_name: str, insertion: str) -> str:
        match = re.search(
            rf"(?m)^    {re.escape(property_name)}:[^\n]*$",
            source,
        )
        if match is None:
            raise UiPatchError(
                f"{path}: insertion anchor property was not found: {property_name}"
            )
        return source[: match.end()] + "\n" + insertion + source[match.end() :]

    def set_line_property(
        source: str,
        property_name: str,
        replacement: str,
        *,
        insert_after: str | None = None,
    ) -> str:
        pattern = rf"(?m)^    {re.escape(property_name)}:[^\n]*$"
        updated, count = re.subn(pattern, replacement, source, count=1)
        if count == 1:
            return updated
        if insert_after is None:
            raise UiPatchError(f"{path}: theme property was not found: {property_name}")
        return insert_after_property(source, insert_after, replacement)

    def constructor_property_span(source: str, property_name: str) -> tuple[int, int] | None:
        match = re.search(
            rf"(?m)^    {re.escape(property_name)}:\s*",
            source,
        )
        if match is None:
            return None
        opening = source.find("(", match.end())
        if opening < 0:
            raise UiPatchError(f"{path}: constructor opening was not found: {property_name}")

        depth = 0
        quote: str | None = None
        escaped = False
        line_comment = False
        block_comment = False
        closing = -1
        index = opening
        while index < len(source):
            char = source[index]
            next_char = source[index + 1] if index + 1 < len(source) else ""

            if line_comment:
                if char == "\n":
                    line_comment = False
                index += 1
                continue
            if block_comment:
                if char == "*" and next_char == "/":
                    block_comment = False
                    index += 2
                    continue
                index += 1
                continue
            if quote is not None:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                index += 1
                continue
            if char == "/" and next_char == "/":
                line_comment = True
                index += 2
                continue
            if char == "/" and next_char == "*":
                block_comment = True
                index += 2
                continue
            if char in ("'", '"'):
                quote = char
                index += 1
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    closing = index
                    break
            index += 1

        if closing < 0:
            raise UiPatchError(f"{path}: constructor closing was not found: {property_name}")

        end = closing + 1
        while end < len(source) and source[end] in " \t":
            end += 1
        if end >= len(source) or source[end] != ",":
            raise UiPatchError(f"{path}: constructor property has no trailing comma: {property_name}")
        end += 1
        while end < len(source) and source[end] != "\n":
            end += 1
        return match.start(), end

    def set_constructor_property(
        source: str,
        property_name: str,
        replacement: str,
        *,
        insert_after: str,
    ) -> str:
        span = constructor_property_span(source, property_name)
        if span is None:
            return insert_after_property(source, insert_after, replacement)
        start, end = span
        return source[:start] + replacement + source[end:]

    block = set_line_property(
        block,
        "scaffoldBackgroundColor",
        f"    scaffoldBackgroundColor: const Color({BACKGROUND}), // {theme_marker} {robust_marker}",
        insert_after="brightness",
    )

    app_bar = f"""    appBarTheme: const AppBarTheme(
      backgroundColor: Color({NAVY}),
      foregroundColor: Colors.white,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      shadowColor: Colors.transparent,
    ),"""
    block = set_constructor_property(
        block,
        "appBarTheme",
        app_bar,
        insert_after="scaffoldBackgroundColor",
    )

    block = set_line_property(
        block,
        "cardColor",
        "    cardColor: Colors.white,",
        insert_after="appBarTheme",
    )

    color_scheme = f"""    colorScheme: const ColorScheme.light(
      primary: Color({NAVY}),
      secondary: Color({GOLD}),
      background: Color({BACKGROUND}),
      surface: Colors.white,
    ),"""
    block = set_constructor_property(
        block,
        "colorScheme",
        color_scheme,
        insert_after="cardColor",
    )

    if f"foregroundColor: const Color({NAVY})" not in block:
        button_match = re.search(
            r"(?m)^(\s{8}backgroundColor:\s*(?:MyTheme\.)?accent,\s*)$",
            block,
        )
        if button_match is not None:
            insertion = (
                button_match.group(1)
                + "\n"
                + f"        foregroundColor: const Color({NAVY}),"
            )
            block = block[: button_match.start()] + insertion + block[button_match.end() :]

    content = content[:light_start] + block + content[dark_start:]
    write_text(path, content)


def patch_final_host_title(path: Path, content: str) -> tuple[str, bool]:
    """Promote the base host title to the final visual title idempotently."""
    ui_marker = f"{MARKER}_SERVER"
    base_marker = "SAURUS_ANDROID_HOST_V1_HOST_TITLE"
    final_prefix = '  final title = "Dispositivo";'

    if ui_marker in content:
        if content.count(final_prefix) != 1:
            raise UiPatchError(
                f"{path}: final UI marker exists but the final host title is not unique"
            )
        # Normalize legacy output from earlier builds so both layers can
        # recognize the final line during a second pipeline pass.
        title_line = next(
            line for line in content.splitlines() if final_prefix in line
        )
        if base_marker not in title_line:
            normalized = f'{final_prefix} // {ui_marker} // {base_marker}'
            content = content.replace(title_line, normalized, 1)
            return content, True
        return content, False

    title_pattern = re.compile(
        r'(?m)^  final title = "Este dispositivo";[^\n]*SAURUS_ANDROID_HOST_V1_HOST_TITLE[^\n]*$'
    )
    replacement = f'{final_prefix} // {ui_marker} // {base_marker}'
    content, count = title_pattern.subn(replacement, content, count=1)
    if count != 1:
        raise UiPatchError(f"{path}: marked base host page title contract not found")
    return content, True


def patch_server_page(root: Path) -> None:
    path = root / "flutter/lib/mobile/pages/server_page.dart"
    content = read_text(path)
    if f"{MARKER}_SERVER" in content:
        content, changed = patch_final_host_title(path, content)
        if changed:
            write_text(path, content)
        return

    content, _ = patch_final_host_title(path, content)

    hero_anchor = """                      children: [
                        buildPresetPasswordWarningMobile(),"""
    hero_replacement = """                      children: [
                        const SaurusHostHero(),
                        buildPresetPasswordWarningMobile(),"""
    if hero_anchor not in content:
        raise UiPatchError(f"{path}: host page children anchor not found")
    content = content.replace(hero_anchor, hero_replacement, 1)

    content = content.replace(
        """    const TextStyle textStyleHeading = TextStyle(
        fontSize: 16.0, fontWeight: FontWeight.bold, color: Colors.grey);
    const TextStyle textStyleValue =
        TextStyle(fontSize: 25.0, fontWeight: FontWeight.bold);""",
        f"""    const TextStyle textStyleHeading = TextStyle(
        fontSize: 13.0,
        fontWeight: FontWeight.w600,
        color: Color({MUTED}));
    const TextStyle textStyleValue = TextStyle(
        fontSize: 28.0,
        fontWeight: FontWeight.w700,
        color: Color({NAVY}));""",
        1,
    )

    permission_title_old = '        title: translate("Permissions"),'
    if permission_title_old not in content:
        raise UiPatchError(f"{path}: permissions title contract not found")
    content = content.replace(permission_title_old, "        title: 'Permiss\u00f5es',", 1)

    input_old = """          PermissionRow(
            translate("Input Control"),
            serverModel.inputOk,
            serverModel.toggleInput,
          ),"""
    input_new = f"""          SaurusInputPermissionRow(
            serverModel: serverModel,
          ), // {MARKER}_GUIDED_INPUT"""
    if input_old not in content:
        raise UiPatchError(f"{path}: input permission row contract not found")
    content = content.replace(input_old, input_new, 1)

    label_replacements = [
        ('translate("Screen Capture")', "'Captura de tela'"),
        ('translate("Transfer file")', "'Transferir arquivos'"),
        ('translate("Audio Capture")', "'Captura de \\u00e1udio'"),
        ('translate("Enable clipboard")', "'\\u00c1rea de transfer\\u00eancia'"),
        ('label: Text(translate("Stop service"))', "label: const Text('Parar servi\\u00e7o')"),
    ]
    for old, new in label_replacements:
        if old not in content:
            raise UiPatchError(f"{path}: expected label contract not found: {old}")
        content = content.replace(old, new, 1)

    # SAURUS_ANDROID_DART_CLASS_BOUNDARY_V4
    permission_class = rf'''class PermissionRow extends StatelessWidget {{
  const PermissionRow(this.name, this.isOk, this.onPressed,
      {{Key? key, this.enabled = true}})
      : super(key: key);

  final String name;
  final bool isOk;
  final VoidCallback onPressed;
  final bool enabled;

  @override
  Widget build(BuildContext context) {{
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(13),
        border: Border.all(color: const Color({BORDER})),
      ),
      child: SwitchListTile(
        visualDensity: VisualDensity.compact,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
        secondary: Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: isOk
                ? const Color(0xFFEAF8F0)
                : const Color(0xFFF2F4F7),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(
            isOk ? Icons.check_circle_outline : Icons.tune,
            color: isOk ? const Color(0xFF1E9E5A) : const Color({MUTED}),
          ),
        ),
        title: Text(
          name,
          style: const TextStyle(
            color: Color({NAVY}),
            fontWeight: FontWeight.w600,
          ),
        ),
        value: isOk,
        activeColor: const Color({GOLD}),
        onChanged: enabled ? (_) => onPressed() : null,
      ),
    );
  }}
}}

class ConnectionManager'''
    content = replace_dart_class_pair(
        content,
        "PermissionRow",
        "ConnectionManager",
        permission_class,
        path,
    )

    card_class = rf'''class PaddingCard extends StatelessWidget {{
  const PaddingCard({{Key? key, required this.child, this.title, this.titleIcon}})
      : super(key: key);

  final String? title;
  final Icon? titleIcon;
  final Widget child;

  @override
  Widget build(BuildContext context) {{
    final children = <Widget>[child];
    if (title != null) {{
      children.insert(
        0,
        Padding(
          padding: const EdgeInsets.only(bottom: 14),
          child: Row(
            children: [
              if (titleIcon != null)
                Container(
                  width: 38,
                  height: 38,
                  margin: const EdgeInsets.only(right: 10),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF1F4F7),
                    borderRadius: BorderRadius.circular(11),
                  ),
                  child: IconTheme(
                    data: const IconThemeData(color: Color({NAVY}), size: 21),
                    child: titleIcon!,
                  ),
                ),
              Expanded(
                child: Text(
                  title!,
                  style: const TextStyle(
                    color: Color({NAVY}),
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    }}
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.fromLTRB(14, 10, 14, 0),
      padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color({BORDER})),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0F14213D),
            blurRadius: 16,
            offset: Offset(0, 5),
          ),
        ],
      ),
      child: Column(children: children),
    );
  }}
}}

class ClientInfo'''
    content = replace_dart_class_pair(
        content,
        "PaddingCard",
        "ClientInfo",
        card_class,
        path,
    )

    extra_widgets = rf'''
class SaurusHostHero extends StatelessWidget {{
  const SaurusHostHero({{Key? key}}) : super(key: key);

  @override
  Widget build(BuildContext context) {{
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.fromLTRB(14, 14, 14, 2),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color({NAVY}),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        children: [
          Container(
            width: 52,
            height: 52,
            padding: const EdgeInsets.all(9),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(15),
            ),
            child: Image.asset(
              'assets/saurus_remote_android_logo.png',
              fit: BoxFit.contain,
            ),
          ),
          const SizedBox(width: 14),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Suporte remoto Saurus',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 19,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                SizedBox(height: 5),
                Text(
                  'Compartilhe este dispositivo com seguran\u00e7a.',
                  style: TextStyle(color: Color(0xFFD8DEE9), fontSize: 13),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }}
}}

class SaurusInputPermissionRow extends StatelessWidget {{
  const SaurusInputPermissionRow({{Key? key, required this.serverModel}})
      : super(key: key);

  final ServerModel serverModel;

  @override
  Widget build(BuildContext context) {{
    final enabled = serverModel.inputOk;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: enabled ? const Color(0xFFF0FBF5) : const Color(0xFFFFFBEB),
        borderRadius: BorderRadius.circular(13),
        border: Border.all(
          color: enabled ? const Color(0xFFBDE7CF) : const Color(0xFFF3D98A),
        ),
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 5),
        leading: Container(
          width: 38,
          height: 38,
          decoration: BoxDecoration(
            color: enabled ? const Color(0xFFE0F5E9) : const Color(0xFFFFF2C7),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(
            enabled ? Icons.touch_app : Icons.admin_panel_settings_outlined,
            color: enabled ? const Color(0xFF1E9E5A) : const Color({NAVY}),
          ),
        ),
        title: const Text(
          'Controle de entrada',
          style: TextStyle(
            color: Color({NAVY}),
            fontWeight: FontWeight.w700,
          ),
        ),
        subtitle: Text(
          enabled
              ? 'Ativado para toques, teclado e gestos.'
              : 'Necess\u00e1rio para controlar o Android pelo computador.',
          style: const TextStyle(color: Color({MUTED}), fontSize: 12),
        ),
        trailing: enabled
            ? const Icon(Icons.check_circle, color: Color(0xFF1E9E5A))
            : FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor: const Color({GOLD}),
                  foregroundColor: const Color({NAVY}),
                  padding: const EdgeInsets.symmetric(horizontal: 13),
                ),
                onPressed: () => showSaurusInputPermissionGuide(
                  context,
                  serverModel,
                ),
                child: const Text('Configurar'),
              ),
        onTap: enabled
            ? serverModel.toggleInput
            : () => showSaurusInputPermissionGuide(context, serverModel),
      ),
    );
  }}
}}

Future<void> showSaurusInputPermissionGuide(
  BuildContext context,
  ServerModel serverModel,
) async {{
  await showDialog<void>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.touch_app, color: Color({NAVY})),
          SizedBox(width: 10),
          Expanded(child: Text('Ativar controle de entrada')),
        ],
      ),
      content: const SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'O controle de entrada permite cliques, teclado, rolagem e gestos durante uma sess\u00e3o remota autorizada.',
            ),
            SizedBox(height: 14),
            Text(
              'Se o Android exibir "Configura\u00e7\u00e3o restrita", abra as informa\u00e7\u00f5es do aplicativo e escolha "Permitir configura\u00e7\u00f5es restritas". Depois volte ao Saurus Remote e continue para a acessibilidade.',
              style: TextStyle(color: Color({MUTED}), height: 1.35),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () {{
            Navigator.of(dialogContext).pop();
            AndroidPermissionManager.startAction(
              kActionApplicationDetailsSettings,
            );
          }},
          child: const Text('Informa\u00e7\u00f5es do aplicativo'),
        ),
        FilledButton(
          style: FilledButton.styleFrom(
            backgroundColor: const Color({GOLD}),
            foregroundColor: const Color({NAVY}),
          ),
          onPressed: () {{
            Navigator.of(dialogContext).pop();
            serverModel.toggleInput();
          }},
          child: const Text('Abrir acessibilidade'),
        ),
      ],
    ),
  );
}}

'''
    anchor = "class PermissionChecker extends StatefulWidget {"
    if anchor not in content:
        raise UiPatchError(f"{path}: PermissionChecker anchor not found")
    content = content.replace(anchor, extra_widgets + anchor, 1)
    write_text(path, content)


def patch_settings_title(root: Path) -> None:
    path = root / "flutter/lib/mobile/pages/settings_page.dart"
    content = read_text(path)
    if f"{MARKER}_SETTINGS_TITLE" in content:
        return
    old = '  final title = translate("Settings");'
    if content.count(old) != 1:
        raise UiPatchError(f"{path}: settings title contract not found")
    content = content.replace(
        old,
        f'  final title = "Ajustes"; // {MARKER}_SETTINGS_TITLE',
        1,
    )
    write_text(path, content)


def upsert_xml_attribute_in_start_tag(
    content: str,
    *,
    tag_name: str,
    attribute: str,
    value: str,
    path: Path,
    selector: str | None = None,
    indent: str = "    ",
) -> str:
    """Set one XML attribute while removing legacy or duplicate copies.

    The input may already contain the attribute, including more than once due to
    an interrupted older patch. Working on the start tag before parsing allows
    this helper to repair that invalid intermediate state deterministically.
    """
    pattern = re.compile(
        rf"<{re.escape(tag_name)}\b(?P<body>.*?)(?P<close>/?)>",
        re.DOTALL,
    )
    matches = [
        match
        for match in pattern.finditer(content)
        if selector is None or selector in match.group(0)
    ]
    if len(matches) != 1:
        raise UiPatchError(
            f"{path}: expected one <{tag_name}> start tag for {attribute}, "
            f"found {len(matches)}"
        )

    match = matches[0]
    start_tag = match.group(0)
    attribute_pattern = re.compile(
        rf"\s+{re.escape(attribute)}\s*=\s*(?P<quote>[\"'])(?P<value>.*?)(?P=quote)",
        re.DOTALL,
    )
    cleaned = attribute_pattern.sub("", start_tag)
    stripped = cleaned.rstrip()
    closing = "/>" if stripped.endswith("/>") else ">"
    prefix = stripped[: -len(closing)].rstrip()
    replacement = f'{prefix}\n{indent}{attribute}="{value}"{closing}'
    return content[: match.start()] + replacement + content[match.end() :]


def ensure_single_xml_marker(content: str, marker: str) -> str:
    marker_pattern = re.compile(rf"\s*<!--\s*{re.escape(marker)}\s*-->\s*")
    content = marker_pattern.sub("\n", content).lstrip("\n")
    comment = f"<!-- {marker} -->"
    if content.startswith("<?xml"):
        end = content.find("?>")
        if end < 0:
            raise UiPatchError("Malformed XML declaration while adding Saurus marker")
        return content[: end + 2] + "\n" + comment + "\n" + content[end + 2 :].lstrip("\n")
    return comment + "\n" + content


def _scan_dart_matching(text: str, start: int, opening: str, closing: str) -> int:
    # Return the matching delimiter index while ignoring strings and comments.
    if start < 0 or start >= len(text) or text[start] != opening:
        raise UiPatchError(f"Expected {opening!r} at offset {start}")
    depth = 0
    index = start
    quote: str | None = None
    triple = False
    raw_string = False
    line_comment = False
    block_comment = 0
    escaped = False
    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if char == "/" and nxt == "*":
                block_comment += 1
                index += 2
                continue
            if char == "*" and nxt == "/":
                block_comment -= 1
                index += 2
                continue
            index += 1
            continue
        if quote is not None:
            if triple:
                if text.startswith(quote * 3, index):
                    quote = None
                    triple = False
                    raw_string = False
                    index += 3
                    continue
            elif char == quote and (raw_string or not escaped):
                quote = None
                raw_string = False
                index += 1
                continue
            if char == "\\" and not raw_string:
                escaped = not escaped
            else:
                escaped = False
            index += 1
            continue
        if char == "/" and nxt == "/":
            line_comment = True
            index += 2
            continue
        if char == "/" and nxt == "*":
            block_comment = 1
            index += 2
            continue
        if char in ("'", '"'):
            raw_string = index > 0 and text[index - 1] in ("r", "R")
            quote = char
            triple = text.startswith(char * 3, index)
            index += 3 if triple else 1
            escaped = False
            continue
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise UiPatchError(f"Unbalanced Dart delimiter {opening}{closing}")


def _find_dart_method_block(content: str, method_name: str, path: Path) -> tuple[int, int]:
    pattern = re.compile(
        rf"(?ms)^[ \t]*(?:void\s+)?{re.escape(method_name)}\s*"
        rf"\([^)]*\)\s*(?:async\s*)?\{{"
    )
    matches = list(pattern.finditer(content))
    if len(matches) != 1:
        raise UiPatchError(
            f"{path}: expected one {method_name} method declaration, found {len(matches)}"
        )
    open_brace = content.rfind("{", matches[0].start(), matches[0].end())
    if open_brace < 0:
        raise UiPatchError(f"{path}: opening brace not found for {method_name}")
    close_brace = _scan_dart_matching(content, open_brace, "{", "}")
    return open_brace, close_brace


def _find_named_argument_value(call: str, name: str, path: Path) -> tuple[int, int] | None:
    # Find a top-level named argument value inside a Dart call body.
    index = 0
    depth_round = depth_square = depth_curly = depth_angle = 0
    quote: str | None = None
    triple = False
    raw_string = False
    line_comment = False
    block_comment = 0
    escaped = False
    while index < len(call):
        char = call[index]
        nxt = call[index + 1] if index + 1 < len(call) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if char == "/" and nxt == "*":
                block_comment += 1
                index += 2
                continue
            if char == "*" and nxt == "/":
                block_comment -= 1
                index += 2
                continue
            index += 1
            continue
        if quote is not None:
            if triple:
                if call.startswith(quote * 3, index):
                    quote = None
                    triple = False
                    raw_string = False
                    index += 3
                    continue
            elif char == quote and (raw_string or not escaped):
                quote = None
                raw_string = False
                index += 1
                continue
            if char == "\\" and not raw_string:
                escaped = not escaped
            else:
                escaped = False
            index += 1
            continue
        if char == "/" and nxt == "/":
            line_comment = True
            index += 2
            continue
        if char == "/" and nxt == "*":
            block_comment = 1
            index += 2
            continue
        if char in ("'", '"'):
            raw_string = index > 0 and call[index - 1] in ("r", "R")
            quote = char
            triple = call.startswith(char * 3, index)
            index += 3 if triple else 1
            escaped = False
            continue
        if char == "(":
            depth_round += 1
        elif char == ")":
            depth_round -= 1
        elif char == "[":
            depth_square += 1
        elif char == "]":
            depth_square -= 1
        elif char == "{":
            depth_curly += 1
        elif char == "}":
            depth_curly -= 1
        elif char == "<":
            depth_angle += 1
        elif char == ">" and depth_angle:
            depth_angle -= 1
        if not any((depth_round, depth_square, depth_curly, depth_angle)):
            match = re.match(rf"\s*{re.escape(name)}\s*:\s*", call[index:])
            if match:
                value_start = index + match.end()
                value_index = value_start
                vr = vs = vc = va = 0
                vquote: str | None = None
                vtriple = False
                vraw = False
                vline = False
                vblock = 0
                vescaped = False
                while value_index < len(call):
                    vchar = call[value_index]
                    vnxt = call[value_index + 1] if value_index + 1 < len(call) else ""
                    if vline:
                        if vchar == "\n":
                            vline = False
                        value_index += 1
                        continue
                    if vblock:
                        if vchar == "/" and vnxt == "*":
                            vblock += 1
                            value_index += 2
                            continue
                        if vchar == "*" and vnxt == "/":
                            vblock -= 1
                            value_index += 2
                            continue
                        value_index += 1
                        continue
                    if vquote is not None:
                        if vtriple:
                            if call.startswith(vquote * 3, value_index):
                                vquote = None
                                vtriple = False
                                vraw = False
                                value_index += 3
                                continue
                        elif vchar == vquote and (vraw or not vescaped):
                            vquote = None
                            vraw = False
                            value_index += 1
                            continue
                        if vchar == "\\" and not vraw:
                            vescaped = not vescaped
                        else:
                            vescaped = False
                        value_index += 1
                        continue
                    if vchar == "/" and vnxt == "/":
                        vline = True
                        value_index += 2
                        continue
                    if vchar == "/" and vnxt == "*":
                        vblock = 1
                        value_index += 2
                        continue
                    if vchar in ("'", '"'):
                        vraw = value_index > 0 and call[value_index - 1] in ("r", "R")
                        vquote = vchar
                        vtriple = call.startswith(vchar * 3, value_index)
                        value_index += 3 if vtriple else 1
                        vescaped = False
                        continue
                    if vchar == "(":
                        vr += 1
                    elif vchar == ")":
                        vr -= 1
                    elif vchar == "[":
                        vs += 1
                    elif vchar == "]":
                        vs -= 1
                    elif vchar == "{":
                        vc += 1
                    elif vchar == "}":
                        vc -= 1
                    elif vchar == "<":
                        va += 1
                    elif vchar == ">" and va:
                        va -= 1
                    elif vchar == "," and not any((vr, vs, vc, va)):
                        return value_start, value_index
                    value_index += 1
                return value_start, value_index
        index += 1
    return None


def _incoming_actions_widget() -> str:
    return f"""[
        // {INCOMING_ACCEPT_MARKER}
        SizedBox(
          width: double.infinity,
          child: Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: cancel,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color({NAVY}),
                    side: const BorderSide(color: Color({BORDER})),
                    minimumSize: const Size(0, 46),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 12),
                  ),
                  icon: const Icon(Icons.close, size: 18),
                  label: const FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text('Dispensar'),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: submit,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color({GOLD}),
                    foregroundColor: const Color({NAVY}),
                    minimumSize: const Size(0, 46),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 12),
                    elevation: 0,
                  ),
                  icon: const Icon(Icons.check, size: 18),
                  label: const FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text('Aceitar'),
                  ),
                ),
              ),
            ],
          ),
        ),
      ]"""


def patch_incoming_accept_dialog_content(content: str, path: Path) -> tuple[str, bool]:
    # Replace incoming actions regardless of whether upstream uses a list or variable.
    method_open, method_close = _find_dart_method_block(content, "showLoginDialog", path)
    method = content[method_open : method_close + 1]
    for callback in (
        "sendLoginResponse(client, false)",
        "sendLoginResponse(client, true)",
    ):
        if callback not in method:
            raise UiPatchError(f"{path}: missing incoming-access callback: {callback}")
    dialog_match = re.search(r"\bCustomAlertDialog\s*\(", method)
    if not dialog_match:
        raise UiPatchError(f"{path}: incoming CustomAlertDialog call not found")
    call_open = method.find("(", dialog_match.start())
    call_close = _scan_dart_matching(method, call_open, "(", ")")
    call_body_start = call_open + 1
    call_body = method[call_body_start:call_close]
    actions = _find_named_argument_value(call_body, "actions", path)
    replacement = _incoming_actions_widget()
    if actions is None:
        insertion = _find_named_argument_value(call_body, "onSubmit", path)
        if insertion is None:
            raise UiPatchError(f"{path}: neither actions nor onSubmit was found in incoming dialog")
        argument_start = call_body.rfind("\n", 0, insertion[0]) + 1
        indent_match = re.match(r"\s*", call_body[argument_start:])
        indent = indent_match.group(0) if indent_match else "      "
        updated_body = (
            call_body[:argument_start]
            + f"{indent}actions: {replacement},\n"
            + call_body[argument_start:]
        )
    else:
        value_start, value_end = actions
        current = call_body[value_start:value_end]
        if INCOMING_ACCEPT_MARKER in current and re.sub(r"\s+", "", current) == re.sub(r"\s+", "", replacement):
            return content, False
        updated_body = call_body[:value_start] + replacement + call_body[value_end:]
    updated_method = method[:call_body_start] + updated_body + method[call_close:]
    updated = content[:method_open] + updated_method + content[method_close + 1:]
    final_open, final_close = _find_dart_method_block(updated, "showLoginDialog", path)
    final_method = updated[final_open : final_close + 1]
    for required in (
        INCOMING_ACCEPT_MARKER,
        "child: Text('Dispensar')",
        "child: Text('Aceitar')",
        "onPressed: cancel",
        "onPressed: submit",
        "width: double.infinity",
    ):
        if required not in final_method:
            raise UiPatchError(f"{path}: incomplete incoming-access action contract: {required}")
    return updated, updated != content

def patch_incoming_accept_dialog(root: Path) -> None:
    path = root / "flutter/lib/models/server_model.dart"
    content = read_text(path)
    content, changed = patch_incoming_accept_dialog_content(content, path)
    if changed:
        write_text(path, content)


def patch_launcher_resources(root: Path) -> None:
    """Replace legacy and adaptive launcher contracts with Saurus resources."""
    res = root / "flutter/android/app/src/main/res"
    colors = res / "values/saurus_launcher_colors.xml"
    adaptive = res / "mipmap-anydpi-v26/ic_launcher.xml"
    adaptive_round = res / "mipmap-anydpi-v26/ic_launcher_round.xml"

    write_text(
        colors,
        '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="saurus_launcher_background">#14213D</color>
</resources>''',
    )
    adaptive_content = f'''<?xml version="1.0" encoding="utf-8"?>
<!-- {LAUNCHER_PATCH_MARKER} -->
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/saurus_launcher_background" />
    <foreground android:drawable="@mipmap/saurus_launcher_foreground" />
</adaptive-icon>'''
    write_text(adaptive, adaptive_content)
    write_text(adaptive_round, adaptive_content)

    manifest = root / "flutter/android/app/src/main/AndroidManifest.xml"
    manifest_content = read_text(manifest)
    manifest_content = upsert_xml_attribute_in_start_tag(
        manifest_content,
        tag_name="application",
        attribute="android:icon",
        value="@mipmap/ic_launcher",
        path=manifest,
        indent="        ",
    )
    manifest_content = upsert_xml_attribute_in_start_tag(
        manifest_content,
        tag_name="application",
        attribute="android:roundIcon",
        value="@mipmap/ic_launcher_round",
        path=manifest,
        indent="        ",
    )
    manifest_content = ensure_single_xml_marker(
        manifest_content,
        LAUNCHER_PATCH_MARKER,
    )
    write_text(manifest, manifest_content)

    for path in (manifest, colors, adaptive, adaptive_round):
        try:
            ET.parse(path)
        except ET.ParseError as exc:
            raise UiPatchError(f"{path}: invalid XML after launcher patch: {exc}") from exc


def patch_accessibility_resources(root: Path) -> None:
    values = root / "flutter/android/app/src/main/res/values/saurus_accessibility_strings.xml"
    write_text(
        values,
        """<?xml version=\"1.0\" encoding=\"utf-8\"?>
<resources>
    <string name=\"saurus_accessibility_description\">Permite que o Saurus Remote execute toques, gestos e digitacao somente durante uma sessao de suporte remoto autorizada.</string>
</resources>""",
    )

    manifest = root / "flutter/android/app/src/main/AndroidManifest.xml"
    manifest_content = read_text(manifest)
    manifest_content = upsert_xml_attribute_in_start_tag(
        manifest_content,
        tag_name="service",
        attribute="android:description",
        value="@string/saurus_accessibility_description",
        path=manifest,
        selector='android.permission.BIND_ACCESSIBILITY_SERVICE',
        indent="            ",
    )
    manifest_content = upsert_xml_attribute_in_start_tag(
        manifest_content,
        tag_name="service",
        attribute="android:icon",
        value="@mipmap/ic_launcher",
        path=manifest,
        selector='android.permission.BIND_ACCESSIBILITY_SERVICE',
        indent="            ",
    )
    manifest_content = ensure_single_xml_marker(
        manifest_content,
        f"{MARKER}_ACCESSIBILITY_METADATA",
    )
    write_text(manifest, manifest_content)

    config = root / "flutter/android/app/src/main/res/xml/accessibility_service_config.xml"
    config_content = read_text(config)
    config_content = upsert_xml_attribute_in_start_tag(
        config_content,
        tag_name="accessibility-service",
        attribute="android:description",
        value="@string/saurus_accessibility_description",
        path=config,
        indent="    ",
    )
    config_content = ensure_single_xml_marker(
        config_content,
        f"{MARKER}_ACCESSIBILITY_DESCRIPTION",
    )
    write_text(config, config_content)

    for xml_path in (manifest, config, values):
        try:
            ET.parse(xml_path)
        except ET.ParseError as exc:
            raise UiPatchError(f"{xml_path}: invalid XML after accessibility patch: {exc}") from exc


def apply_ui_v2(root: Path) -> None:
    patch_home_page(root)
    patch_theme(root)
    patch_server_page(root)
    patch_incoming_accept_dialog(root)
    patch_settings_title(root)
    patch_launcher_resources(root)
    patch_accessibility_resources(root)


def self_test() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        sample = root / "sample.txt"
        write_text(sample, "A\r\nB  ")
        if read_text(sample) != "A\nB\n":
            raise UiPatchError("UTF-8/LF helper self-test failed")

        fixtures = [
            """class MyTheme {
  static ThemeData lightTheme = ThemeData(
    brightness: Brightness.light,
    scaffoldBackgroundColor: Colors.white,
    appBarTheme: AppBarTheme(
      shadowColor: Colors.transparent,
    ),
    cardColor: grayBg,
    colorScheme: ColorScheme.light(
        primary: Colors.blue, secondary: accent, background: grayBg),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: MyTheme.accent,
      ),
    ),
  );
  static ThemeData darkTheme = ThemeData(
    brightness: Brightness.dark,
  );
}
""",
            """class MyTheme {
  static ThemeData lightTheme = ThemeData(
    brightness: Brightness.light,
    scaffoldBackgroundColor: const Color(0xFFF4F5F7),
    cardColor: const Color(0xFFF4F5F7),
    visualDensity: VisualDensity.adaptivePlatformDensity,
  );
  static ThemeData darkTheme = ThemeData(
    brightness: Brightness.dark,
  );
}
""",
            """class MyTheme {
  static ThemeData lightTheme = ThemeData(
    brightness: Brightness.light,
    scaffoldBackgroundColor: const Color(0xFFF4F5F7), // existing customization
    appBarTheme: const AppBarTheme(
      backgroundColor: Color(0xFF123456),
      shadowColor: Colors.transparent,
    ),
    colorScheme: const ColorScheme.light(
      primary: Color(0xFF123456),
      secondary: Color(0xFF654321),
    ),
  );
  static ThemeData darkTheme = ThemeData(
    brightness: Brightness.dark,
  );
}
""",
        ]

        for number, fixture in enumerate(fixtures, start=1):
            fixture_root = root / f"fixture-{number}"
            common = fixture_root / "flutter/lib/common.dart"
            write_text(common, fixture)
            patch_theme(fixture_root)
            patch_theme(fixture_root)
            themed = read_text(common)
            for required in (
                "SAURUS_ANDROID_THEME_PATCH_V3",
                f"primary: Color({NAVY})",
                f"secondary: Color({GOLD})",
                "cardColor: Colors.white",
                f"backgroundColor: Color({NAVY})",
            ):
                if required not in themed:
                    raise UiPatchError(
                        f"Theme variant self-test {number} failed: {required}"
                    )
            if themed.count(f"{MARKER}_THEME") != 1:
                raise UiPatchError(
                    f"Theme variant self-test {number} is not idempotent"
                )

        dart_fixture = """class PermissionRow extends StatelessWidget {
  Widget build(BuildContext context) {
    return const SizedBox.shrink();
  }
}

class ConnectionManager extends StatelessWidget {
}

class PaddingCard extends StatelessWidget {
  Widget build(BuildContext context) {
    return const SizedBox.shrink();
  }
}


class ClientInfo extends StatelessWidget {
}
"""
        permission_fixture_replacement = """class PermissionRow extends StatelessWidget {
  const PermissionRow();
}

class ConnectionManager"""
        card_fixture_replacement = """class PaddingCard extends StatelessWidget {
  const PaddingCard();
}

class ClientInfo"""
        dart_fixture = replace_dart_class_pair(
            dart_fixture,
            "PermissionRow",
            "ConnectionManager",
            permission_fixture_replacement,
            root / "server-page-fixture.dart",
        )
        dart_fixture = replace_dart_class_pair(
            dart_fixture,
            "PaddingCard",
            "ClientInfo",
            card_fixture_replacement,
            root / "server-page-fixture.dart",
        )
        for required in (
            "const PermissionRow();",
            "class ConnectionManager extends StatelessWidget",
            "const PaddingCard();",
            "class ClientInfo extends StatelessWidget",
        ):
            if required not in dart_fixture:
                raise UiPatchError(
                    f"Dart class boundary self-test failed: {required}"
                )

        incoming_variants = [
            """void caller(Client client) { showLoginDialog(client); }

void showLoginDialog(Client client) {
  cancel() { sendLoginResponse(client, false); }
  submit() { sendLoginResponse(client, true); }
  return CustomAlertDialog(
      content: const Text('request'),
      actions: [
        TextButton(onPressed: cancel, child: Text(translate(\"Dismiss\"))),
        ElevatedButton(onPressed: submit, child: Text(translate(\"Accept\"))),
      ],
      onSubmit: submit,
      onCancel: cancel,
  );
}""",
            """void showLoginDialog(Client client) {
  cancel() { sendLoginResponse(client, false); }
  submit() { sendLoginResponse(client, true); }
  return CustomAlertDialog(
      content: const Text('request'),
      actions: [
        dialogButton("Dismiss", onPressed: cancel, isOutline: true),
        if (approveMode != 'password')
          dialogButton("Accept", onPressed: submit),
      ],
      onSubmit: submit,
      onCancel: cancel,
  );
}""",
            """void showLoginDialog(Client client) {
  cancel() { sendLoginResponse(client, false); }
  submit() { sendLoginResponse(client, true); }
  final buttons = <Widget>[
    dialogButton(\"Dismiss\", onPressed: cancel, isOutline: true),
    dialogButton(\"Accept\", onPressed: submit),
  ];
  return CustomAlertDialog(
      content: const Text('request'),
      actions: buttons,
      onSubmit: submit,
      onCancel: cancel,
  );
}""",
            """void showLoginDialog(Client client) {
  cancel() { sendLoginResponse(client, false); }
  submit() { sendLoginResponse(client, true); }
  return CustomAlertDialog(
      content: const Text('request'),
      onSubmit: submit,
      onCancel: cancel,
  );
}""",
        ]
        for number, incoming_fixture in enumerate(incoming_variants, start=1):
            incoming_fixture, changed = patch_incoming_accept_dialog_content(
                incoming_fixture,
                root / f"server-model-fixture-{number}.dart",
            )
            if not changed:
                raise UiPatchError(f"Incoming-access structural self-test {number} did not apply")
            incoming_second, changed = patch_incoming_accept_dialog_content(
                incoming_fixture,
                root / f"server-model-fixture-{number}.dart",
            )
            if changed or incoming_second != incoming_fixture:
                raise UiPatchError(f"Incoming-access structural self-test {number} is not idempotent")
            for required in (
                "child: Text('Dispensar')",
                "child: Text('Aceitar')",
                "onPressed: cancel",
                "onPressed: submit",
                "width: double.infinity",
                INCOMING_ACCEPT_MARKER,
            ):
                if required not in incoming_fixture:
                    raise UiPatchError(f"Incoming-access structural self-test {number} failed: {required}")
        malformed_incoming = incoming_variants[0].replace(
            "sendLoginResponse(client, true);", "close();"
        )
        try:
            patch_incoming_accept_dialog_content(
                malformed_incoming,
                root / "server-model-negative-fixture.dart",
            )
        except UiPatchError:
            pass
        else:
            raise UiPatchError(
                "Incoming-access negative self-test accepted a dialog without approve callback"
            )

        xml_root = root / "xml-fixture"
        manifest = xml_root / "flutter/android/app/src/main/AndroidManifest.xml"
        accessibility = xml_root / "flutter/android/app/src/main/res/xml/accessibility_service_config.xml"
        write_text(
            manifest,
            """<manifest xmlns:android="http://schemas.android.com/apk/res/android">
<application android:icon="@mipmap/legacy" android:roundIcon="@mipmap/legacy_round">
<service
            android:label="Saurus Remote - Controle de entrada"
            android:description="@string/legacy_accessibility_description"
            android:icon="@drawable/legacy_icon"
            android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE">
</service>
</application>
</manifest>""",
        )
        write_text(
            accessibility,
            """<accessibility-service xmlns:android="http://schemas.android.com/apk/res/android"
    android:description="@string/legacy_accessibility_description"
    android:description="@string/interrupted_duplicate_description"
    android:accessibilityEventTypes="typeAllMask" />""",
        )
        patch_launcher_resources(xml_root)
        patch_accessibility_resources(xml_root)
        first_manifest = manifest.read_bytes()
        first_accessibility = accessibility.read_bytes()
        patch_launcher_resources(xml_root)
        patch_accessibility_resources(xml_root)
        if manifest.read_bytes() != first_manifest:
            raise UiPatchError("Accessibility manifest patch is not byte-idempotent")
        if accessibility.read_bytes() != first_accessibility:
            raise UiPatchError("Accessibility config patch is not byte-idempotent")

        manifest_root = ET.parse(manifest).getroot()
        config_root = ET.parse(accessibility).getroot()
        android_description = f"{{{ANDROID_NAMESPACE}}}description"
        android_icon = f"{{{ANDROID_NAMESPACE}}}icon"
        android_permission = f"{{{ANDROID_NAMESPACE}}}permission"
        services = [
            item
            for item in manifest_root.iter("service")
            if item.get(android_permission) == "android.permission.BIND_ACCESSIBILITY_SERVICE"
        ]
        if len(services) != 1:
            raise UiPatchError("Accessibility manifest service lookup self-test failed")
        if services[0].get(android_description) != "@string/saurus_accessibility_description":
            raise UiPatchError("Accessibility manifest description upsert self-test failed")
        if services[0].get(android_icon) != "@mipmap/ic_launcher":
            raise UiPatchError("Accessibility manifest icon upsert self-test failed")
        if config_root.get(android_description) != "@string/saurus_accessibility_description":
            raise UiPatchError("Accessibility config description upsert self-test failed")

        applications = list(manifest_root.iter("application"))
        if len(applications) != 1:
            raise UiPatchError("Launcher manifest application lookup self-test failed")
        android_round_icon = f"{{{ANDROID_NAMESPACE}}}roundIcon"
        if applications[0].get(android_icon) != "@mipmap/ic_launcher":
            raise UiPatchError("Launcher manifest icon upsert self-test failed")
        if applications[0].get(android_round_icon) != "@mipmap/ic_launcher_round":
            raise UiPatchError("Launcher manifest roundIcon upsert self-test failed")
        for launcher_xml in (
            xml_root / "flutter/android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml",
            xml_root / "flutter/android/app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml",
        ):
            launcher_root = ET.parse(launcher_xml).getroot()
            if launcher_root.tag != "adaptive-icon":
                raise UiPatchError("Adaptive launcher root self-test failed")
            foreground = launcher_root.find("foreground")
            background = launcher_root.find("background")
            android_drawable = f"{{{ANDROID_NAMESPACE}}}drawable"
            if foreground is None or foreground.get(android_drawable) != "@mipmap/saurus_launcher_foreground":
                raise UiPatchError("Adaptive launcher foreground self-test failed")
            if background is None or background.get(android_drawable) != "@color/saurus_launcher_background":
                raise UiPatchError("Adaptive launcher background self-test failed")

        manifest_text = read_text(manifest)
        xml_text = read_text(accessibility)
        if manifest_text.count(f"{MARKER}_ACCESSIBILITY_METADATA") != 1:
            raise UiPatchError("Accessibility manifest marker is not idempotent")
        if xml_text.count(f"{MARKER}_ACCESSIBILITY_DESCRIPTION") != 1:
            raise UiPatchError("Accessibility XML marker is not idempotent")
        if xml_text.count("android:description=") != 1:
            raise UiPatchError("Accessibility XML duplicate-attribute regression")

        if not all(ord(ch) < 128 for ch in Path(__file__).read_text(encoding="utf-8")):
            raise UiPatchError("The UI patch source must remain ASCII-only")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.self_test:
            self_test()
        else:
            if args.source_root is None:
                raise UiPatchError("--source-root is required")
            apply_ui_v2(args.source_root.resolve())
        print("[OK] Saurus Remote Android UI V2 customization applied")
        return 0
    except (UiPatchError, OSError, UnicodeError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
