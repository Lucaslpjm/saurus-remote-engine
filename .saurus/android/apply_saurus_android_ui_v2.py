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
from pathlib import Path

MARKER = "SAURUS_ANDROID_UI_V2"
NAVY = "0xFF14213D"
GOLD = "0xFFD8B62A"
BACKGROUND = "0xFFF4F6F8"
BORDER = "0xFFE2E7EC"
MUTED = "0xFF667085"


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


def patch_server_page(root: Path) -> None:
    path = root / "flutter/lib/mobile/pages/server_page.dart"
    content = read_text(path)
    if f"{MARKER}_SERVER" in content:
        return

    title_pattern = re.compile(r'  final title = "Este dispositivo";[^\n]*')
    content, count = title_pattern.subn(
        f'  final title = "Dispositivo"; // {MARKER}_SERVER', content, count=1
    )
    if count != 1:
        raise UiPatchError(f"{path}: host page title contract not found")

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

    permission_class_pattern = re.compile(
        r"class PermissionRow extends StatelessWidget \{.*?\n\}\nclass ConnectionManager",
        flags=re.S,
    )
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
    content, count = permission_class_pattern.subn(permission_class, content, count=1)
    if count != 1:
        raise UiPatchError(f"{path}: PermissionRow class contract not found")

    card_pattern = re.compile(
        r"class PaddingCard extends StatelessWidget \{.*?\n\}\nclass ClientInfo",
        flags=re.S,
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
    content, count = card_pattern.subn(card_class, content, count=1)
    if count != 1:
        raise UiPatchError(f"{path}: PaddingCard class contract not found")

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
    content = read_text(manifest)
    if f"{MARKER}_ACCESSIBILITY_METADATA" not in content:
        old = '            android:label="Saurus Remote - Controle de entrada"\n            android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE">'
        new = f'''            android:label="Saurus Remote - Controle de entrada"
            android:description="@string/saurus_accessibility_description"
            android:icon="@mipmap/ic_launcher"
            android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE">\n            <!-- {MARKER}_ACCESSIBILITY_METADATA -->'''
        if content.count(old) != 1:
            raise UiPatchError(f"{manifest}: accessibility service contract not found")
        content = content.replace(old, new, 1)
        write_text(manifest, content)

    config = root / "flutter/android/app/src/main/res/xml/accessibility_service_config.xml"
    config_content = read_text(config)
    if f"{MARKER}_ACCESSIBILITY_DESCRIPTION" not in config_content:
        pattern = r"(<accessibility-service\b)"
        replacement = rf'\1\n    android:description="@string/saurus_accessibility_description"\n    <!-- {MARKER}_ACCESSIBILITY_DESCRIPTION -->'
        updated, count = re.subn(pattern, replacement, config_content, count=1)
        if count != 1:
            raise UiPatchError(f"{config}: accessibility-service root not found")
        write_text(config, updated)


def apply_ui_v2(root: Path) -> None:
    patch_home_page(root)
    patch_theme(root)
    patch_server_page(root)
    patch_settings_title(root)
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
